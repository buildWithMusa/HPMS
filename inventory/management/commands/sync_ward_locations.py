from django.core.management.base import BaseCommand

from hospital.models import Ward
from inventory.models import StockLocation


class Command(BaseCommand):
    help = "Create inventory locations for active hospital wards."

    def handle(self, *args, **options):
        created_count = 0

        wards = Ward.objects.filter(is_active=True)

        for ward in wards:
            location, created = StockLocation.objects.get_or_create(
                ward=ward,
                defaults={
                    "name": ward.name,
                    "location_type": StockLocation.LocationType.WARD,
                    "is_active": True,
                },
            )

            if not created:
                changed = False

                if location.name != ward.name:
                    location.name = ward.name
                    changed = True

                if not location.is_active:
                    location.is_active = True
                    changed = True

                if changed:
                    location.save()

            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Ward location synchronization complete. "
                f"{created_count} new locations created."
            )
        )
