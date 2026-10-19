"""Add sample satisfaction ratings so the admin dashboard has data to show. Safe to re-run."""
from django.core.management.base import BaseCommand

from services.models import Feedback, ServiceRequest, Status

SAMPLES = [
    (5, "Fixed quickly, thank you."),
    (4, "Good result, took a bit longer than expected."),
    (5, ""),
    (2, "The problem came back after a week."),
    (4, ""),
    (3, "Fixed, but nobody told me when the crew was coming."),
    (5, "Very helpful officer."),
    (1, "Marked resolved but the problem is still there."),
]


class Command(BaseCommand):
    help = "Create sample feedback on up to 8 of the oldest resolved requests (does nothing if any feedback exists)."

    def handle(self, *args, **options):
        if Feedback.objects.exists():
            self.stdout.write("Feedback already exists; nothing was created.")
            return
        unrated = list(
            ServiceRequest.objects.filter(status=Status.RESOLVED, feedback__isnull=True)
            .order_by("id")[: len(SAMPLES)]
        )
        for service_request, (rating, comment) in zip(unrated, SAMPLES):
            Feedback.objects.create(request=service_request, rating=rating, comment=comment)
        self.stdout.write(self.style.SUCCESS(f"Created {len(unrated)} feedback entries."))