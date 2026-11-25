from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from prescriptions.models import Prescription


class Command(BaseCommand):
    help = "Configure HPMS prescription permissions."

    def handle(self, *args, **options):
        content_type = ContentType.objects.get_for_model(Prescription)

        codes = [
            "can_create_prescription",
            "can_view_prescriptions",
            "can_verify_prescription",
            "can_register_paper_prescription",
            "can_cancel_prescription",
        ]

        permissions = {
            code: Permission.objects.get(
                content_type=content_type,
                codename=code,
            )
            for code in codes
        }

        assignments = {
            "Hospital Administrator": list(permissions.values()),

            "Hospital Manager": [
                permissions["can_view_prescriptions"],
            ],

            "Doctor": [
                permissions["can_create_prescription"],
                permissions["can_view_prescriptions"],
                permissions["can_cancel_prescription"],
            ],

            "Pharmacist": [
                permissions["can_view_prescriptions"],
                permissions["can_verify_prescription"],
                permissions["can_register_paper_prescription"],
                permissions["can_cancel_prescription"],
            ],

            "Pharmacy Technician": [
                permissions["can_view_prescriptions"],
            ],
        }

        for role_name, role_permissions in assignments.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            group.permissions.add(*role_permissions)
            self.stdout.write(
                self.style.SUCCESS(f"Configured {role_name}")
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Prescription permissions configured successfully."
            )
        )
