from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponse
from django.test import RequestFactory, TestCase

from accounts.forms import RegistrationForm
from accounts.models import User

from .analytics import citizen_stats, dashboard_stats
from .forms import ReportForm, StatusChangeForm
from .models import Category, County, ServiceRequest, Status, is_valid_transition
from .notifications import send_status_email, send_submission_email
from .permissions import get_owned_request, staff_required


def make_user(email, national_id, staff=False):
    return User.objects.create_user(
        email, "pass12345", full_name="Test User", national_id=national_id,
        phone="0712345678", is_staff=staff,
    )


class CoreTestCase(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Streetlight")
        self.unused_category = Category.objects.create(name="Water")
        self.county = County.objects.create(name="Embu")
        self.citizen = make_user("a@x.com", "12345678")
        self.other = make_user("b@x.com", "87654321")
        self.officer = make_user("o@x.com", "11111111", staff=True)

    def new_request(self, user=None):
        return ServiceRequest.objects.create(
            user=user or self.citizen, category=self.category, county=self.county,
            area="Kenyatta Ave", description="Streetlight out for two weeks near the market.",
        )


class WorkflowTests(CoreTestCase):
    def test_new_request_gets_reference_and_first_history_entry(self):
        req = self.new_request()
        req.refresh_from_db()
        self.assertRegex(req.reference, r"^SR-\d{4}-\d{4}$")
        self.assertEqual(req.status, Status.PENDING)
        self.assertEqual(req.history.count(), 1)

    def test_full_valid_flow_logs_every_step(self):
        req = self.new_request()
        req.change_status(Status.IN_PROGRESS, self.officer, "Crew dispatched.")
        req.change_status(Status.RESOLVED, self.officer)
        self.assertFalse(req.is_open)
        self.assertEqual(
            [h.new_status for h in req.history.all()],
            [Status.PENDING, Status.IN_PROGRESS, Status.RESOLVED],
        )

    def test_illegal_transitions_are_blocked(self):
        req = self.new_request()
        for bad in (Status.RESOLVED, Status.PENDING, "GARBAGE"):
            with self.assertRaises(ValidationError):
                req.change_status(bad, self.officer)
        req.change_status(Status.IN_PROGRESS, self.officer)
        req.change_status(Status.RESOLVED, self.officer)
        with self.assertRaises(ValidationError):
            req.change_status(Status.IN_PROGRESS, self.officer)
        self.assertEqual(req.history.count(), 3)

    def test_transition_rule_function(self):
        self.assertTrue(is_valid_transition("PENDING", "IN_PROGRESS"))
        self.assertFalse(is_valid_transition("PENDING", "RESOLVED"))
        self.assertFalse(is_valid_transition("RESOLVED", "PENDING"))


class FormTests(CoreTestCase):
    def test_status_form_only_offers_next_step(self):
        req = self.new_request()
        form = StatusChangeForm(service_request=req)
        self.assertEqual([c[0] for c in form.fields["new_status"].choices], ["IN_PROGRESS"])
        self.assertTrue(form.can_change)

    def test_status_form_hidden_when_resolved(self):
        req = self.new_request()
        req.change_status(Status.IN_PROGRESS, self.officer)
        req.change_status(Status.RESOLVED, self.officer)
        self.assertFalse(StatusChangeForm(service_request=req).can_change)

    def test_status_form_rejects_skipping_a_step(self):
        form = StatusChangeForm({"new_status": "RESOLVED"}, service_request=self.new_request())
        self.assertFalse(form.is_valid())

    def test_report_form_validates_description_length(self):
        form = ReportForm({
            "category": self.category.pk, "county": self.county.pk,
            "area": "x", "description": "too short",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)

    def test_report_form_hides_inactive_categories(self):
        self.unused_category.is_active = False
        self.unused_category.save()
        self.assertNotIn(self.unused_category, ReportForm().fields["category"].queryset)

    def test_registration_rejects_duplicate_email_any_case(self):
        form = RegistrationForm({
            "full_name": "New Person", "national_id": "22222222", "email": "A@X.com",
            "phone": "0712345678", "password1": "Str0ng-pass-99", "password2": "Str0ng-pass-99",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_registration_creates_citizen_not_staff(self):
        form = RegistrationForm({
            "full_name": "New Person", "national_id": "22222222", "email": "New@X.com",
            "phone": "+254712345678", "password1": "Str0ng-pass-99", "password2": "Str0ng-pass-99",
        })
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, "new@x.com")
        self.assertFalse(user.is_staff)


class AnalyticsTests(CoreTestCase):
    def test_dashboard_and_citizen_counts(self):
        a = self.new_request()
        b = self.new_request()
        self.new_request(user=self.other)
        b.change_status(Status.IN_PROGRESS, self.officer)
        a.change_status(Status.IN_PROGRESS, self.officer)
        a.change_status(Status.RESOLVED, self.officer)

        stats = dashboard_stats()
        self.assertEqual(
            (stats["total"], stats["pending"], stats["in_progress"], stats["resolved"], stats["open"]),
            (3, 1, 1, 1, 2),
        )
        names = {row["name"]: row["total"] for row in stats["by_category"]}
        self.assertEqual(names, {"Streetlight": 3, "Water": 0})

        mine = citizen_stats(self.citizen)
        self.assertEqual((mine["total"], mine["open"], mine["resolved"]), (2, 1, 1))

    def test_empty_database_gives_zeros(self):
        self.assertEqual(dashboard_stats()["total"], 0)


class PermissionTests(CoreTestCase):
    def test_owner_scoping(self):
        req = self.new_request()
        self.assertEqual(get_owned_request(self.citizen, req.pk), req)
        with self.assertRaises(Http404):
            get_owned_request(self.other, req.pk)
        self.assertEqual(ServiceRequest.objects.for_user(self.other).count(), 0)

    def test_staff_required_blocks_citizens(self):
        view = staff_required(lambda request: HttpResponse("ok"))
        request = RequestFactory().get("/")
        request.user = self.citizen
        with self.assertRaises(PermissionDenied):
            view(request)
        request.user = self.officer
        self.assertEqual(view(request).status_code, 200)


class NotificationTests(CoreTestCase):
    def test_submission_and_status_emails(self):
        req = self.new_request()
        send_submission_email(req)
        update = req.change_status(Status.IN_PROGRESS, self.officer, "Crew dispatched.")
        send_status_email(req, update)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, ["a@x.com"])
        self.assertIn(req.reference, mail.outbox[0].subject)
        self.assertIn("Crew dispatched.", mail.outbox[1].body)
