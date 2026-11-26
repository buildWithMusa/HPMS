from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group

from accounts.permissions import ROLE_PERMISSION_POLICY


class Command(BaseCommand):
    help = (
        "Restrict staff profile and assignment permissions "
        "to Hospital Administrators and Hospital Managers."
    )

    def handle(self, *args, **options):
        allowed_roles = {
            "Hospital Administrator",
            "Hospital Manager",
        }

        all_roles = set(ROLE_PERMISSION_POLICY.keys())
        restricted_roles = all_roles - allowed_roles

        staff_permissions = Permission.objects.filter(
            content_type__app_label="staff"
        )

        if not staff_permissions.exists():
            self.stdout.write(
                self.style.ERROR(
                    "No staff permissions found. Run migrations first."
                )
            )
            return

        removed_group_count = 0

        for role_name in sorted(restricted_roles):
            group = Group.objects.filter(name=role_name).first()

            if not group:
                self.stdout.write(
                    self.style.WARNING(f"Group not found: {role_name}")
                )
                continue

            assigned = group.permissions.filter(
                pk__in=staff_permissions.values("pk")
            )

            count = assigned.count()

            if count:
                group.permissions.remove(*assigned)
                removed_group_count += count

            self.stdout.write(
                f"{role_name}: removed {count} staff permissions"
            )

        User = get_user_model()

        restricted_users = User.objects.filter(
            groups__name__in=restricted_roles
        ).exclude(
            groups__name__in=allowed_roles
        ).distinct()

        removed_user_count = 0

        for user in restricted_users:
            assigned = user.user_permissions.filter(
                pk__in=staff_permissions.values("pk")
            )

            count = assigned.count()

            if count:
                user.user_permissions.remove(*assigned)
                removed_user_count += count

        self.stdout.write(
            self.style.SUCCESS(
                "\nStaff directory access restriction completed."
            )
        )
        self.stdout.write(
            f"Group permissions removed: {removed_group_count}"
        )
        self.stdout.write(
            f"Individual user permissions removed: {removed_user_count}"
        )
        self.stdout.write(
            "Allowed roles: Hospital Administrator, Hospital Manager"
        )
