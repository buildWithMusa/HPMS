from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = "Assign medicine catalogue permissions to HPMS roles."

    ROLE_PERMISSIONS = {
        "Hospital Administrator": [
            "view_medicine",
            "add_medicine",
            "change_medicine",
            "can_manage_medicine_status",
            "view_medicinecategory",
            "add_medicinecategory",
            "change_medicinecategory",
        ],
        "Pharmacist": [
            "view_medicine",
            "add_medicine",
            "change_medicine",
            "can_manage_medicine_status",
            "view_medicinecategory",
        ],
        "Pharmacy Technician": [
            "view_medicine",
            "view_medicinecategory",
        ],
        "Store Manager": [
            "view_medicine",
            "add_medicine",
            "change_medicine",
            "can_manage_medicine_status",
            "view_medicinecategory",
            "add_medicinecategory",
            "change_medicinecategory",
        ],
        "Hospital Manager": [
            "view_medicine",
            "view_medicinecategory",
        ],
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
                content_type__app_label="medicines",
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
                    f"Permissions assigned to {role_name}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS("Medicine permissions setup completed.")
        )
