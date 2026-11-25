from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounts.authorization import require_hpms_permission
from inventory.models import StockLocation
from inventory.services import dispense_medicine_fefo
from prescriptions.models import Prescription, PrescriptionLine

from .models import Dispensing, DispensingBatchAllocation


@transaction.atomic
def dispense_prescription_line(
    *, actor, prescription, prescription_line, quantity, notes=""
):
    require_hpms_permission(
        actor, "dispensing.can_dispense_prescription"
    )

    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValidationError("Dispensing quantity must be a positive whole number.")

    # Lock the prescription to prevent simultaneous dispensing exceeding the order.
    prescription = Prescription.objects.select_for_update().get(
        pk=prescription.pk
    )

    if prescription.status not in [
        Prescription.Status.VERIFIED,
        Prescription.Status.PARTIALLY_DISPENSED,
    ]:
        raise ValidationError(
            "Only verified prescriptions can be dispensed."
        )

    if not prescription.patient.is_active:
        raise ValidationError("This patient record is inactive.")

    try:
        line = PrescriptionLine.objects.select_for_update().select_related(
            "medicine"
        ).get(
            pk=prescription_line.pk,
            prescription=prescription,
        )
    except PrescriptionLine.DoesNotExist:
        raise ValidationError(
            "The selected medicine does not belong to this prescription."
        )

    if not line.medicine.is_active:
        raise ValidationError("This medicine is inactive.")

    already_dispensed = (
        Dispensing.objects.filter(prescription_line=line)
        .aggregate(total=Sum("quantity"))["total"] or 0
    )
    remaining = line.quantity - already_dispensed

    if remaining <= 0:
        raise ValidationError("This prescription line has already been fully dispensed.")

    if quantity > remaining:
        raise ValidationError(
            f"Cannot dispense {quantity}. Only {remaining} remain to be dispensed."
        )

    try:
        location = StockLocation.objects.get(
            location_type=StockLocation.LocationType.CENTRAL,
            is_active=True,
        )
    except StockLocation.DoesNotExist:
        raise ValidationError("The active central pharmacy location is not configured.")

    record = Dispensing.objects.create(
        prescription=prescription,
        prescription_line=line,
        quantity=quantity,
        dispensed_by=actor,
        notes=notes.strip(),
    )

    allocations = dispense_medicine_fefo(
        actor=actor,
        medicine=line.medicine,
        location=location,
        quantity=quantity,
        reference=record.reference,
        notes=f"Prescription {prescription.prescription_number}. {notes}".strip(),
    )

    allocated_total = 0
    for allocation in allocations:
        DispensingBatchAllocation.objects.create(
            dispensing=record,
            batch=allocation["batch"],
            quantity=allocation["quantity"],
            stock_movement=allocation["movement"],
        )
        allocated_total += allocation["quantity"]

    if allocated_total != quantity:
        raise ValidationError("The stock allocation did not match the dispensing quantity.")

    # Recalculate the prescription's overall dispensing status.
    totals = {
        row["prescription_line_id"]: row["total"]
        for row in Dispensing.objects.filter(
            prescription=prescription
        ).values("prescription_line_id").annotate(
            total=Sum("quantity")
        )
    }

    prescription_lines = list(
        prescription.lines.values_list("id", "quantity")
    )

    fully_dispensed = all(
        totals.get(line_id, 0) >= prescribed
        for line_id, prescribed in prescription_lines
    )

    any_dispensed = any(totals.values())

    if fully_dispensed:
        prescription.status = Prescription.Status.DISPENSED
    elif any_dispensed:
        prescription.status = Prescription.Status.PARTIALLY_DISPENSED

    prescription.save(update_fields=["status", "updated_at"])

    return record


def get_remaining_quantity(prescription_line):
    dispensed = (
        Dispensing.objects.filter(prescription_line=prescription_line)
        .aggregate(total=Sum("quantity"))["total"] or 0
    )
    return max(0, prescription_line.quantity - dispensed)
