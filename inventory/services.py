from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.authorization import require_hpms_permission
from .models import StockLocation, StockBatch, StockBalance, StockMovement


def validate_quantity(quantity):
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValidationError("Quantity must be a positive whole number.")


def get_central_pharmacy():
    try:
        return StockLocation.objects.get(
            location_type=StockLocation.LocationType.CENTRAL
        )
    except StockLocation.DoesNotExist:
        raise ValidationError(
            "The central pharmacy stock location has not been configured."
        )


def receive_stock(
    *, actor, medicine, batch_number, manufacture_date, expiry_date,
    quantity, purchase_price, selling_price, notes=""
):
    require_hpms_permission(actor, "accounts.can_receive_stock")
    validate_quantity(quantity)

    if not medicine.is_active:
        raise ValidationError("Inactive medicines cannot receive new stock.")

    batch_number = batch_number.strip()

    if not batch_number:
        raise ValidationError("Batch number is required.")

    today = timezone.localdate()

    if expiry_date <= manufacture_date:
        raise ValidationError("Expiry date must be after manufacture date.")

    if expiry_date <= today:
        raise ValidationError("Expired batches cannot be received as usable stock.")

    if Decimal(purchase_price) < 0 or Decimal(selling_price) < 0:
        raise ValidationError("Prices cannot be negative.")

    central = get_central_pharmacy()

    with transaction.atomic():
        batch = StockBatch.objects.select_for_update().filter(
            medicine=medicine,
            batch_number=batch_number,
        ).first()

        if batch:
            if (
                batch.manufacture_date != manufacture_date
                or batch.expiry_date != expiry_date
                or batch.purchase_price != Decimal(purchase_price)
                or batch.selling_price != Decimal(selling_price)
            ):
                raise ValidationError(
                    "This batch already exists with different dates or prices."
                )
        else:
            batch = StockBatch(
                medicine=medicine,
                batch_number=batch_number,
                manufacture_date=manufacture_date,
                expiry_date=expiry_date,
                purchase_price=purchase_price,
                selling_price=selling_price,
                notes=notes,
            )
            batch.full_clean()
            batch.save()

        balance, _ = StockBalance.objects.get_or_create(
            batch=batch,
            location=central,
            defaults={"quantity": 0},
        )

        balance = StockBalance.objects.select_for_update().get(pk=balance.pk)
        balance.quantity = F("quantity") + quantity
        balance.save(update_fields=["quantity", "updated_at"])

        StockMovement.objects.create(
            batch=batch,
            movement_type=StockMovement.MovementType.RECEIPT,
            destination_location=central,
            quantity=quantity,
            performed_by=actor,
            notes=notes,
        )

    return batch


def transfer_stock(
    *, actor, batch, source_location, destination_location,
    quantity, notes=""
):
    require_hpms_permission(actor, "inventory.can_transfer_stock")
    validate_quantity(quantity)

    if source_location.pk == destination_location.pk:
        raise ValidationError("Source and destination must be different.")

    if not source_location.is_active or not destination_location.is_active:
        raise ValidationError("Both stock locations must be active.")

    if not batch.is_active:
        raise ValidationError("This medicine batch is inactive.")

    if batch.expiry_date <= timezone.localdate():
        raise ValidationError("Expired medicine cannot be transferred.")

    with transaction.atomic():
        balances = {
            balance.location_id: balance
            for balance in StockBalance.objects.select_for_update().filter(
                batch=batch,
                location_id__in=[
                    source_location.pk,
                    destination_location.pk,
                ],
            ).order_by("location_id")
        }

        source = balances.get(source_location.pk)

        if source is None or source.quantity < quantity:
            raise ValidationError("Insufficient stock at the source location.")

        destination = balances.get(destination_location.pk)

        if destination is None:
            destination, _ = StockBalance.objects.get_or_create(
                batch=batch,
                location=destination_location,
                defaults={"quantity": 0},
            )
            destination = StockBalance.objects.select_for_update().get(
                pk=destination.pk
            )

        source.quantity -= quantity
        destination.quantity = F("quantity") + quantity

        source.save(update_fields=["quantity", "updated_at"])
        destination.save(update_fields=["quantity", "updated_at"])

        StockMovement.objects.create(
            batch=batch,
            movement_type=StockMovement.MovementType.TRANSFER,
            source_location=source_location,
            destination_location=destination_location,
            quantity=quantity,
            performed_by=actor,
            notes=notes,
        )

    return True


def dispense_stock(
    *, actor, batch, location, quantity, reference="", notes=""
):
    require_hpms_permission(actor, "inventory.can_dispense_stock")
    validate_quantity(quantity)

    if not location.is_active:
        raise ValidationError("This stock location is inactive.")

    if not batch.is_active:
        raise ValidationError("This medicine batch is inactive.")

    if batch.expiry_date <= timezone.localdate():
        raise ValidationError("Expired medicine cannot be dispensed.")

    with transaction.atomic():
        try:
            balance = StockBalance.objects.select_for_update().get(
                batch=batch,
                location=location,
            )
        except StockBalance.DoesNotExist:
            raise ValidationError("No stock exists at this location.")

        if balance.quantity < quantity:
            raise ValidationError("Insufficient stock for dispensing.")

        balance.quantity -= quantity
        balance.save(update_fields=["quantity", "updated_at"])

        StockMovement.objects.create(
            batch=batch,
            movement_type=StockMovement.MovementType.DISPENSE,
            source_location=location,
            quantity=quantity,
            performed_by=actor,
            reference=reference,
            notes=notes,
        )

    return True


def dispense_medicine_fefo(
    *, actor, medicine, location, quantity, reference="", notes=""
):
    """
    Dispense a medicine using First Expiry, First Out.
    A single issue may consume several batches.
    """
    require_hpms_permission(actor, "inventory.can_dispense_stock")
    validate_quantity(quantity)

    if not medicine.is_active:
        raise ValidationError("Inactive medicines cannot be dispensed.")

    if not location.is_active:
        raise ValidationError("This stock location is inactive.")

    today = timezone.localdate()

    with transaction.atomic():
        balances = list(
            StockBalance.objects.select_for_update()
            .select_related("batch")
            .filter(
                batch__medicine=medicine,
                batch__is_active=True,
                batch__expiry_date__gt=today,
                location=location,
                quantity__gt=0,
            )
            .order_by("batch__expiry_date", "batch__created_at", "pk")
        )

        available = sum(balance.quantity for balance in balances)

        if available < quantity:
            raise ValidationError(
                f"Insufficient usable stock. Available: {available}; "
                f"requested: {quantity}."
            )

        remaining = quantity
        allocations = []

        for balance in balances:
            if remaining == 0:
                break

            issued = min(balance.quantity, remaining)

            balance.quantity -= issued
            balance.save(update_fields=["quantity", "updated_at"])

            movement = StockMovement.objects.create(
                batch=balance.batch,
                movement_type=StockMovement.MovementType.DISPENSE,
                source_location=location,
                quantity=issued,
                performed_by=actor,
                reference=reference,
                notes=notes or "FEFO medicine issue",
            )

            allocations.append({
                "batch": balance.batch,
                "quantity": issued,
                "movement": movement,
            })

            remaining -= issued

    return allocations


def return_stock(
    *, actor, batch, source_location, destination_location,
    quantity, reference="", notes=""
):
    """
    Return usable stock from one location to another.
    The original batch is retained.
    """
    require_hpms_permission(actor, "inventory.can_transfer_stock")
    validate_quantity(quantity)

    if source_location.pk == destination_location.pk:
        raise ValidationError("Source and destination must be different.")

    if not source_location.is_active or not destination_location.is_active:
        raise ValidationError("Both locations must be active.")

    if not batch.is_active:
        raise ValidationError("Inactive batches cannot be returned.")

    if batch.expiry_date <= timezone.localdate():
        raise ValidationError("Expired medicine cannot be returned to usable stock.")

    with transaction.atomic():
        try:
            source = StockBalance.objects.select_for_update().get(
                batch=batch,
                location=source_location,
            )
        except StockBalance.DoesNotExist:
            raise ValidationError("No stock exists at the return source.")

        if source.quantity < quantity:
            raise ValidationError("Insufficient stock available for return.")

        destination, _ = StockBalance.objects.get_or_create(
            batch=batch,
            location=destination_location,
            defaults={"quantity": 0},
        )

        destination = StockBalance.objects.select_for_update().get(
            pk=destination.pk
        )

        source.quantity -= quantity
        destination.quantity = F("quantity") + quantity

        source.save(update_fields=["quantity", "updated_at"])
        destination.save(update_fields=["quantity", "updated_at"])

        StockMovement.objects.create(
            batch=batch,
            movement_type=StockMovement.MovementType.RETURN,
            source_location=source_location,
            destination_location=destination_location,
            quantity=quantity,
            performed_by=actor,
            reference=reference,
            notes=notes,
        )

    return True


def adjust_stock(*, actor, batch, location, quantity_change, reason):
    require_hpms_permission(actor, "inventory.can_adjust_stock")

    if isinstance(quantity_change, bool) or not isinstance(quantity_change, int):
        raise ValidationError("Stock adjustment must be a whole number.")

    if quantity_change == 0:
        raise ValidationError("Stock adjustment cannot be zero.")

    if not reason or not reason.strip():
        raise ValidationError("A reason is required for stock adjustment.")

    if not location.is_active:
        raise ValidationError("Inactive locations cannot be adjusted.")

    with transaction.atomic():
        balance, _ = StockBalance.objects.get_or_create(
            batch=batch,
            location=location,
            defaults={"quantity": 0},
        )

        balance = StockBalance.objects.select_for_update().get(pk=balance.pk)
        new_quantity = balance.quantity + quantity_change

        if new_quantity < 0:
            raise ValidationError("Adjustment would result in negative stock.")

        balance.quantity = new_quantity
        balance.save(update_fields=["quantity", "updated_at"])

        movement_type = (
            StockMovement.MovementType.ADJUSTMENT_IN
            if quantity_change > 0
            else StockMovement.MovementType.ADJUSTMENT_OUT
        )

        StockMovement.objects.create(
            batch=batch,
            movement_type=movement_type,
            source_location=location if quantity_change < 0 else None,
            destination_location=location if quantity_change > 0 else None,
            quantity=abs(quantity_change),
            performed_by=actor,
            notes=reason.strip(),
        )

    return balance


def get_available_batches(*, medicine, location):
    return (
        StockBalance.objects
        .select_related("batch", "batch__medicine", "location")
        .filter(
            batch__medicine=medicine,
            location=location,
            quantity__gt=0,
            batch__is_active=True,
            batch__expiry_date__gt=timezone.localdate(),
        )
        .order_by("batch__expiry_date", "batch__created_at")
    )


def get_expiring_stock(*, days=90):
    today = timezone.localdate()
    cutoff = today + timedelta(days=days)

    return (
        StockBalance.objects
        .select_related("batch", "batch__medicine", "location")
        .filter(
            quantity__gt=0,
            batch__expiry_date__gte=today,
            batch__expiry_date__lte=cutoff,
            batch__is_active=True,
        )
        .order_by("batch__expiry_date")
    )


def get_expired_stock():
    return (
        StockBalance.objects
        .select_related("batch", "batch__medicine", "location")
        .filter(
            quantity__gt=0,
            batch__expiry_date__lt=timezone.localdate(),
        )
        .order_by("batch__expiry_date")
    )
