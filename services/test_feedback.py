from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from .analytics import feedback_stats
from .models import Feedback, Status
from .test_core import CoreTestCase


class FeedbackTestCase(CoreTestCase):
    def resolved_request(self, user=None):
        req = self.new_request(user=user)
        req.change_status(Status.IN_PROGRESS, self.officer)
        req.change_status(Status.RESOLVED, self.officer)
        return req

    def post_feedback(self, req, **data):
        return self.client.post(reverse("request_feedback", args=[req.pk]), data)


class FeedbackModelTests(FeedbackTestCase):
    def test_rating_must_be_between_1_and_5(self):
        req = self.resolved_request()
        for bad in (0, 6):
            with self.assertRaises(ValidationError):
                Feedback(request=req, rating=bad).full_clean()
        Feedback(request=req, rating=3).full_clean()

    def test_database_also_rejects_out_of_range_rating(self):
        req = self.resolved_request()
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Feedback.objects.create(request=req, rating=9)

    def test_only_one_feedback_per_request(self):
        req = self.resolved_request()
        Feedback.objects.create(request=req, rating=4)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Feedback.objects.create(request=req, rating=1)

    def test_unresolved_request_cannot_be_rated(self):
        req = self.new_request()
        with self.assertRaises(ValidationError):
            Feedback(request=req, rating=5).full_clean()

    def test_can_receive_feedback_property(self):
        pending = self.new_request()
        resolved = self.resolved_request()
        self.assertFalse(pending.can_receive_feedback)
        self.assertTrue(resolved.can_receive_feedback)
        Feedback.objects.create(request=resolved, rating=5)
        self.assertFalse(resolved.can_receive_feedback)


class FeedbackViewTests(FeedbackTestCase):
    def test_owner_can_rate_a_resolved_request(self):
        req = self.resolved_request()
        self.client.force_login(self.citizen)
        response = self.post_feedback(req, rating="4", comment="Quick fix.")
        self.assertRedirects(response, reverse("request_detail", args=[req.pk]))
        feedback = Feedback.objects.get(request=req)
        self.assertEqual((feedback.rating, feedback.comment), (4, "Quick fix."))

    def test_comment_is_optional(self):
        req = self.resolved_request()
        self.client.force_login(self.citizen)
        self.post_feedback(req, rating="5")
        self.assertEqual(Feedback.objects.get(request=req).comment, "")

    def test_other_citizen_gets_404_and_nothing_is_saved(self):
        req = self.resolved_request()
        self.client.force_login(self.other)
        self.assertEqual(self.post_feedback(req, rating="1").status_code, 404)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_pending_request_cannot_be_rated(self):
        req = self.new_request()
        self.client.force_login(self.citizen)
        self.post_feedback(req, rating="5")
        self.assertEqual(Feedback.objects.count(), 0)

    def test_second_submission_does_not_overwrite(self):
        req = self.resolved_request()
        self.client.force_login(self.citizen)
        self.post_feedback(req, rating="5", comment="First.")
        self.post_feedback(req, rating="1", comment="Second.")
        feedback = Feedback.objects.get(request=req)
        self.assertEqual((feedback.rating, feedback.comment), (5, "First."))

    def test_invalid_ratings_are_rejected(self):
        req = self.resolved_request()
        self.client.force_login(self.citizen)
        for bad in ("7", "0", "abc", ""):
            self.post_feedback(req, rating=bad)
        self.post_feedback(req, comment="No rating given.")
        self.assertEqual(Feedback.objects.count(), 0)

    def test_overlong_comment_is_rejected(self):
        req = self.resolved_request()
        self.client.force_login(self.citizen)
        self.post_feedback(req, rating="3", comment="x" * 501)
        self.assertEqual(Feedback.objects.count(), 0)

    def test_staff_cannot_submit_feedback(self):
        req = self.resolved_request()
        self.client.force_login(self.officer)
        self.post_feedback(req, rating="5")
        self.assertEqual(Feedback.objects.count(), 0)

    def test_anonymous_is_redirected_to_login(self):
        req = self.resolved_request()
        response = self.post_feedback(req, rating="5")
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])
        self.assertEqual(Feedback.objects.count(), 0)

    def test_get_is_not_allowed(self):
        req = self.resolved_request()
        self.client.force_login(self.citizen)
        response = self.client.get(reverse("request_feedback", args=[req.pk]))
        self.assertEqual(response.status_code, 405)


class FeedbackPageTests(FeedbackTestCase):
    def test_detail_page_offers_the_form_only_when_allowed(self):
        pending = self.new_request()
        resolved = self.resolved_request()
        self.client.force_login(self.citizen)

        page = self.client.get(reverse("request_detail", args=[pending.pk]))
        self.assertFalse(page.context["can_give_feedback"])
        self.assertNotContains(page, reverse("request_feedback", args=[pending.pk]))

        page = self.client.get(reverse("request_detail", args=[resolved.pk]))
        self.assertTrue(page.context["can_give_feedback"])
        self.assertContains(page, reverse("request_feedback", args=[resolved.pk]))

    def test_form_disappears_after_rating(self):
        req = self.resolved_request()
        self.client.force_login(self.citizen)
        self.post_feedback(req, rating="4", comment="Thanks.")
        page = self.client.get(reverse("request_detail", args=[req.pk]))
        self.assertFalse(page.context["can_give_feedback"])
        self.assertNotContains(page, reverse("request_feedback", args=[req.pk]))
        self.assertContains(page, "Your feedback")

    def test_admin_dashboard_gets_feedback_stats(self):
        req = self.resolved_request()
        Feedback.objects.create(request=req, rating=4, comment="Good.")
        self.client.force_login(self.officer)
        page = self.client.get(reverse("panel:dashboard"))
        self.assertEqual(page.context["feedback"]["count"], 1)
        self.assertEqual(page.context["feedback"]["average"], 4.0)
        self.assertContains(page, "Citizen satisfaction")

    def test_admin_request_page_shows_feedback(self):
        req = self.resolved_request()
        Feedback.objects.create(request=req, rating=2, comment="Came back after a week.")
        self.client.force_login(self.officer)
        page = self.client.get(reverse("panel:request_detail", args=[req.pk]))
        self.assertContains(page, "Came back after a week.")


class FeedbackAnalyticsTests(FeedbackTestCase):
    def test_empty_state(self):
        stats = feedback_stats()
        self.assertEqual((stats["count"], stats["average"], stats["average_stars"]), (0, None, 0))
        self.assertEqual(stats["by_category"], [])

    def test_summary_numbers(self):
        for rating, comment in ((5, "Great."), (4, ""), (2, "Poor.")):
            Feedback.objects.create(request=self.resolved_request(), rating=rating, comment=comment)
        stats = feedback_stats()
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["average"], 3.7)
        self.assertEqual(stats["average_stars"], 4)
        self.assertEqual(stats["low_count"], 1)

    def test_latest_comments_skip_empty_ones(self):
        Feedback.objects.create(request=self.resolved_request(), rating=5, comment="")
        Feedback.objects.create(request=self.resolved_request(), rating=3, comment="Okay.")
        comments = [item.comment for item in feedback_stats()["latest_comments"]]
        self.assertEqual(comments, ["Okay."])

    def test_category_averages_list_lowest_first(self):
        from .models import Category, ServiceRequest

        water = Category.objects.get(name="Water")
        for rating in (5, 5):
            Feedback.objects.create(request=self.resolved_request(), rating=rating)
        slow = ServiceRequest.objects.create(
            user=self.citizen, category=water, county=self.county,
            area="Moi Rd", description="Tap has been dry for three days now.",
        )
        slow.change_status(Status.IN_PROGRESS, self.officer)
        slow.change_status(Status.RESOLVED, self.officer)
        Feedback.objects.create(request=slow, rating=1)
        rows = feedback_stats()["by_category"]
        self.assertEqual([row["name"] for row in rows], ["Water", "Streetlight"])
        self.assertEqual(rows[0]["avg"], 1.0)