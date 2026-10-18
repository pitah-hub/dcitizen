"""Integration tests for citizen, staff, and public request views."""
import io
import tempfile

from PIL import Image
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from services.models import Category, County, ServiceRequest, Status


class ServiceViewTests(TestCase):
    """Verify owner scoping, workflow actions, emails, and public privacy."""

    def setUp(self):
        self.category = Category.objects.create(name="Streetlight")
        self.water = Category.objects.create(name="Water")
        self.county = County.objects.create(name="Nairobi")
        self.citizen = self.make_user("maya@example.com", "12345678", "Maya Citizen")
        self.other = self.make_user("other@example.com", "87654321", "Other Citizen")
        self.officer = self.make_user("officer@example.com", "11111111", "Panel Officer", True)

    def make_user(self, email, national_id, full_name, staff=False):
        """Create a user with credentials shared by these client tests."""
        return User.objects.create_user(
            email,
            "Safe-pass-123",
            full_name=full_name,
            national_id=national_id,
            phone="0712345678",
            is_staff=staff,
        )

    def create_request(self, user=None, category=None):
        """Create a valid request using the normal model save path."""
        return ServiceRequest.objects.create(
            user=user or self.citizen,
            category=category or self.category,
            county=self.county,
            area="Kenyatta Avenue",
            description="The streetlight has been off for more than two weeks.",
        )

    def image_upload(self):
        """Build a real in-memory PNG for the upload form."""
        image_data = io.BytesIO()
        Image.new("RGB", (1, 1), "green").save(image_data, format="PNG")
        return SimpleUploadedFile("issue.png", image_data.getvalue(), content_type="image/png")

    def test_anonymous_citizen_page_redirects_to_login(self):
        """Reporting requires authentication."""
        response = self.client.get(reverse("request_create"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('request_create')}")

    def test_citizen_cannot_open_another_citizens_request(self):
        """Foreign request IDs return 404 so the id is not revealed."""
        request = self.create_request(user=self.other)
        self.client.force_login(self.citizen)
        self.assertEqual(self.client.get(reverse("request_detail", args=[request.pk])).status_code, 404)

    def test_citizen_cannot_access_staff_panel(self):
        """The staff panel returns 403 to authenticated citizens."""
        self.client.force_login(self.citizen)
        self.assertEqual(self.client.get(reverse("panel:dashboard")).status_code, 403)

    def test_submission_creates_request_history_and_email(self):
        """Submitting a report stores its timeline entry and sends one email."""
        self.client.force_login(self.citizen)
        response = self.client.post(
            reverse("request_create"),
            {
                "category": self.category.pk,
                "county": self.county.pk,
                "area": "Kenyatta Avenue",
                "description": "The streetlight has been off for more than two weeks.",
            },
        )
        request = ServiceRequest.objects.get(user=self.citizen)
        self.assertRedirects(response, reverse("request_detail", args=[request.pk]))
        self.assertEqual(request.history.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_image_upload_uses_configured_media_root(self):
        """A valid optional image is accepted during report submission."""
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            self.client.force_login(self.citizen)
            response = self.client.post(
                reverse("request_create"),
                {
                    "category": self.category.pk,
                    "county": self.county.pk,
                    "area": "Kenyatta Avenue",
                    "description": "The streetlight has been off for more than two weeks.",
                    "image": self.image_upload(),
                },
            )
            self.assertEqual(response.status_code, 302)
            self.assertTrue(ServiceRequest.objects.get(user=self.citizen).image.name)

    def test_staff_status_change_sends_email_and_rejects_skipping_step(self):
        """Staff updates use the model workflow and notify the request owner."""
        request = self.create_request()
        self.client.force_login(self.officer)
        invalid = self.client.post(
            reverse("panel:request_detail", args=[request.pk]),
            {"new_status": Status.RESOLVED, "note": "Not allowed yet."},
        )
        request.refresh_from_db()
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(request.status, Status.PENDING)
        response = self.client.post(
            reverse("panel:request_detail", args=[request.pk]),
            {"new_status": Status.IN_PROGRESS, "note": "Crew dispatched."},
        )
        request.refresh_from_db()
        self.assertRedirects(response, reverse("panel:request_detail", args=[request.pk]))
        self.assertEqual(request.status, Status.IN_PROGRESS)
        self.assertEqual(len(mail.outbox), 1)

    def test_public_tracking_hides_personal_and_request_content(self):
        """A public result exposes progress metadata only."""
        request = self.create_request()
        response = self.client.get(reverse("track"), {"ref": request.reference})
        self.assertContains(response, request.reference)
        self.assertNotContains(response, request.description)
        self.assertNotContains(response, self.citizen.full_name)
        self.assertNotContains(response, self.citizen.email)

    def test_admin_filters_and_search(self):
        """Staff can narrow requests by status and citizen name."""
        mine = self.create_request()
        other = self.create_request(user=self.other, category=self.water)
        other.change_status(Status.IN_PROGRESS, self.officer)
        self.client.force_login(self.officer)
        response = self.client.get(
            reverse("panel:request_list"), {"status": Status.PENDING, "q": "Maya"}
        )
        self.assertContains(response, mine.reference)
        self.assertNotContains(response, other.reference)
