
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from hospital.models import Department, ServiceArea
from staff.models import StaffProfile, StaffAssignment
import staff.access as access

User = get_user_model()

models_to_inspect = [
    User,
    Department,
    ServiceArea,
    StaffProfile,
    StaffAssignment,
]

print("\n========== HPMS MODEL INSPECTION ==========")

for model in models_to_inspect:
    print("\nMODEL:", model.__name__)

    for field in model._meta.get_fields():
        if not getattr(field, "concrete", False):
            continue

        required = (
            not field.null
            and not field.blank
            and not field.has_default()
            and not field.primary_key
        )

        print(
            f"Field: {field.name} | "
            f"Type: {field.get_internal_type()} | "
            f"Required: {required}"
        )

print("\n========== AUTHORIZATION FUNCTIONS ==========")

functions = [
    "has_cross_department_access",
    "get_active_staff_assignments",
    "has_department_access",
    "has_service_area_access",
    "get_accessible_department_ids",
    "get_accessible_service_area_ids",
    "require_department_access",
    "require_service_area_access",
    "department_access_required",
    "service_area_access_required",
]

for name in functions:
    print(name, callable(getattr(access, name, None)))
