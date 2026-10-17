"""View tests for public registration and authentication behaviour."""
from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class AccountViewTests(TestCase):
    """Exercise registration and role-aware login redirects."""

    def test_registration_redirects_to_citizen_dashboard(self):
        """A new citizen is authenticated and sent to the dashboard."""
        response = self.client.post(
            reverse("register"),
            {
                "full_name": "Maya Citizen",
                "national_id": "12345678",
                "email": "maya@example.com",
                "phone": "0712345678",
                "password1": "Safe-pass-123",
                "password2": "Safe-pass-123",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(User.objects.get(email="maya@example.com").is_staff)

    def test_login_routes_staff_to_panel(self):
        """A staff member lands on the staff panel after the dashboard handoff."""
        User.objects.create_user(
            "officer@example.com",
            "Safe-pass-123",
            full_name="Panel Officer",
            national_id="87654321",
            phone="0712345678",
            is_staff=True,
        )
        response = self.client.post(
            reverse("login"),
            {"username": "officer@example.com", "password": "Safe-pass-123"},
            follow=True,
        )
        self.assertEqual(response.redirect_chain[-1][0], reverse("panel:dashboard"))
