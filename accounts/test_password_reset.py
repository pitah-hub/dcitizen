import re

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import User

OLD_PASSWORD = "OldPass-12345"
NEW_PASSWORD = "Brand-New-Pass-9"


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "amina@x.com", OLD_PASSWORD, full_name="Amina Wanjiru",
            national_id="12345678", phone="0712345678",
        )

    def request_reset(self, email="amina@x.com"):
        return self.client.post(reverse("password_reset"), {"email": email})

    def emailed_link(self):
        self.request_reset()
        return re.search(r"https?://testserver(/reset/\S+)", mail.outbox[-1].body).group(1)

    def test_form_page_loads(self):
        self.assertContains(self.client.get(reverse("password_reset")), "Forgot your password?")

    def test_known_email_receives_a_link(self):
        response = self.request_reset()
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["amina@x.com"])
        self.assertIn("/reset/", mail.outbox[0].body)

    def test_email_match_ignores_case(self):
        self.request_reset("AMINA@X.COM")
        self.assertEqual(len(mail.outbox), 1)

    def test_unknown_email_gets_the_same_response_and_no_email(self):
        response = self.request_reset("nobody@x.com")
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_inactive_account_gets_no_email(self):
        self.user.is_active = False
        self.user.save()
        self.request_reset()
        self.assertEqual(len(mail.outbox), 0)

    def test_suspended_citizen_can_still_reset(self):
        self.user.posting_suspended = True
        self.user.save()
        self.request_reset()
        self.assertEqual(len(mail.outbox), 1)

    def test_full_flow_changes_the_password(self):
        link = self.emailed_link()
        page = self.client.get(link, follow=True)
        self.assertTrue(page.context["validlink"])
        response = self.client.post(
            page.request["PATH_INFO"],
            {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
        )
        self.assertRedirects(response, reverse("password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertFalse(self.user.check_password(OLD_PASSWORD))
        self.assertTrue(self.client.login(username="amina@x.com", password=NEW_PASSWORD))

    def test_link_works_only_once(self):
        link = self.emailed_link()
        page = self.client.get(link, follow=True)
        self.client.post(
            page.request["PATH_INFO"],
            {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
        )
        reused = self.client.get(link, follow=True)
        self.assertFalse(reused.context["validlink"])

    def test_tampered_link_is_rejected(self):
        link = self.emailed_link()
        uid = link.split("/")[2]
        bad = self.client.get(f"/reset/{uid}/not-a-real-token/", follow=True)
        self.assertEqual(bad.status_code, 200)
        self.assertFalse(bad.context["validlink"])

    def test_weak_password_is_rejected(self):
        link = self.emailed_link()
        page = self.client.get(link, follow=True)
        response = self.client.post(
            page.request["PATH_INFO"], {"new_password1": "12345678", "new_password2": "12345678"}
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PASSWORD))

    def test_mismatched_passwords_are_rejected(self):
        link = self.emailed_link()
        page = self.client.get(link, follow=True)
        response = self.client.post(
            page.request["PATH_INFO"], {"new_password1": NEW_PASSWORD, "new_password2": "Different-Pass-7"}
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD_PASSWORD))
