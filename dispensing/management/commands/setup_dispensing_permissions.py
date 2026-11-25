from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from dispensing.models import Dispensing


class Command(BaseCommand):
    help = "Configure HPMS dispensing permissions."

    def handle(self, *args, **options):
        content_type = ContentType.objects.get_for_model(Dispensing)

        permissions = {
            p.codename: p
            for p in Permission.objects.filter(
                content_type=content_type
            )
        }

        assignments = {
            "Hospital Administrator": [
                "can_dispense_prescription",
                "can_view_dispensing",
            ],
            "Pharmacist": [
                "can_dispense_prescription",
                "can_view_dispensing",
            ],
            "Pharmacy Technician": [
                "can_view_dispensing",
            ],
            "Hospital Manager": [
                "can_view_dispensing",
            ],
        }

        for role, codes in assignments.items():
            group, _ = Group.objects.get_or_create(name=role)
            for code in codes:
                if code not in permissions:
                    self.stdout.write(self.style.WARNING(
                        f"Missing permission: {code}"
                    ))
                    continue
                group.permissions.add(permissions[code])
            self.stdout.write(self.style.SUCCESS(f"Configured {role}"))

        self.stdout.write(self.style.SUCCESS("Dispensing permissions configured."))
