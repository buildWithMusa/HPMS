
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.test import TestCase

from accounts.authorization import (
    has_hpms_permission,
    require_hpms_permission,
    authorize_approval,
)

User = get_user_model()


class HPMSSecurityRoleTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):

        # Create the standard HPMS roles.
        call_command("setup_roles", verbosity=0)

        # Apply the permission policy to those roles.
        call_command("setup_permissions", verbosity=0)

        # Create users for each role.
        cls.doctor = cls.create_role_user(
            "doctor-role-test@hpms.local",
            "Doctor",
        )

        cls.pharmacist = cls.create_role_user(
            "pharmacist-role-test@hpms.local",
            "Pharmacist",
        )

        cls.procurement = cls.create_role_user(
            "procurement-role-test@hpms.local",
            "Procurement Officer",
        )

        cls.manager = cls.create_role_user(
            "manager-role-test@hpms.local",
            "Hospital Manager",
        )

        cls.cashier = cls.create_role_user(
            "cashier-role-test@hpms.local",
            "Cashier",
        )

        cls.finance = cls.create_role_user(
            "finance-role-test@hpms.local",
            "Finance Officer",
        )

        cls.unassigned_user = User.objects.create_user(
            email="unassigned-role-test@hpms.local",
            password="TestPassword123!",
        )

    @classmethod
    def create_role_user(cls, email, role_name):
        user = User.objects.create_user(
            email=email,
            password="TestPassword123!",
        )

        group = Group.objects.get(name=role_name)
        user.groups.add(group)

        return user

    # ==================================================
    # DOCTOR PERMISSIONS
    # ==================================================

    def test_doctor_can_create_prescriptions(self):
        self.assertTrue(
            has_hpms_permission(
                self.doctor,
                "accounts.can_create_prescription",
            )
        )

    def test_doctor_cannot_verify_prescriptions(self):
        self.assertFalse(
            has_hpms_permission(
                self.doctor,
                "accounts.can_verify_prescription",
            )
        )

    def test_doctor_cannot_dispense_medicine(self):
        self.assertFalse(
            has_hpms_permission(
                self.doctor,
                "accounts.can_dispense_medicine",
            )
        )

    # ==================================================
    # PHARMACIST PERMISSIONS
    # ==================================================

    def test_pharmacist_can_verify_prescriptions(self):
        self.assertTrue(
            has_hpms_permission(
                self.pharmacist,
                "accounts.can_verify_prescription",
            )
        )

    def test_pharmacist_can_dispense_medicine(self):
        self.assertTrue(
            has_hpms_permission(
                self.pharmacist,
                "accounts.can_dispense_medicine",
            )
        )

    def test_pharmacist_cannot_create_prescriptions(self):
        self.assertFalse(
            has_hpms_permission(
                self.pharmacist,
                "accounts.can_create_prescription",
            )
        )

    # ==================================================
    # PROCUREMENT PERMISSIONS
    # ==================================================

    def test_procurement_officer_can_create_purchase_orders(self):
        self.assertTrue(
            has_hpms_permission(
                self.procurement,
                "accounts.can_create_purchase_order",
            )
        )

    def test_procurement_officer_cannot_approve_purchase_orders(self):
        self.assertFalse(
            has_hpms_permission(
                self.procurement,
                "accounts.can_approve_purchase_order",
            )
        )

    # ==================================================
    # HOSPITAL MANAGER PERMISSIONS
    # ==================================================

    def test_hospital_manager_can_approve_purchase_orders(self):
        self.assertTrue(
            has_hpms_permission(
                self.manager,
                "accounts.can_approve_purchase_order",
            )
        )

    def test_hospital_manager_has_cross_department_access(self):
        self.assertTrue(
            has_hpms_permission(
                self.manager,
                "accounts.can_access_all_departments",
            )
        )

    # ==================================================
    # CASHIER AND FINANCE PERMISSIONS
    # ==================================================

    def test_cashier_can_process_patient_payments(self):
        self.assertTrue(
            has_hpms_permission(
                self.cashier,
                "accounts.can_process_patient_payment",
            )
        )

    def test_cashier_cannot_authorize_refunds(self):
        self.assertFalse(
            has_hpms_permission(
                self.cashier,
                "accounts.can_authorize_refund",
            )
        )

    def test_finance_officer_can_reconcile_payments(self):
        self.assertTrue(
            has_hpms_permission(
                self.finance,
                "accounts.can_reconcile_payments",
            )
        )

    def test_finance_officer_can_view_financial_reports(self):
        self.assertTrue(
            has_hpms_permission(
                self.finance,
                "accounts.can_view_financial_reports",
            )
        )

    def test_finance_officer_can_authorize_refunds(self):
        self.assertTrue(
            has_hpms_permission(
                self.finance,
                "accounts.can_authorize_refund",
            )
        )

    # ==================================================
    # USERS WITHOUT PERMISSIONS
    # ==================================================

    def test_unassigned_user_has_no_purchase_approval_permission(self):
        self.assertFalse(
            has_hpms_permission(
                self.unassigned_user,
                "accounts.can_approve_purchase_order",
            )
        )

    def test_unassigned_user_cannot_use_protected_operation(self):
        with self.assertRaises(PermissionDenied):
            require_hpms_permission(
                self.unassigned_user,
                "accounts.can_approve_purchase_order",
            )

    def test_inactive_user_has_no_hpms_permission(self):
        self.manager.is_active = False
        self.manager.save()

        self.assertFalse(
            has_hpms_permission(
                self.manager,
                "accounts.can_approve_purchase_order",
            )
        )

    # ==================================================
    # APPROVAL AND SEPARATION OF DUTIES
    # ==================================================

    def test_manager_can_approve_another_users_transaction(self):
        result = authorize_approval(
            actor=self.manager,
            initiator=self.procurement,
            permission="accounts.can_approve_purchase_order",
        )

        self.assertTrue(result)

    def test_manager_cannot_approve_own_transaction(self):
        with self.assertRaises(PermissionDenied):
            authorize_approval(
                actor=self.manager,
                initiator=self.manager,
                permission="accounts.can_approve_purchase_order",
            )

    def test_procurement_officer_cannot_approve_purchase_order(self):
        with self.assertRaises(PermissionDenied):
            authorize_approval(
                actor=self.procurement,
                initiator=self.doctor,
                permission="accounts.can_approve_purchase_order",
            )

    def test_approval_requires_a_known_initiator(self):
        with self.assertRaises(PermissionDenied):
            authorize_approval(
                actor=self.manager,
                initiator=None,
                permission="accounts.can_approve_purchase_order",
            )

    def test_inactive_manager_cannot_approve_transaction(self):
        self.manager.is_active = False
        self.manager.save()

        with self.assertRaises(PermissionDenied):
            authorize_approval(
                actor=self.manager,
                initiator=self.procurement,
                permission="accounts.can_approve_purchase_order",
            )
