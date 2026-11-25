
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from accounts.authorization import require_hpms_permission

from .models import Patient, PatientIdentifier, PatientGuardian
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError

PATIENT_FIELDS = {
    "first_name",
    "middle_name",
    "last_name",
    "date_of_birth",
    "sex",
    "phone_number",
    "email",
    "address",
    "county",
    "sub_county",
}

IDENTIFIER_FIELDS = {
    "identifier_type",
    "identifier_value",
    "is_primary",
}

GUARDIAN_FIELDS = {
    "full_name",
    "relationship",
    "phone_number",
    "email",
    "national_id",
    "is_primary",
    "is_active",
}


def validate_allowed_fields(data, allowed_fields, record_name):
    if not isinstance(data, dict):
        raise ValidationError(
            f"{record_name} data must be provided as a dictionary."
        )

    unexpected = set(data.keys()) - allowed_fields

    if unexpected:
        raise ValidationError({
            "fields": (
                f"Unsupported {record_name} fields: "
                f"{', '.join(sorted(unexpected))}"
            )
        })


def register_patient(
    *,
    actor,
    patient_data,
    identifiers=None,
    guardians=None,
):
    """
    Register a patient and associated identification documents
    and guardians as one atomic operation.

    Returns the newly created Patient instance.
    """

    # 1. Check authorization.
    require_hpms_permission(
        actor,
        "patients.can_register_patient"
    )

    identifiers = identifiers or []
    guardians = guardians or []

    if not isinstance(identifiers, list):
        raise ValidationError(
            "Identifiers must be provided as a list."
        )

    if not isinstance(guardians, list):
        raise ValidationError(
            "Guardians must be provided as a list."
        )

    # 2. Validate the supplied fields.
    validate_allowed_fields(
        patient_data,
        PATIENT_FIELDS,
        "patient"
    )

    for identifier_data in identifiers:
        validate_allowed_fields(
            identifier_data,
            IDENTIFIER_FIELDS,
            "identifier"
        )

    for guardian_data in guardians:
        validate_allowed_fields(
            guardian_data,
            GUARDIAN_FIELDS,
            "guardian"
        )

    # 3. Check primary-record rules before writing.
    primary_identifiers = sum(
        bool(item.get("is_primary", False))
        for item in identifiers
    )

    active_primary_guardians = sum(
        bool(item.get("is_primary", False))
        and item.get("is_active", True)
        for item in guardians
    )

    if primary_identifiers > 1:
        raise ValidationError(
            "A patient can only have one primary identifier."
        )

    if active_primary_guardians > 1:
        raise ValidationError(
            "A patient can only have one active primary guardian."
        )

    try:
        with transaction.atomic():

            # 4. Construct and validate the patient.
            patient = Patient(
                **patient_data,
                registered_by=actor
            )

            # hospital_number is generated during save().
            patient.full_clean(
                exclude=["hospital_number"]
            )

            # 5. Save patient and generate hospital number.
            patient.save()

            # 6. Register identification documents.
            for identifier_data in identifiers:

                identifier = PatientIdentifier(
                    patient=patient,
                    **identifier_data
                )

                identifier.identifier_value = " ".join(
                    identifier.identifier_value.split()
                )

                identifier.full_clean()
                identifier.save()

            # 7. Register guardians.
            for guardian_data in guardians:

                guardian = PatientGuardian(
                    patient=patient,
                    **guardian_data
                )

                guardian.full_clean()
                guardian.save()

            return patient

    except IntegrityError as exc:
        raise ValidationError(
            "Registration could not be completed because "
            "a database constraint was violated. Check for "
            "duplicate identification documents or conflicting "
            "primary records."
        ) from exc

def update_patient(*, actor, patient, patient_data):
    """
    Update permitted patient information.

    The hospital number, registration information and
    database identity cannot be changed through this service.
    """

    require_hpms_permission(
        actor,
        "patients.can_update_patient_records",
    )

    allowed_fields = {
        "first_name",
        "middle_name",
        "last_name",
        "date_of_birth",
        "sex",
        "phone_number",
        "email",
        "address",
        "county",
        "sub_county",
    }

    validate_allowed_fields(
        patient_data,
        allowed_fields,
        "Patient",
    )

    with transaction.atomic():

        locked_patient = Patient.objects.select_for_update().get(
            pk=patient.pk
        )

        for field, value in patient_data.items():
            setattr(locked_patient, field, value)

        locked_patient.full_clean(
            exclude=["hospital_number"]
        )

        locked_patient.save()

    return locked_patient

def change_patient_status(*, actor, patient, new_status):
    """
    Activate or deactivate a patient record.

    Patient records are never deleted by this operation.
    """

    require_hpms_permission(
        actor,
        "patients.can_manage_patient_status",
    )

    if not isinstance(new_status, bool):
        raise ValidationError(
            "Patient status must be either active or inactive."
        )

    with transaction.atomic():

        locked_patient = Patient.objects.select_for_update().get(
            pk=patient.pk
        )

        if locked_patient.is_active == new_status:
            return locked_patient

        locked_patient.is_active = new_status

        locked_patient.save(
            update_fields=["is_active", "updated_at"]
        )

    return locked_patient


