from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Assign inventory permissions to HPMS staff roles."

    ROLE_PERMISSIONS = {
        "Hospital Administrator": [
            "can_transfer_stock",
            "can_adjust_stock",
            "can_dispense_stock",
            "can_view_inventory",
        ],
        "Pharmacist": [
            "can_transfer_stock",
            "can_dispense_stock",
            "can_view_inventory",
        ],
        "Pharmacy Technician": ["can_view_inventory"],
        "Store Manager": [
            "can_transfer_stock",
            "can_adjust_stock",
            "can_view_inventory",
        ],
        "Hospital Manager": ["can_view_inventory"],
    }

    def handle(self, *args, **options):
        for role_name, codenames in self.ROLE_PERMISSIONS.items():
            try:
                group = Group.objects.get(name=role_name)
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Group not found: {role_name}")
                )
                continue

            permissions = Permission.objects.filter(
                content_type__app_label="inventory",
                codename__in=codenames,
            )

            found = set(permissions.values_list("codename", flat=True))
            missing = set(codenames) - found

            if missing:
                self.stdout.write(
                    self.style.WARNING(
                        f"{role_name}: missing permissions {missing}"
                    )
                )

            group.permissions.add(*permissions)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Inventory permissions assigned to {role_name}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS("Inventory permissions setup completed.")
        )
