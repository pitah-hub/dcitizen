from django.core import mail
from django.core.exceptions import ValidationError
from django.urls import reverse

from accounts.models import User

from .models import Comment, Status
from .test_core import CoreTestCase


class CommentTestCase(CoreTestCase):
    def setUp(self):
        super().setUp()
        self.named_officer = User.objects.create_user(
            "grace@x.com", "pass12345", full_name="Grace Njeri",
            national_id="33333333", phone="0712345678", is_staff=True,
        )

    def resolved_request(self):
        req = self.new_request()
        req.change_status(Status.IN_PROGRESS, self.officer)
        req.change_status(Status.RESOLVED, self.officer)
        return req

    def citizen_post(self, req, body="Any update on this?"):
        return self.client.post(reverse("request_comment", args=[req.pk]), {"body": body})

    def staff_post(self, req, body="We are on it."):
        return self.client.post(reverse("panel:request_comment", args=[req.pk]), {"body": body})


class CitizenCommentTests(CommentTestCase):
    def test_owner_can_comment_and_no_email_is_sent(self):
        req = self.new_request()
        self.client.force_login(self.citizen)
        response = self.citizen_post(req)
        self.assertRedirects(response, reverse("request_detail", args=[req.pk]))
        comment = Comment.objects.get(request=req)
        self.assertEqual((comment.author, comment.body), (self.citizen, "Any update on this?"))
        self.assertEqual(len(mail.outbox), 0)

    def test_other_citizen_gets_404(self):
        req = self.new_request()
        self.client.force_login(self.other)
        self.assertEqual(self.citizen_post(req).status_code, 404)
        self.assertEqual(Comment.objects.count(), 0)

    def test_resolved_request_is_closed(self):
        req = self.resolved_request()
        self.client.force_login(self.citizen)
        self.citizen_post(req)
        self.assertEqual(Comment.objects.count(), 0)

    def test_blank_and_overlong_messages_are_rejected(self):
        req = self.new_request()
        self.client.force_login(self.citizen)
        for bad in ("", "   ", "\n\n", "x" * 1001):
            self.citizen_post(req, bad)
        self.assertEqual(Comment.objects.count(), 0)

    def test_staff_cannot_use_the_citizen_endpoint(self):
        req = self.new_request()
        self.client.force_login(self.officer)
        self.citizen_post(req)
        self.assertEqual(Comment.objects.count(), 0)

    def test_anonymous_is_sent_to_login(self):
        req = self.new_request()
        response = self.citizen_post(req)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])
        self.assertEqual(Comment.objects.count(), 0)

    def test_get_is_not_allowed(self):
        req = self.new_request()
        self.client.force_login(self.citizen)
        self.assertEqual(self.client.get(reverse("request_comment", args=[req.pk])).status_code, 405)


class StaffCommentTests(CommentTestCase):
    def test_officer_comment_emails_the_citizen(self):
        req = self.new_request()
        self.client.force_login(self.named_officer)
        self.staff_post(req, "Crew arrives Friday.")
        comment = Comment.objects.get(request=req)
        self.assertEqual(comment.author, self.named_officer)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["a@x.com"])
        self.assertIn("Crew arrives Friday.", mail.outbox[0].body)
        self.assertIn(req.reference, mail.outbox[0].subject)

    def test_officer_cannot_comment_on_a_resolved_request(self):
        req = self.resolved_request()
        self.client.force_login(self.named_officer)
        self.staff_post(req)
        self.assertEqual(Comment.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_citizens_cannot_use_the_staff_endpoint(self):
        req = self.new_request()
        self.client.force_login(self.citizen)
        self.assertEqual(self.staff_post(req).status_code, 403)
        self.assertEqual(Comment.objects.count(), 0)

    def test_blank_officer_message_sends_nothing(self):
        req = self.new_request()
        self.client.force_login(self.named_officer)
        self.staff_post(req, "   ")
        self.assertEqual(Comment.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)


class CommentModelAndPageTests(CommentTestCase):
    def test_model_refuses_comment_on_resolved_request(self):
        req = self.resolved_request()
        with self.assertRaises(ValidationError):
            Comment(request=req, author=self.citizen, body="Hello").full_clean()

    def test_messages_are_listed_oldest_first(self):
        req = self.new_request()
        Comment.objects.create(request=req, author=self.citizen, body="first")
        Comment.objects.create(request=req, author=self.named_officer, body="second")
        self.assertEqual([c.body for c in req.comments.all()], ["first", "second"])

    def test_citizen_sees_officer_as_generic_name_admin_sees_real_name(self):
        req = self.new_request()
        Comment.objects.create(request=req, author=self.named_officer, body="Crew arrives Friday.")

        self.client.force_login(self.citizen)
        page = self.client.get(reverse("request_detail", args=[req.pk]))
        self.assertContains(page, "Crew arrives Friday.")
        self.assertContains(page, "Huduma officer")
        self.assertNotContains(page, "Grace Njeri")

        self.client.force_login(self.officer)
        page = self.client.get(reverse("panel:request_detail", args=[req.pk]))
        self.assertContains(page, "Grace Njeri")

    def test_message_form_is_hidden_once_resolved(self):
        req = self.resolved_request()
        self.client.force_login(self.citizen)
        page = self.client.get(reverse("request_detail", args=[req.pk]))
        self.assertFalse(page.context["can_comment"])
        self.assertNotContains(page, reverse("request_comment", args=[req.pk]))

    def test_comments_never_appear_on_the_public_tracking_page(self):
        req = self.new_request()
        Comment.objects.create(request=req, author=self.citizen, body="private words xyz")
        page = self.client.get(reverse("track"), {"ref": req.reference})
        self.assertNotContains(page, "private words xyz")