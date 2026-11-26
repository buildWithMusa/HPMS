"""
Central permission policy for Arango's Pharmacy Management System.

All role permissions are defined here, including the actual app-level
permissions checked by the protected module views.

This policy is additive. It does not remove existing group permissions.
"""

from django.contrib.auth.models import Group


# ---------------------------------------------------------
# SHARED HOSPITAL PERMISSIONS
# ---------------------------------------------------------

HOSPITAL_STRUCTURE_VIEW = [
    "hospital.view_department",
    "hospital.view_servicearea",
    "hospital.view_ward",
]

STAFF_VIEW = [
    "staff.view_staffprofile",
    "staff.view_staffassignment",
]

STAFF_MANAGEMENT = [
    "staff.add_staffprofile",
    "staff.change_staffprofile",
    "staff.delete_staffprofile",
    "staff.add_staffassignment",
    "staff.change_staffassignment",
    "staff.delete_staffassignment",
    *STAFF_VIEW,
]

HOSPITAL_STRUCTURE_MANAGEMENT = [
    "hospital.add_department",
    "hospital.change_department",
    "hospital.delete_department",
    "hospital.add_servicearea",
    "hospital.change_servicearea",
    "hospital.delete_servicearea",
    "hospital.add_ward",
    "hospital.change_ward",
    "hospital.delete_ward",
    *HOSPITAL_STRUCTURE_VIEW,
]

USER_MANAGEMENT = [
    "accounts.add_user",
    "accounts.change_user",
    "accounts.delete_user",
    "accounts.view_user",
]


# ---------------------------------------------------------
# PATIENTS
# ---------------------------------------------------------

PATIENT_VIEW = [
    "patients.can_view_patient_records",
]

PATIENT_MANAGEMENT = [
    "patients.can_register_patient",
    "patients.can_view_patient_records",
    "patients.can_update_patient_records",
    "patients.can_manage_patient_status",
]


# ---------------------------------------------------------
# MEDICINES
# ---------------------------------------------------------

MEDICINE_VIEW = [
    "medicines.view_medicine",
    "medicines.view_medicinecategory",
]

MEDICINE_MANAGEMENT = [
    *MEDICINE_VIEW,
    "medicines.add_medicine",
    "medicines.change_medicine",
    "medicines.can_manage_medicine_status",
    "medicines.add_medicinecategory",
    "medicines.change_medicinecategory",
]


# ---------------------------------------------------------
# INVENTORY
# ---------------------------------------------------------

INVENTORY_VIEW = [
    "inventory.can_view_inventory",
]

INVENTORY_PHARMACIST = [
    "inventory.can_view_inventory",
    "inventory.can_transfer_stock",
    "inventory.can_dispense_stock",
]

INVENTORY_STORE = [
    "inventory.can_view_inventory",
    "inventory.can_transfer_stock",
    "inventory.can_adjust_stock",
    "accounts.can_receive_stock",
]


# ---------------------------------------------------------
# PRESCRIPTIONS
# ---------------------------------------------------------

PRESCRIPTION_VIEW = [
    "prescriptions.can_view_prescriptions",
]

PRESCRIPTION_DOCTOR = [
    "prescriptions.can_view_prescriptions",
    "prescriptions.can_create_prescription",
    "prescriptions.can_cancel_prescription",
]

PRESCRIPTION_PHARMACIST = [
    "prescriptions.can_view_prescriptions",
    "prescriptions.can_verify_prescription",
    "prescriptions.can_register_paper_prescription",
    "prescriptions.can_cancel_prescription",
]


# ---------------------------------------------------------
# DISPENSING
# ---------------------------------------------------------

DISPENSING_VIEW = [
    "dispensing.can_view_dispensing",
]

DISPENSING_PHARMACIST = [
    "dispensing.can_view_dispensing",
    "dispensing.can_dispense_prescription",
]


# ---------------------------------------------------------
# PROCUREMENT
# ---------------------------------------------------------

PROCUREMENT_VIEW = [
    "procurement.can_view_procurement",
]

PROCUREMENT_OFFICER = [
    "procurement.can_view_procurement",
    "procurement.can_manage_suppliers",
    "procurement.can_submit_purchase_order",
    "accounts.can_create_purchase_order",
]

PROCUREMENT_RECEIVING = [
    "procurement.can_view_procurement",
    "procurement.can_receive_purchase_order",
    "accounts.can_receive_stock",
]


# ---------------------------------------------------------
# BILLING
# ---------------------------------------------------------

BILLING_VIEW = [
    "billing.can_view_billing",
]

BILLING_CASHIER = [
    "billing.can_view_billing",
    "billing.can_create_invoice",
    "billing.can_initiate_payment",
    "billing.can_record_cash_payment",
]

BILLING_PHARMACIST = [
    "billing.can_view_billing",
    "billing.can_create_invoice",
    "billing.can_initiate_payment",
]


# ---------------------------------------------------------
# EXISTING BUSINESS PERMISSIONS
# Retained for compatibility with existing HPMS features.
# ---------------------------------------------------------

LEGACY_ADMIN_PERMISSIONS = [
    "accounts.can_create_prescription",
    "accounts.can_verify_prescription",
    "accounts.can_dispense_medicine",
    "accounts.can_request_ward_stock",
    "accounts.can_receive_stock",
    "accounts.can_approve_stock_adjustment",
    "accounts.can_create_purchase_order",
    "accounts.can_approve_purchase_order",
    "accounts.can_process_patient_payment",
    "accounts.can_reconcile_payments",
    "accounts.can_view_financial_reports",
    "accounts.can_authorize_refund",
    "accounts.can_manage_staff_access",
    "accounts.can_access_all_departments",
]

MANAGER_PERMISSIONS = [
    "accounts.can_approve_stock_adjustment",
    "accounts.can_approve_purchase_order",
    "accounts.can_view_financial_reports",
    "accounts.can_authorize_refund",
]

FINANCE_PERMISSIONS = [
    "accounts.can_reconcile_payments",
    "accounts.can_view_financial_reports",
    "accounts.can_authorize_refund",
]


# ---------------------------------------------------------
# ROLE-BASED PERMISSION POLICY
# ---------------------------------------------------------

ROLE_PERMISSION_POLICY = {

    "Hospital Administrator": (
        STAFF_MANAGEMENT
        + HOSPITAL_STRUCTURE_MANAGEMENT
        + USER_MANAGEMENT
        + PATIENT_MANAGEMENT
        + MEDICINE_MANAGEMENT
        + INVENTORY_STORE
        + INVENTORY_PHARMACIST
        + PRESCRIPTION_DOCTOR
        + PRESCRIPTION_PHARMACIST
        + DISPENSING_PHARMACIST
        + PROCUREMENT_OFFICER
        + PROCUREMENT_RECEIVING
        + BILLING_CASHIER
        + LEGACY_ADMIN_PERMISSIONS
    ),

    "Hospital Manager": (
        STAFF_VIEW
        + HOSPITAL_STRUCTURE_VIEW
        + PATIENT_VIEW
        + MEDICINE_VIEW
        + INVENTORY_VIEW
        + PRESCRIPTION_VIEW
        + DISPENSING_VIEW
        + PROCUREMENT_VIEW
        + BILLING_VIEW
        + MANAGER_PERMISSIONS
    ),

    "Pharmacist": (
        HOSPITAL_STRUCTURE_VIEW
        + PATIENT_VIEW
        + MEDICINE_MANAGEMENT
        + INVENTORY_PHARMACIST
        + PRESCRIPTION_PHARMACIST
        + DISPENSING_PHARMACIST
        + PROCUREMENT_VIEW
        + BILLING_PHARMACIST
        + [
            "accounts.can_verify_prescription",
            "accounts.can_dispense_medicine",
        ]
    ),

    "Pharmacy Technician": (
        HOSPITAL_STRUCTURE_VIEW
        + PATIENT_VIEW
        + MEDICINE_VIEW
        + INVENTORY_VIEW
        + PRESCRIPTION_VIEW
        + DISPENSING_VIEW
    ),

    "Store Manager": (
        HOSPITAL_STRUCTURE_VIEW
        + MEDICINE_MANAGEMENT
        + INVENTORY_STORE
        + PROCUREMENT_RECEIVING
    ),

    "Doctor": (
        HOSPITAL_STRUCTURE_VIEW
        + PATIENT_VIEW
        + PRESCRIPTION_DOCTOR
        + ["accounts.can_create_prescription"]
    ),

    "Nurse": (
        HOSPITAL_STRUCTURE_VIEW
        + PATIENT_VIEW
        + ["accounts.can_request_ward_stock"]
    ),

    "Procurement Officer": (
        HOSPITAL_STRUCTURE_VIEW
        + PROCUREMENT_OFFICER
    ),

    "Finance Officer": (
        HOSPITAL_STRUCTURE_VIEW
        + BILLING_VIEW
        + FINANCE_PERMISSIONS
    ),

    "Cashier": (
        HOSPITAL_STRUCTURE_VIEW
        + BILLING_CASHIER
        + ["accounts.can_process_patient_payment"]
    ),
}


# ---------------------------------------------------------
# POLICY ACCESS FUNCTIONS
# ---------------------------------------------------------

def get_role_permission_policy():
    """Return a copy of the configured role policy."""
    return {
        role: list(permissions)
        for role, permissions in ROLE_PERMISSION_POLICY.items()
    }


def get_hpms_groups():
    """Retrieve the configured HPMS role groups."""
    return Group.objects.filter(
        name__in=ROLE_PERMISSION_POLICY.keys()
    ).order_by("name")
