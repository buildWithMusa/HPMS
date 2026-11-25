from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from accounts.models import HPMSAccessPolicy
from procurement.models import Supplier


class Command(BaseCommand):
    help = "Configure Hospital Pharmacy Management System procurement permissions."

    def handle(self, *args, **options):
        supplier_ct = ContentType.objects.get_for_model(Supplier)
        account_ct = ContentType.objects.get_for_model(HPMSAccessPolicy)

        permissions = {
            code: Permission.objects.get(
                content_type=content_type,
                codename=code,
            )
            for content_type, codes in [
                (supplier_ct, [
                    "can_manage_suppliers",
                    "can_view_procurement",
                    "can_submit_purchase_order",
                    "can_receive_purchase_order",
                ]),
                (account_ct, [
                    "can_create_purchase_order",
                    "can_approve_purchase_order",
                    "can_receive_stock",
                ]),
            ]
            for code in codes
        }

        assignments = {
            "Hospital Administrator": list(permissions.values()),
            "Hospital Manager": [
                permissions["can_view_procurement"],
                permissions["can_approve_purchase_order"],
            ],
            "Procurement Officer": [
                permissions["can_manage_suppliers"],
                permissions["can_view_procurement"],
                permissions["can_create_purchase_order"],
                permissions["can_submit_purchase_order"],
            ],
            "Store Manager": [
                permissions["can_view_procurement"],
                permissions["can_receive_purchase_order"],
                permissions["can_receive_stock"],
            ],
            "Pharmacist": [
                permissions["can_view_procurement"],
            ],
        }

        for group_name, group_permissions in assignments.items():
            group, created = Group.objects.get_or_create(name=group_name)
            group.permissions.add(*group_permissions)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Configured {group_name}"
                )
            )

        self.stdout.write(self.style.SUCCESS(
            "Procurement permissions configured successfully."
        ))
