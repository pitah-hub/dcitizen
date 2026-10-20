"""
Create demo accounts and sample requests so a fresh install has something to show.

Safe to run again: the accounts are created if missing and always end up active,
with the right role and the given password. Sample requests are created only once.

    python manage.py seed_demo
    python manage.py seed_demo --password "a-private-password"

Use --password (or the DEMO_PASSWORD environment variable) on any public site, so
the default below, which is published in the README, does not protect a live
staff account.
"""
import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from accounts.models import User
from services.models import Category, County, ServiceRequest, Status

DEFAULT_PASSWORD = "Demo-pass-123"

# email, full name, national id, phone, is_staff
ACCOUNTS = [
    ("officer@demo.local", "Grace Njeri", "90000001", "0700000001", True),
    ("amina@demo.local", "Amina Wanjiru", "90000002", "0711000002", False),
    ("brian@demo.local", "Brian Otieno", "90000003", "0722000003", False),
    ("cynthia@demo.local", "Cynthia Achieng", "90000004", "0733000004", False),
]

# category, county, area, description, pin (latitude, longitude) or None
SAMPLES = [
    ("Streetlight", "Embu", "Kenyatta Avenue near the market",
     "The streetlight has been out for two weeks and the road is dark at night.", (-0.5389, 37.4596)),
    ("Water", "Nairobi", "Pipeline Estate, Embakasi",
     "No water has come out of the taps for three days now.", (-1.3198, 36.9065)),
    ("Garbage Collection", "Kiambu", "Thika Road, near the stage",
     "Garbage has not been collected for over a week and it is piling up.", (-1.1714, 36.8356)),
    ("Roads", "Mombasa", "Nyali Road",
     "A large pothole near the roundabout is damaging vehicles.", (-4.0435, 39.6682)),
    ("Drainage", "Kisumu", "Milimani Road",
     "The drain is blocked and floods the road whenever it rains.", None),
    ("Streetlight", "Nakuru", "Lanet Road",
     "Three streetlights in a row are not working at night.", None),
    ("Water", "Meru", "Makutano market",
     "Water pressure is very low and the supply cuts off every evening.", None),
    ("Other", "Embu", "County hospital gate",
     "The pedestrian crossing paint has faded and cars do not stop.", (-0.5300, 37.4500)),
]


def _find(model, name):
    """Match a seeded name loosely, and fall back to any row so the command never fails."""
    return model.objects.filter(name__istartswith=name).first() or model.objects.first()


class Command(BaseCommand):
    help = "Create demo accounts and sample requests (safe to run again)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=os.environ.get("DEMO_PASSWORD", DEFAULT_PASSWORD),
            help="Password for every demo account (default: the one published in the README).",
        )

    def handle(self, *args, **options):
        password = options["password"]
        if not Category.objects.exists() or not County.objects.exists():
            call_command("seed_reference_data")

        officer, citizens = self._ensure_accounts(password)
        created = self._ensure_requests(officer, citizens)

        self.stdout.write(self.style.SUCCESS("Demo accounts are ready:"))
        for email, _name, _nid, _phone, is_staff in ACCOUNTS:
            role = "Officer" if is_staff else "Citizen"
            self.stdout.write(f"  {role:8} {email} / {password}")
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created {created} sample requests."))
        else:
            self.stdout.write("Sample requests already exist; none were created.")

    def _ensure_accounts(self, password):
        """Create or repair every demo account so it can always sign in."""
        officer, citizens = None, []
        for email, name, national_id, phone, is_staff in ACCOUNTS:
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={"full_name": name, "national_id": national_id, "phone": phone},
            )
            user.set_password(password)
            user.is_active = True
            user.is_staff = is_staff
            user.posting_suspended = False
            user.suspension_reason = ""
            user.save()
            if is_staff:
                officer = user
            else:
                citizens.append(user)
        return officer, citizens

    def _ensure_requests(self, officer, citizens):
        """Create the sample requests once, then walk them through the real workflow."""
        if ServiceRequest.objects.filter(user__in=citizens).exists():
            return 0
        total = len(SAMPLES) * 3
        for index in range(total):
            category_name, county_name, area, description, pin = SAMPLES[index % len(SAMPLES)]
            service_request = ServiceRequest.objects.create(
                user=citizens[index % len(citizens)],
                category=_find(Category, category_name),
                county=_find(County, county_name),
                area=area,
                description=description,
                latitude=pin[0] if pin else None,
                longitude=pin[1] if pin else None,
            )
            stage = index // len(SAMPLES)
            if stage >= 1:
                service_request.change_status(Status.IN_PROGRESS, officer, "Assigned to a crew.")
            if stage >= 2:
                service_request.change_status(Status.RESOLVED, officer, "Work completed.")
        return total
