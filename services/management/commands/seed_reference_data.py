"""Seed the fixed Kenyan county and service-category reference data."""
from django.core.management.base import BaseCommand

from services.models import Category, County


COUNTIES = [
    "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu",
    "Garissa", "Homa Bay", "Isiolo", "Kajiado", "Kakamega", "Kericho",
    "Kiambu", "Kilifi", "Kirinyaga", "Kisii", "Kisumu", "Kitui", "Kwale",
    "Laikipia", "Lamu", "Machakos", "Makueni", "Mandera", "Marsabit",
    "Meru", "Migori", "Mombasa", "Murang'a", "Nairobi", "Nakuru", "Nandi",
    "Narok", "Nyamira", "Nyandarua", "Nyeri", "Samburu", "Siaya", "Taita-Taveta",
    "Tana River", "Tharaka-Nithi", "Trans Nzoia", "Turkana", "Uasin Gishu",
    "Vihiga", "Wajir", "West Pokot",
]

CATEGORIES = [
    ("Streetlight", "bi-lightbulb"),
    ("Water", "bi-droplet"),
    ("Garbage Collection", "bi-trash"),
    ("Roads", "bi-cone-striped"),
    ("Drainage", "bi-water"),
    ("Other", "bi-three-dots"),
]


class Command(BaseCommand):
    help = "Create the fixed county and service-category reference data."

    def handle(self, *args, **options):
        """Create missing reference data without altering existing records."""
        if len(COUNTIES) != 47:
            raise ValueError("The Kenyan county seed list must contain exactly 47 counties.")

        counties_created = 0
        for county_name in COUNTIES:
            _, created = County.objects.get_or_create(name=county_name)
            counties_created += created

        categories_created = 0
        for category_name, icon in CATEGORIES:
            _, created = Category.objects.get_or_create(
                name=category_name,
                defaults={"icon": icon},
            )
            categories_created += created

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {counties_created} counties and {categories_created} categories."
            )
        )
