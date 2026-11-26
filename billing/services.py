from decimal import Decimal
import uuid

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from dispensing.models import Dispensing, DispensingBatchAllocation

from .models import Invoice, InvoiceLine, Payment


def require_permission(actor, permission):
    if (
        not actor
        or not actor.is_authenticated
        or not actor.is_active
        or not actor.has_perm(permission)
    ):
        raise PermissionDenied(
            "You are not authorized to perform this operation."
        )


@transaction.atomic
def create_invoice(*, actor, dispensing):
    require_permission(
        actor,
        "billing.can_create_invoice"
    )

    dispensing = Dispensing.objects.select_for_update().get(
        pk=dispensing.pk
    )

    existing = Invoice.objects.filter(
        dispensing=dispensing
    ).first()

    if existing:
        return existing

    allocations = DispensingBatchAllocation.objects.filter(
        dispensing=dispensing
    ).select_related(
        "batch",
        "batch__medicine"
    )

    if not allocations.exists():
        raise ValidationError(
            "This dispensing record has no batch allocations."
        )

    patient = dispensing.prescription.patient

    invoice = Invoice.objects.create(
        dispensing=dispensing,
        patient=patient,
        created_by=actor
    )

    total = Decimal("0.00")

    for allocation in allocations:
        batch = allocation.batch

        unit_price = Decimal(batch.selling_price)
        line_total = unit_price * allocation.quantity

        InvoiceLine.objects.create(
            invoice=invoice,
            dispensing_allocation=allocation,
            medicine_name=batch.medicine.display_name,
            batch_number=batch.batch_number,
            quantity=allocation.quantity,
            unit_price=unit_price,
            line_total=line_total
        )

        total += line_total

    invoice.total_amount = total
    invoice.save(update_fields=["total_amount", "updated_at"])

    return invoice


@transaction.atomic
def simulate_payment(
    *,
    actor,
    invoice,
    amount,
    method,
    outcome,
    phone_number=""
):
    if method == Payment.Method.MPESA:
        require_permission(
            actor,
            "billing.can_initiate_payment"
        )
    elif method == Payment.Method.CASH:
        require_permission(
            actor,
            "billing.can_record_cash_payment"
        )
    else:
        raise ValidationError("Invalid payment method.")

    invoice = Invoice.objects.select_for_update().get(
        pk=invoice.pk
    )

    if invoice.status == Invoice.Status.CANCELLED:
        raise ValidationError(
            "This invoice has been cancelled."
        )

    if invoice.status == Invoice.Status.PAID:
        raise ValidationError(
            "This invoice has already been paid."
        )

    try:
        amount = Decimal(str(amount))
    except Exception:
        raise ValidationError("Enter a valid payment amount.")

    if not amount.is_finite() or amount <= 0:
        raise ValidationError(
            "Payment amount must be greater than zero."
        )

    if amount > invoice.balance:
        raise ValidationError(
            "Payment cannot exceed the outstanding balance."
        )

    allowed_outcomes = {
        "SUCCESSFUL",
        "FAILED",
        "CANCELLED"
    }

    if outcome not in allowed_outcomes:
        raise ValidationError("Invalid simulated payment outcome.")

    payment = Payment.objects.create(
        invoice=invoice,
        method=method,
        amount=amount,
        phone_number=phone_number,
        transaction_reference=(
            f"SIM-{uuid.uuid4().hex[:16].upper()}"
        ),
        initiated_by=actor,
        status=Payment.Status.PENDING
    )

    payment.status = outcome

    if outcome == Payment.Status.SUCCESSFUL:
        payment.receipt_number = (
            f"SIM-{timezone.now().year}-"
            f"{uuid.uuid4().hex[:10].upper()}"
        )
        payment.completed_at = timezone.now()

    payment.save(
        update_fields=[
            "status",
            "receipt_number",
            "completed_at"
        ]
    )

    if outcome == Payment.Status.SUCCESSFUL:
        if invoice.balance == 0:
            invoice.status = Invoice.Status.PAID
        else:
            invoice.status = Invoice.Status.PARTIALLY_PAID

        invoice.save(
            update_fields=["status", "updated_at"]
        )

    return payment
