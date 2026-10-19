from django.core.exceptions import ValidationError
from django.urls import reverse

from .forms import ReportForm
from .models import ServiceRequest
from .test_core import CoreTestCase


class LocationTestCase(CoreTestCase):
    def form_data(self, **extra):
        data = {
            "category": self.category.pk,
            "county": self.county.pk,
            "area": "Kenyatta Ave",
            "description": "Streetlight out for two weeks near the market.",
        }
        data.update(extra)
        return data

    def pinned_request(self):
        return ServiceRequest.objects.create(
            user=self.citizen, category=self.category, county=self.county,
            area="Kenyatta Ave", description="Streetlight out for two weeks near the market.",
            latitude=-1.286389, longitude=36.817223,
        )


class LocationRuleTests(LocationTestCase):
    def test_pin_is_optional(self):
        form = ReportForm(self.form_data())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["latitude"])

    def test_valid_pin_is_accepted_and_rounded(self):
        form = ReportForm(self.form_data(latitude="-1.28638912345", longitude="36.81722399"))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["latitude"], -1.286389)
        self.assertEqual(form.cleaned_data["longitude"], 36.817224)

    def test_half_a_pin_is_rejected(self):
        self.assertFalse(ReportForm(self.form_data(latitude="-1.28")).is_valid())
        self.assertFalse(ReportForm(self.form_data(longitude="36.8")).is_valid())

    def test_pin_outside_kenya_is_rejected(self):
        form = ReportForm(self.form_data(latitude="51.5", longitude="-0.12"))
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_garbage_coordinates_are_rejected(self):
        for lat, lng in (("abc", "36.8"), ("nan", "36.8"), ("-1.2", "inf"), ("999", "36.8")):
            self.assertFalse(ReportForm(self.form_data(latitude=lat, longitude=lng)).is_valid(), (lat, lng))

    def test_model_clean_enforces_the_same_rules(self):
        req = self.new_request()
        req.latitude = -1.2
        with self.assertRaises(ValidationError):
            req.full_clean()
        req.longitude = 36.8
        req.full_clean()


class LocationViewTests(LocationTestCase):
    def test_report_view_saves_the_pin(self):
        self.client.force_login(self.citizen)
        response = self.client.post(
            reverse("request_create"), self.form_data(latitude="-1.286389", longitude="36.817223")
        )
        self.assertEqual(response.status_code, 302)
        saved = ServiceRequest.objects.get(user=self.citizen)
        self.assertEqual((saved.latitude, saved.longitude), (-1.286389, 36.817223))

    def test_report_view_works_without_a_pin(self):
        self.client.force_login(self.citizen)
        self.client.post(reverse("request_create"), self.form_data())
        self.assertIsNone(ServiceRequest.objects.get(user=self.citizen).latitude)

    def test_report_view_rejects_a_pin_outside_kenya(self):
        self.client.force_login(self.citizen)
        response = self.client.post(
            reverse("request_create"), self.form_data(latitude="51.5", longitude="-0.12")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ServiceRequest.objects.count(), 0)

    def test_citizen_detail_shows_map_only_when_pinned(self):
        plain, pinned = self.new_request(), self.pinned_request()
        self.client.force_login(self.citizen)
        self.assertNotContains(self.client.get(reverse("request_detail", args=[plain.pk])), 'id="location-map"')
        self.assertContains(self.client.get(reverse("request_detail", args=[pinned.pk])), 'id="location-map"')

    def test_admin_detail_shows_the_map(self):
        pinned = self.pinned_request()
        self.client.force_login(self.officer)
        self.assertContains(self.client.get(reverse("panel:request_detail", args=[pinned.pk])), 'id="location-map"')

    def test_public_tracking_never_exposes_coordinates(self):
        pinned = self.pinned_request()
        page = self.client.get(reverse("track"), {"ref": pinned.reference})
        self.assertNotContains(page, "-1.286")
        self.assertNotContains(page, "36.817")