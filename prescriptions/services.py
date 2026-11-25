from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone

from accounts.authorization import (
    require_hpms_permission,
    authorize_approval,
)

from .models import Prescription, PrescriptionLine


@transaction.atomic
def create_prescription(actor, patient, diagnosis="", clinical_notes=""):
    require_hpms_permission(actor, "prescriptions.can_create_prescription")

    if not patient.is_active:
        raise ValidationError("Cannot prescribe for an inactive patient.")

    prescription = Prescription(
        patient=patient,
        source=Prescription.Source.ELECTRONIC,
        prescribed_by=actor,
        recorded_by=actor,
        diagnosis=diagnosis,
        clinical_notes=clinical_notes,
    )
    prescription.full_clean()
    prescription.save()
    return prescription


@transaction.atomic
def register_paper_prescription(
    actor,
    patient,
    prescriber_name,
    prescriber_registration="",
    external_reference="",
    diagnosis="",
    clinical_notes="",
):
    require_hpms_permission(
        actor,
        "prescriptions.can_register_paper_prescription"
    )

    if not patient.is_active:
        raise ValidationError("Cannot register a prescription for an inactive patient.")

    prescription = Prescription(
        patient=patient,
        source=Prescription.Source.PAPER,
        recorded_by=actor,
        paper_prescriber_name=prescriber_name.strip(),
        paper_prescriber_registration=prescriber_registration.strip(),
        external_reference=external_reference.strip(),
        diagnosis=diagnosis,
        clinical_notes=clinical_notes,
    )
    prescription.full_clean()
    prescription.save()
    return prescription


@transaction.atomic
def add_prescription_line(
    actor,
    prescription,
    medicine,
    dose,
    route,
    frequency,
    duration_days,
    quantity,
    instructions="",
):
    prescription = Prescription.objects.select_for_update().get(
        pk=prescription.pk
    )

    permission = (
        "prescriptions.can_register_paper_prescription"
        if prescription.source == Prescription.Source.PAPER
        else "prescriptions.can_create_prescription"
    )
    require_hpms_permission(actor, permission)

    if prescription.recorded_by_id != actor.pk:
        raise PermissionDenied("You can only edit prescriptions you recorded.")

    if prescription.status != Prescription.Status.DRAFT:
        raise ValidationError("Only draft prescriptions can be edited.")

    if not medicine.is_active:
        raise ValidationError("This medicine is inactive.")

    line = PrescriptionLine(
        prescription=prescription,
        medicine=medicine,
        dose=dose.strip(),
        route=route,
        frequency=frequency.strip(),
        duration_days=duration_days,
        quantity=quantity,
        instructions=instructions.strip(),
    )
    line.full_clean()
    line.save()
    return line


@transaction.atomic
def submit_prescription(actor, prescription):
    prescription = Prescription.objects.select_for_update().get(
        pk=prescription.pk
    )

    permission = (
        "prescriptions.can_register_paper_prescription"
        if prescription.source == Prescription.Source.PAPER
        else "prescriptions.can_create_prescription"
    )
    require_hpms_permission(actor, permission)

    if prescription.recorded_by_id != actor.pk:
        raise PermissionDenied("You can only submit prescriptions you recorded.")

    if prescription.status != Prescription.Status.DRAFT:
        raise ValidationError("Only draft prescriptions can be submitted.")

    if not prescription.lines.exists():
        raise ValidationError("Add at least one medicine before submitting.")

    prescription.status = Prescription.Status.SUBMITTED
    prescription.submitted_at = timezone.now()
    prescription.save(update_fields=["status", "submitted_at", "updated_at"])
    return prescription


@transaction.atomic
def verify_prescription(actor, prescription):
    prescription = Prescription.objects.select_for_update().get(
        pk=prescription.pk
    )

    if prescription.status != Prescription.Status.SUBMITTED:
        raise ValidationError("Only submitted prescriptions can be verified.")

    authorize_approval(
        actor,
        prescription.recorded_by,
        "prescriptions.can_verify_prescription",
    )

    for line in prescription.lines.select_related("medicine"):
        if not line.medicine.is_active:
            raise ValidationError(
                f"{line.medicine} is inactive and cannot be verified."
            )

    prescription.status = Prescription.Status.VERIFIED
    prescription.verified_by = actor
    prescription.verified_at = timezone.now()
    prescription.save(
        update_fields=["status", "verified_by", "verified_at", "updated_at"]
    )
    return prescription


@transaction.atomic
def reject_prescription(actor, prescription, reason):
    prescription = Prescription.objects.select_for_update().get(
        pk=prescription.pk
    )

    if prescription.status != Prescription.Status.SUBMITTED:
        raise ValidationError("Only submitted prescriptions can be rejected.")

    reason = reason.strip()
    if not reason:
        raise ValidationError("A rejection reason is required.")

    authorize_approval(
        actor,
        prescription.recorded_by,
        "prescriptions.can_verify_prescription",
    )

    prescription.status = Prescription.Status.REJECTED
    prescription.verified_by = actor
    prescription.rejection_reason = reason
    prescription.rejected_at = timezone.now()
    prescription.save(
        update_fields=[
            "status", "verified_by", "rejection_reason",
            "rejected_at", "updated_at"
        ]
    )
    return prescription


@transaction.atomic
def cancel_prescription(actor, prescription):
    require_hpms_permission(actor, "prescriptions.can_cancel_prescription")

    prescription = Prescription.objects.select_for_update().get(
        pk=prescription.pk
    )

    if prescription.status not in [
        Prescription.Status.DRAFT,
        Prescription.Status.SUBMITTED,
    ]:
        raise ValidationError(
            "Only draft or submitted prescriptions can be cancelled."
        )

    prescription.status = Prescription.Status.CANCELLED
    prescription.save(update_fields=["status", "updated_at"])
    return prescription
