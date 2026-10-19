from django.urls import reverse

from .test_core import CoreTestCase


class ReceiptTests(CoreTestCase):
    def test_owner_gets_a_receipt_with_the_key_details(self):
        req = self.new_request()
        self.client.force_login(self.citizen)
        page = self.client.get(reverse("request_receipt", args=[req.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, req.reference)
        self.assertContains(page, "Pending")
        self.assertContains(page, "Streetlight")
        self.assertContains(page, "Embu")
        self.assertContains(page, f"ref={req.reference}")

    def test_receipt_shows_a_readable_status_not_the_raw_code(self):
        req = self.new_request()
        req.change_status("IN_PROGRESS", self.officer)
        self.client.force_login(self.citizen)
        page = self.client.get(reverse("request_receipt", args=[req.pk]))
        self.assertContains(page, "In Progress")
        self.assertNotContains(page, "IN_PROGRESS")

    def test_receipt_leaves_out_the_national_id(self):
        req = self.new_request()
        self.client.force_login(self.citizen)
        self.assertNotContains(self.client.get(reverse("request_receipt", args=[req.pk])), self.citizen.national_id)

    def test_other_citizen_gets_404(self):
        req = self.new_request()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("request_receipt", args=[req.pk])).status_code, 404)

    def test_anonymous_is_sent_to_login(self):
        req = self.new_request()
        response = self.client.get(reverse("request_receipt", args=[req.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_staff_are_redirected_to_the_panel(self):
        req = self.new_request()
        self.client.force_login(self.officer)
        response = self.client.get(reverse("request_receipt", args=[req.pk]))
        self.assertRedirects(response, reverse("panel:dashboard"), fetch_redirect_response=False)

    def test_citizen_detail_page_links_to_the_receipt(self):
        req = self.new_request()
        self.client.force_login(self.citizen)
        page = self.client.get(reverse("request_detail", args=[req.pk]))
        self.assertContains(page, reverse("request_receipt", args=[req.pk]))