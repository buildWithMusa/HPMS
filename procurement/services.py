from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.authorization import (
    require_hpms_permission,
    authorize_approval,
)
from inventory.models import StockBatch
from inventory.services import receive_stock
from .models import (
    Supplier,
    PurchaseOrder,
    PurchaseOrderLine,
    GoodsReceipt,
    GoodsReceiptLine,
)


def _require(actor, permission):
    require_hpms_permission(actor, permission)


def create_supplier(actor, **data):
    _require(actor, "procurement.can_manage_suppliers")
    name = data.get("name", "").strip()
    if not name:
        raise ValidationError("Supplier name is required.")
    data["name"] = name
    return Supplier.objects.create(**data)


def update_supplier(actor, supplier, **data):
    _require(actor, "procurement.can_manage_suppliers")
    for field, value in data.items():
        if field == "name":
            value = value.strip()
        setattr(supplier, field, value)
    supplier.save()
    return supplier


@transaction.atomic
def create_purchase_order(actor, supplier, expected_delivery_date=None, notes=""):
    _require(actor, "accounts.can_create_purchase_order")

    if not supplier.is_active:
        raise ValidationError("You cannot create an order for an inactive supplier.")

    return PurchaseOrder.objects.create(
        supplier=supplier,
        created_by=actor,
        expected_delivery_date=expected_delivery_date,
        notes=notes,
    )


@transaction.atomic
def add_purchase_order_line(
    actor, purchase_order, medicine, quantity_ordered, unit_cost, selling_price, notes=""
):
    _require(actor, "accounts.can_create_purchase_order")

    order = PurchaseOrder.objects.select_for_update().get(pk=purchase_order.pk)
    if order.status != PurchaseOrder.Status.DRAFT:
        raise ValidationError("Lines can only be added to a draft purchase order.")

    if not medicine.is_active:
        raise ValidationError("Inactive medicines cannot be ordered.")

    if quantity_ordered < 1:
        raise ValidationError("Order quantity must be at least one.")

    if unit_cost < 0 or selling_price < 0:
        raise ValidationError("Prices cannot be negative.")

    if order.lines.filter(medicine=medicine).exists():
        raise ValidationError("This medicine is already on the purchase order.")

    return PurchaseOrderLine.objects.create(
        purchase_order=order,
        medicine=medicine,
        quantity_ordered=quantity_ordered,
        unit_cost=unit_cost,
        selling_price=selling_price,
        notes=notes,
    )


@transaction.atomic
def submit_purchase_order(actor, purchase_order):
    _require(actor, "procurement.can_submit_purchase_order")

    order = PurchaseOrder.objects.select_for_update().get(pk=purchase_order.pk)
    if order.status != PurchaseOrder.Status.DRAFT:
        raise ValidationError("Only draft purchase orders can be submitted.")

    if not order.lines.exists():
        raise ValidationError("Add at least one medicine before submitting.")

    order.status = PurchaseOrder.Status.SUBMITTED
    order.submitted_at = timezone.now()
    order.save(update_fields=["status", "submitted_at", "updated_at"])
    return order


@transaction.atomic
def approve_purchase_order(actor, purchase_order):
    order = PurchaseOrder.objects.select_for_update().get(pk=purchase_order.pk)

    if order.status != PurchaseOrder.Status.SUBMITTED:
        raise ValidationError("Only submitted purchase orders can be approved.")

    authorize_approval(
        actor,
        order.created_by,
        "accounts.can_approve_purchase_order",
    )

    order.status = PurchaseOrder.Status.APPROVED
    order.approved_by = actor
    order.approved_at = timezone.now()
    order.save(update_fields=[
        "status", "approved_by", "approved_at", "updated_at"
    ])
    return order


@transaction.atomic
def reject_purchase_order(actor, purchase_order, reason):
    order = PurchaseOrder.objects.select_for_update().get(pk=purchase_order.pk)

    if order.status != PurchaseOrder.Status.SUBMITTED:
        raise ValidationError("Only submitted purchase orders can be rejected.")

    authorize_approval(
        actor,
        order.created_by,
        "accounts.can_approve_purchase_order",
    )

    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("A rejection reason is required.")

    order.status = PurchaseOrder.Status.REJECTED
    order.rejected_by = actor
    order.rejected_at = timezone.now()
    order.rejection_reason = reason
    order.save(update_fields=[
        "status", "rejected_by", "rejected_at",
        "rejection_reason", "updated_at",
    ])
    return order


@transaction.atomic
def receive_purchase_order(
    actor,
    purchase_order,
    received_lines,
    supplier_delivery_note="",
    notes="",
):
    """
    received_lines is a list of dictionaries. Each dictionary contains:
    purchase_order_line, batch_number, manufacture_date, expiry_date,
    quantity_received, purchase_price and selling_price.
    """
    _require(actor, "procurement.can_receive_purchase_order")
    _require(actor, "accounts.can_receive_stock")

    order = PurchaseOrder.objects.select_for_update().get(pk=purchase_order.pk)

    if order.status not in (
        PurchaseOrder.Status.APPROVED,
        PurchaseOrder.Status.PARTIALLY_RECEIVED,
    ):
        raise ValidationError("Only approved orders can receive deliveries.")

    if not received_lines:
        raise ValidationError("Add at least one delivery line.")

    locked_lines = {
        line.pk: line
        for line in PurchaseOrderLine.objects.select_for_update().filter(
            purchase_order=order
        )
    }

    # Validate every line before changing any stock.
    prepared = []
    for item in received_lines:
        line = item["purchase_order_line"]
        line_id = line.pk if hasattr(line, "pk") else int(line)

        if line_id not in locked_lines:
            raise ValidationError("A delivery line does not belong to this order.")

        order_line = locked_lines[line_id]
        quantity = int(item["quantity_received"])

        if quantity < 1:
            raise ValidationError("Received quantity must be at least one.")

        if quantity > order_line.outstanding_quantity:
            raise ValidationError(
                f"Delivery exceeds the outstanding quantity for "
                f"{order_line.medicine}."
            )

        manufacture_date = item["manufacture_date"]
        expiry_date = item["expiry_date"]
        if expiry_date <= manufacture_date:
            raise ValidationError("Expiry date must be after manufacture date.")

        prepared.append((order_line, item, quantity))

    receipt = GoodsReceipt.objects.create(
        purchase_order=order,
        received_by=actor,
        supplier_delivery_note=supplier_delivery_note,
        notes=notes,
    )

    for order_line, item, quantity in prepared:
        batch_number = item["batch_number"].strip()
        if not batch_number:
            raise ValidationError("Batch number is required.")

        receive_stock(
            actor=actor,
            medicine=order_line.medicine,
            batch_number=batch_number,
            manufacture_date=item["manufacture_date"],
            expiry_date=item["expiry_date"],
            quantity=quantity,
            purchase_price=item["purchase_price"],
            selling_price=item["selling_price"],
            notes=f"Purchase order {order.order_number}; GRN {receipt.receipt_number}",
        )

        batch = StockBatch.objects.get(
            medicine=order_line.medicine,
            batch_number=batch_number,
        )

        GoodsReceiptLine.objects.create(
            goods_receipt=receipt,
            purchase_order_line=order_line,
            batch_number=batch_number,
            manufacture_date=item["manufacture_date"],
            expiry_date=item["expiry_date"],
            quantity_received=quantity,
            purchase_price=item["purchase_price"],
            selling_price=item["selling_price"],
            stock_batch=batch,
        )

        order_line.quantity_received += quantity
        order_line.save(update_fields=["quantity_received"])

    if all(line.quantity_received >= line.quantity_ordered
           for line in locked_lines.values()):
        order.status = PurchaseOrder.Status.RECEIVED
    else:
        order.status = PurchaseOrder.Status.PARTIALLY_RECEIVED

    order.save(update_fields=["status", "updated_at"])
    return receipt
