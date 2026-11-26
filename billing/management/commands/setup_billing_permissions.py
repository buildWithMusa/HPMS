from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = "Set up HPMS billing permissions"

    def handle(self, *args, **options):
        permissions = {
            "Hospital Administrator": [
                "can_create_invoice",
                "can_view_billing",
                "can_cancel_invoice",
                "can_initiate_payment",
                "can_record_cash_payment",
            ],
            "Cashier": [
                "can_create_invoice",
                "can_view_billing",
                "can_initiate_payment",
                "can_record_cash_payment",
            ],
            "Pharmacist": [
                "can_create_invoice",
                "can_view_billing",
                "can_initiate_payment",
            ],
            "Hospital Manager": [
                "can_view_billing",
            ],
        }

        for group_name, codenames in permissions.items():
            group, _ = Group.objects.get_or_create(
                name=group_name
            )

            for codename in codenames:
                permission = Permission.objects.get(
                    codename=codename,
                    content_type__app_label="billing"
                )
                group.permissions.add(permission)

        self.stdout.write(
            self.style.SUCCESS(
                "Billing permissions configured."
            )
        )
