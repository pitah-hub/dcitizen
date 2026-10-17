"""Create deterministic demo accounts and service requests."""
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from services.models import Category, County, ServiceRequest, Status


DEMO_PASSWORD = "Demo-pass-123"
OFFICER_EMAIL = "officer@demo.local"
DEMO_USERS = [
    ("amina@demo.local", "Amina Wanjiku", "20000001", "0712345678"),
    ("brian@demo.local", "Brian Otieno", "20000002", "0712345679"),
    ("cynthia@demo.local", "Cynthia Mutua", "20000003", "0712345680"),
]


class Command(BaseCommand):
    help = "Create a staff officer, three citizens, and 25 demo service requests."

    def handle(self, *args, **options):
        """Seed a stable demo dataset without duplicating it on later runs."""
        if User.objects.filter(email=OFFICER_EMAIL).exists():
            self.stdout.write("Demo users already exist; no demo data was created.")
            return
        categories = list(Category.objects.all())
        counties = list(County.objects.all())
        if not categories or not counties:
            raise CommandError("Run seed_reference_data before seed_demo.")

        officer = User.objects.create_user(
            OFFICER_EMAIL,
            DEMO_PASSWORD,
            full_name="Grace Officer",
            national_id="20000000",
            phone="0712345670",
            is_staff=True,
        )
        citizens = [
            User.objects.create_user(email, DEMO_PASSWORD, full_name=name, national_id=national_id, phone=phone)
            for email, name, national_id, phone in DEMO_USERS
        ]
        descriptions = [
            "This public-service issue has affected residents for several days and needs attention.",
            "The reported problem is causing disruption in the area and requires a service response.",
            "Residents have requested assistance because this issue remains unresolved near the landmark.",
        ]
        for index in range(25):
            service_request = ServiceRequest.objects.create(
                user=citizens[index % len(citizens)],
                category=categories[index % len(categories)],
                county=counties[index % len(counties)],
                area=f"Demo area {index + 1}",
                description=descriptions[index % len(descriptions)],
            )
            if index % 3 >= 1:
                service_request.change_status(Status.IN_PROGRESS, officer, "Officer assigned to investigate.")
            if index % 3 == 2:
                service_request.change_status(Status.RESOLVED, officer, "Issue addressed by the service team.")

        self.stdout.write(self.style.SUCCESS("Created 1 officer, 3 citizens, and 25 demo requests."))
        self.stdout.write(f"Officer: {OFFICER_EMAIL} / {DEMO_PASSWORD}")
        for email, _, _, _ in DEMO_USERS:
            self.stdout.write(f"Citizen: {email} / {DEMO_PASSWORD}")
