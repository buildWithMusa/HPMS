from django.core.management.base import BaseCommand
from inventory.models import StockLocation


class Command(BaseCommand):
    help = "Create the central pharmacy stock location."

    def handle(self, *args, **options):
        location, created = StockLocation.objects.get_or_create(
            location_type=StockLocation.LocationType.CENTRAL,
            defaults={
                "name": "Central Pharmacy",
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS("Central Pharmacy location created.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("Central Pharmacy location already exists.")
            )
