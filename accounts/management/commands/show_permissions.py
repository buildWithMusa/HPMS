
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):

    help = "Display all permissions assigned to HPMS role groups."

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.SUCCESS(
                "\n========== HPMS ROLE PERMISSIONS ==========\n"
            )
        )

        groups = Group.objects.prefetch_related(
            "permissions__content_type",
            "user_set",
        ).order_by("name")

        for group in groups:

            self.stdout.write(
                self.style.HTTP_INFO(
                    f"\nROLE: {group.name}"
                )
            )

            self.stdout.write(
                f"Employees assigned: {group.user_set.count()}"
            )

            permissions = group.permissions.all().order_by(
                "content_type__app_label",
                "codename",
            )

            if not permissions.exists():

                self.stdout.write(
                    self.style.WARNING(
                        "  No permissions assigned."
                    )
                )

                continue

            for permission in permissions:

                full_permission = (
                    f"{permission.content_type.app_label}."
                    f"{permission.codename}"
                )

                self.stdout.write(
                    f"  {full_permission}"
                )

            self.stdout.write(
                f"Total permissions: {permissions.count()}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\n========== END OF REPORT ==========\n"
            )
        )
