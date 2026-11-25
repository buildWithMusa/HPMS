
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from accounts.permissions import ROLE_PERMISSION_POLICY


class Command(BaseCommand):

    help = (
        "Assign the configured HPMS permissions "
        "to the existing role groups."
    )

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.NOTICE(
                "\nStarting HPMS permission configuration...\n"
            )
        )

        total_assigned = 0
        total_already_assigned = 0
        missing_permissions = []
        missing_groups = []

        for role_name, permission_codes in ROLE_PERMISSION_POLICY.items():

            from django.contrib.auth.models import Group

            group = Group.objects.filter(
                name=role_name
            ).first()

            if group is None:
                missing_groups.append(role_name)

                self.stdout.write(
                    self.style.WARNING(
                        f"Missing group: {role_name}"
                    )
                )

                continue

            self.stdout.write(
                self.style.HTTP_INFO(
                    f"\nProcessing role: {role_name}"
                )
            )

            for permission_code in permission_codes:

                try:
                    app_label, codename = permission_code.split(".", 1)
                except ValueError:
                    missing_permissions.append(permission_code)

                    self.stdout.write(
                        self.style.ERROR(
                            f"Invalid permission format: {permission_code}"
                        )
                    )

                    continue

                permission = Permission.objects.filter(
                    content_type__app_label=app_label,
                    codename=codename,
                ).select_related(
                    "content_type"
                ).first()

                if permission is None:

                    missing_permissions.append(permission_code)

                    self.stdout.write(
                        self.style.WARNING(
                            f"Permission not available yet: {permission_code}"
                        )
                    )

                    continue

                if group.permissions.filter(
                    pk=permission.pk
                ).exists():

                    total_already_assigned += 1

                    self.stdout.write(
                        f"  Already assigned: {permission_code}"
                    )

                else:

                    group.permissions.add(permission)

                    total_assigned += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  Assigned: {permission_code}"
                        )
                    )

        self.stdout.write("\n")
        self.stdout.write(
            self.style.SUCCESS(
                f"New permissions assigned: {total_assigned}"
            )
        )

        self.stdout.write(
            self.style.NOTICE(
                f"Already assigned: {total_already_assigned}"
            )
        )

        if missing_groups:
            self.stdout.write(
                self.style.WARNING(
                    f"Groups not found: {len(missing_groups)}"
                )
            )

        if missing_permissions:
            self.stdout.write(
                self.style.WARNING(
                    f"Unavailable permissions: {len(missing_permissions)}"
                )
            )

            for permission_code in missing_permissions:
                self.stdout.write(f"  - {permission_code}")

            raise CommandError(
                "Permission configuration is incomplete. "
                "Review the missing groups or permissions above."
            )

        if missing_groups:
            raise CommandError(
                "Some configured HPMS groups do not exist."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\nHPMS permission configuration completed successfully."
            )
        )
