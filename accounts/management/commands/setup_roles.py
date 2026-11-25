
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = "Create the default HPMS staff roles"

    ROLES = {
        "Hospital Administrator": (
            "Manages hospital system configuration and user administration."
        ),
        "Hospital Manager": (
            "Oversees hospital operations and management reports."
        ),
        "Pharmacist": (
            "Verifies prescriptions and manages medicine dispensing."
        ),
        "Pharmacy Technician": (
            "Supports pharmacists with dispensing and pharmacy operations."
        ),
        "Store Manager": (
            "Manages medicine inventory, batches and stock movements."
        ),
        "Doctor": (
            "Creates and manages patient prescriptions."
        ),
        "Nurse": (
            "Requests and receives medicines for authorized ward operations."
        ),
        "Procurement Officer": (
            "Manages suppliers, purchasing and purchase orders."
        ),
        "Finance Officer": (
            "Manages financial records, supplier payments and balances."
        ),
        "Cashier": (
            "Handles patient payments and receipts."
        ),
    }

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.SUCCESS(
                "Setting up HPMS staff roles..."
            )
        )

        created_count = 0
        existing_count = 0

        for role_name, description in self.ROLES.items():

            group, created = Group.objects.get_or_create(
                name=role_name
            )

            if created:
                created_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created role: {role_name}"
                    )
                )

            else:
                existing_count += 1

                self.stdout.write(
                    self.style.WARNING(
                        f"Role already exists: {role_name}"
                    )
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Role setup completed. "
                f"Created: {created_count}, "
                f"Already existing: {existing_count}"
            )
        )
