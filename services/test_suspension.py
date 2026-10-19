from django.urls import reverse

from .models import Comment, Feedback, ServiceRequest, Status
from .test_core import CoreTestCase

FORM = {
    "area": "Kenyatta Ave",
    "description": "Streetlight out for two weeks near the market.",
}


class SuspensionTestCase(CoreTestCase):
    def suspend(self, user, reason="Repeated false reports"):
        user.posting_suspended = True
        user.suspension_reason = reason
        user.save()

    def resolved_request(self, user=None):
        req = self.new_request(user=user)
        req.change_status(Status.IN_PROGRESS, self.officer)
        req.change_status(Status.RESOLVED, self.officer)
        return req

    def panel_post(self, user, **data):
        return self.client.post(reverse("panel:citizen_posting", args=[user.pk]), data)


class SuspendedCitizenTests(SuspensionTestCase):
    def setUp(self):
        super().setUp()
        self.suspend(self.citizen)
        self.client.force_login(self.citizen)

    def test_cannot_open_or_submit_the_report_form(self):
        self.assertRedirects(self.client.get(reverse("request_create")), reverse("dashboard"))
        data = dict(FORM, category=self.category.pk, county=self.county.pk)
        self.assertRedirects(self.client.post(reverse("request_create"), data), reverse("dashboard"))
        self.assertEqual(ServiceRequest.objects.count(), 0)

    def test_cannot_message(self):
        req = self.new_request()
        self.client.post(reverse("request_comment", args=[req.pk]), {"body": "Hello"})
        self.assertEqual(Comment.objects.count(), 0)

    def test_cannot_rate(self):
        req = self.resolved_request()
        self.client.post(reverse("request_feedback", args=[req.pk]), {"rating": "5"})
        self.assertEqual(Feedback.objects.count(), 0)

    def test_can_still_read_everything(self):
        req = self.new_request()
        for name, args in (("dashboard", []), ("request_list", []), ("request_detail", [req.pk]), ("request_receipt", [req.pk])):
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200, name)

    def test_banner_explains_the_suspension(self):
        page = self.client.get(reverse("dashboard"))
        self.assertContains(page, "Posting is suspended on your account")
        self.assertContains(page, "Repeated false reports")


class OtherUsersTests(SuspensionTestCase):
    def test_other_citizens_can_still_post(self):
        self.suspend(self.citizen)
        self.client.force_login(self.other)
        data = dict(FORM, category=self.category.pk, county=self.county.pk)
        self.assertEqual(self.client.post(reverse("request_create"), data).status_code, 302)
        self.assertEqual(ServiceRequest.objects.filter(user=self.other).count(), 1)

    def test_reinstated_citizen_can_post_again(self):
        self.suspend(self.citizen)
        self.citizen.posting_suspended = False
        self.citizen.save()
        self.client.force_login(self.citizen)
        data = dict(FORM, category=self.category.pk, county=self.county.pk)
        self.client.post(reverse("request_create"), data)
        self.assertEqual(ServiceRequest.objects.filter(user=self.citizen).count(), 1)


class StaffControlTests(SuspensionTestCase):
    def test_staff_can_suspend_with_a_reason(self):
        self.client.force_login(self.officer)
        self.panel_post(self.citizen, action="suspend", reason="  Repeated false reports  ")
        self.citizen.refresh_from_db()
        self.assertTrue(self.citizen.posting_suspended)
        self.assertEqual(self.citizen.suspension_reason, "Repeated false reports")

    def test_reason_is_capped_at_200_characters(self):
        self.client.force_login(self.officer)
        self.panel_post(self.citizen, action="suspend", reason="x" * 500)
        self.citizen.refresh_from_db()
        self.assertEqual(len(self.citizen.suspension_reason), 200)

    def test_staff_can_reinstate_and_the_reason_is_cleared(self):
        self.suspend(self.citizen)
        self.client.force_login(self.officer)
        self.panel_post(self.citizen, action="reinstate")
        self.citizen.refresh_from_db()
        self.assertFalse(self.citizen.posting_suspended)
        self.assertEqual(self.citizen.suspension_reason, "")

    def test_unknown_action_changes_nothing(self):
        self.client.force_login(self.officer)
        self.panel_post(self.citizen, action="delete")
        self.citizen.refresh_from_db()
        self.assertFalse(self.citizen.posting_suspended)

    def test_citizens_cannot_use_the_control(self):
        self.client.force_login(self.other)
        self.assertEqual(self.panel_post(self.citizen, action="suspend").status_code, 403)
        self.citizen.refresh_from_db()
        self.assertFalse(self.citizen.posting_suspended)

    def test_anonymous_is_sent_to_login(self):
        response = self.panel_post(self.citizen, action="suspend")
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_staff_accounts_cannot_be_suspended(self):
        self.client.force_login(self.officer)
        self.assertEqual(self.panel_post(self.officer, action="suspend").status_code, 404)

    def test_get_is_not_allowed(self):
        self.client.force_login(self.officer)
        response = self.client.get(reverse("panel:citizen_posting", args=[self.citizen.pk]))
        self.assertEqual(response.status_code, 405)

    def test_redirects_back_to_the_request_page(self):
        req = self.new_request()
        self.client.force_login(self.officer)
        response = self.panel_post(self.citizen, action="suspend", request=str(req.pk))
        self.assertRedirects(
            response, reverse("panel:request_detail", args=[req.pk]), fetch_redirect_response=False
        )

    def test_admin_request_page_shows_the_control(self):
        req = self.new_request()
        self.client.force_login(self.officer)
        page = self.client.get(reverse("panel:request_detail", args=[req.pk]))
        self.assertContains(page, "Suspend posting")
        self.suspend(self.citizen)
        page = self.client.get(reverse("panel:request_detail", args=[req.pk]))
        self.assertContains(page, "Reinstate posting")
