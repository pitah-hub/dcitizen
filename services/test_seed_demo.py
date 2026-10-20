from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Category, County, Feedback, ServiceRequest, Status

PASSWORD = "Test-pass-123"
EMAILS = ["officer@demo.local", "amina@demo.local", "brian@demo.local", "cynthia@demo.local"]


def run_seed(**options):
    options.setdefault("password", PASSWORD)
    call_command("seed_demo", stdout=StringIO(), **options)


class SeedDemoTests(TestCase):
    def test_every_demo_account_can_sign_in(self):
        run_seed()
        for email in EMAILS:
            self.assertTrue(self.client.login(username=email, password=PASSWORD), email)

    def test_officer_is_staff_and_reaches_the_panel(self):
        run_seed()
        self.client.login(username="officer@demo.local", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("panel:dashboard")).status_code, 200)

    def test_citizens_are_not_staff(self):
        run_seed()
        self.assertFalse(User.objects.filter(email__in=EMAILS[1:], is_staff=True).exists())
        self.assertTrue(User.objects.get(email=EMAILS[0]).is_staff)

    def test_sample_requests_cover_every_status(self):
        run_seed()
        counts = {s: ServiceRequest.objects.filter(status=s).count() for s in Status.values}
        self.assertEqual(counts, {"PENDING": 8, "IN_PROGRESS": 8, "RESOLVED": 8})

    def test_history_is_complete_for_resolved_requests(self):
        run_seed()
        resolved = ServiceRequest.objects.filter(status=Status.RESOLVED).first()
        self.assertEqual(
            [h.new_status for h in resolved.history.all()],
            [Status.PENDING, Status.IN_PROGRESS, Status.RESOLVED],
        )

    def test_running_twice_does_not_duplicate_anything(self):
        run_seed()
        run_seed()
        self.assertEqual(User.objects.count(), 4)
        self.assertEqual(ServiceRequest.objects.count(), 24)

    def test_rerun_repairs_a_broken_account(self):
        run_seed()
        officer = User.objects.get(email="officer@demo.local")
        officer.set_password("something-else")
        officer.is_active = False
        officer.is_staff = False
        officer.save()
        citizen = User.objects.get(email="amina@demo.local")
        citizen.posting_suspended = True
        citizen.suspension_reason = "test"
        citizen.save()

        run_seed()
        self.assertTrue(self.client.login(username="officer@demo.local", password=PASSWORD))
        self.assertTrue(User.objects.get(email="officer@demo.local").is_staff)
        citizen.refresh_from_db()
        self.assertFalse(citizen.posting_suspended)

    def test_custom_password_replaces_the_default(self):
        run_seed()
        run_seed(password="Another-private-pass-9")
        self.assertFalse(self.client.login(username="officer@demo.local", password=PASSWORD))
        self.assertTrue(self.client.login(username="officer@demo.local", password="Another-private-pass-9"))

    def test_pinned_requests_pass_the_location_rules(self):
        run_seed()
        pinned = ServiceRequest.objects.exclude(latitude=None)
        self.assertTrue(pinned.exists())
        for service_request in pinned:
            service_request.full_clean()

    def test_creates_reference_data_when_it_is_missing(self):
        self.assertFalse(Category.objects.exists() or County.objects.exists())
        run_seed()
        self.assertTrue(County.objects.exists())
        self.assertTrue(Category.objects.exists())

    def test_feedback_seed_works_on_top_of_the_demo_data(self):
        run_seed()
        call_command("seed_demo_feedback", stdout=StringIO())
        self.assertEqual(Feedback.objects.count(), 8)
