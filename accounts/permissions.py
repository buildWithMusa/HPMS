
"""
Central permission policy for the Hospital Pharmacy Management System.

This file defines standard Django permissions and custom HPMS
business permissions assigned to each system role.
"""

from django.contrib.auth.models import Group


# ---------------------------------------------------------
# 1. STANDARD DJANGO PERMISSIONS
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
    "staff.view_staffprofile",
    "staff.view_staffassignment",
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
# 2. CUSTOM HPMS BUSINESS PERMISSIONS
# ---------------------------------------------------------

PRESCRIPTION_CREATE = [
    "accounts.can_create_prescription",
]

PRESCRIPTION_VERIFY_AND_DISPENSE = [
    "accounts.can_verify_prescription",
    "accounts.can_dispense_medicine",
]

WARD_STOCK_REQUEST = [
    "accounts.can_request_ward_stock",
]

STOCK_RECEIVING = [
    "accounts.can_receive_stock",
]

STOCK_APPROVAL = [
    "accounts.can_approve_stock_adjustment",
]

PURCHASE_CREATE = [
    "accounts.can_create_purchase_order",
]

PURCHASE_APPROVAL = [
    "accounts.can_approve_purchase_order",
]

PATIENT_PAYMENT = [
    "accounts.can_process_patient_payment",
]

FINANCE_PERMISSIONS = [
    "accounts.can_reconcile_payments",
    "accounts.can_view_financial_reports",
    "accounts.can_authorize_refund",
]

FINANCIAL_REPORT_VIEW = [
    "accounts.can_view_financial_reports",
]

STAFF_ACCESS_MANAGEMENT = [
    "accounts.can_manage_staff_access",
]


# ---------------------------------------------------------
# 3. ADMINISTRATOR PERMISSIONS
# ---------------------------------------------------------

ALL_CUSTOM_PERMISSIONS = (
    PRESCRIPTION_CREATE
    + PRESCRIPTION_VERIFY_AND_DISPENSE
    + WARD_STOCK_REQUEST
    + STOCK_RECEIVING
    + STOCK_APPROVAL
    + PURCHASE_CREATE
    + PURCHASE_APPROVAL
    + PATIENT_PAYMENT
    + FINANCE_PERMISSIONS
    + STAFF_ACCESS_MANAGEMENT

)
CROSS_DEPARTMENT_ACCESS = [
    "accounts.can_access_all_departments",
]

ADMINISTRATOR_PERMISSIONS = (
    STAFF_MANAGEMENT
    + HOSPITAL_STRUCTURE_MANAGEMENT
    + USER_MANAGEMENT
    + ALL_CUSTOM_PERMISSIONS
)


# ---------------------------------------------------------
# 4. ROLE-BASED PERMISSION POLICY
# ---------------------------------------------------------

ROLE_PERMISSION_POLICY = {

    "Hospital Administrator": ADMINISTRATOR_PERMISSIONS,

    "Hospital Manager": (
        STAFF_VIEW
        + HOSPITAL_STRUCTURE_VIEW
        + STOCK_APPROVAL
        + PURCHASE_APPROVAL
        + FINANCIAL_REPORT_VIEW
        + ["accounts.can_authorize_refund"]
    ),

    "Pharmacist": (
        HOSPITAL_STRUCTURE_VIEW
        + PRESCRIPTION_VERIFY_AND_DISPENSE
    ),

    "Pharmacy Technician": (
        HOSPITAL_STRUCTURE_VIEW
    ),

    "Store Manager": (
        HOSPITAL_STRUCTURE_VIEW
        + STOCK_RECEIVING
    ),

    "Doctor": (
        HOSPITAL_STRUCTURE_VIEW
        + PRESCRIPTION_CREATE
    ),

    "Nurse": (
        HOSPITAL_STRUCTURE_VIEW
        + WARD_STOCK_REQUEST
    ),

    "Procurement Officer": (
        HOSPITAL_STRUCTURE_VIEW
        + PURCHASE_CREATE
    ),

    "Finance Officer": (
        HOSPITAL_STRUCTURE_VIEW
        + FINANCE_PERMISSIONS
    ),

    "Cashier": (
        HOSPITAL_STRUCTURE_VIEW
        + PATIENT_PAYMENT
    ),
}


# ---------------------------------------------------------
# 5. POLICY ACCESS FUNCTIONS
# ---------------------------------------------------------

def get_role_permission_policy():
    """
    Return a copy of the configured HPMS role policy.
    """
    return {
        role: list(permissions)
        for role, permissions in ROLE_PERMISSION_POLICY.items()
    }


def get_hpms_groups():
    """
    Retrieve existing HPMS groups configured in this policy.
    """
    return Group.objects.filter(
        name__in=ROLE_PERMISSION_POLICY.keys()
    ).order_by("name")
