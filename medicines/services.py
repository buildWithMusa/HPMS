from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.authorization import require_hpms_permission
from .models import Medicine, MedicineCategory


def validate_allowed_fields(data, allowed_fields, record_name):
    unsupported = set(data.keys()) - allowed_fields

    if unsupported:
        raise ValidationError(
            f"Unsupported {record_name} fields: "
            f"{', '.join(sorted(unsupported))}"
        )


MEDICINE_FIELDS = {
    "category",
    "generic_name",
    "brand_name",
    "strength",
    "dosage_form",
    "unit_of_measure",
    "description",
}


def create_medicine(*, actor, medicine_data):
    require_hpms_permission(actor, "medicines.add_medicine")

    validate_allowed_fields(
        medicine_data,
        MEDICINE_FIELDS,
        "medicine"
    )

    medicine = Medicine(**medicine_data)
    medicine.full_clean()
    medicine.save()

    return medicine


def update_medicine(*, actor, medicine, medicine_data):
    require_hpms_permission(actor, "medicines.change_medicine")

    validate_allowed_fields(
        medicine_data,
        MEDICINE_FIELDS,
        "medicine"
    )

    with transaction.atomic():
        locked_medicine = Medicine.objects.select_for_update().get(
            pk=medicine.pk
        )

        for field, value in medicine_data.items():
            setattr(locked_medicine, field, value)

        locked_medicine.full_clean()
        locked_medicine.save()

    return locked_medicine


def change_medicine_status(*, actor, medicine, new_status):
    require_hpms_permission(
        actor,
        "medicines.can_manage_medicine_status"
    )

    if not isinstance(new_status, bool):
        raise ValidationError(
            "Medicine status must be active or inactive."
        )

    with transaction.atomic():
        locked_medicine = Medicine.objects.select_for_update().get(
            pk=medicine.pk
        )

        if locked_medicine.is_active == new_status:
            return locked_medicine

        locked_medicine.is_active = new_status
        locked_medicine.save(
            update_fields=["is_active", "updated_at"]
        )

    return locked_medicine


def create_medicine_category(*, actor, category_data):
    require_hpms_permission(actor, "medicines.add_medicinecategory")

    allowed_fields = {"name", "description"}

    validate_allowed_fields(
        category_data,
        allowed_fields,
        "category"
    )

    category = MedicineCategory(**category_data)
    category.full_clean()
    category.save()

    return category
