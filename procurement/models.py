from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Supplier(models.Model):
    name = models.CharField(max_length=200, unique=True)
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    kra_pin = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        permissions = [
            ("can_manage_suppliers", "Can manage medicine suppliers"),
            ("can_view_procurement", "Can view procurement records"),
            ("can_submit_purchase_order", "Can submit purchase orders"),
            ("can_receive_purchase_order", "Can receive purchase order deliveries"),
        ]

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted for approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED", "Partially received"
        RECEIVED = "RECEIVED", "Fully received"
        CANCELLED = "CANCELLED", "Cancelled"

    order_number = models.CharField(max_length=30, unique=True, blank=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="purchase_orders"
    )
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_purchase_orders",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_purchase_orders",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rejected_purchase_orders",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("can_view_all_purchase_orders", "Can view all purchase orders"),
        ]

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.order_number:
            self.order_number = f"PO-{timezone.now():%Y}-{self.pk:06d}"
            super().save(update_fields=["order_number"])

    @property
    def total_amount(self):
        return sum(
            (line.quantity_ordered * line.unit_cost for line in self.lines.all()),
            start=0,
        )

    @property
    def total_quantity(self):
        return sum(line.quantity_ordered for line in self.lines.all())

    @property
    def outstanding_quantity(self):
        return sum(
            line.quantity_ordered - line.quantity_received
            for line in self.lines.all()
        )

    def __str__(self):
        return self.order_number or f"Purchase Order {self.pk}"


class PurchaseOrderLine(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="lines"
    )
    medicine = models.ForeignKey(
        "medicines.Medicine", on_delete=models.PROTECT, related_name="purchase_order_lines"
    )
    quantity_ordered = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    quantity_received = models.PositiveIntegerField(default=0)
    unit_cost = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["purchase_order", "medicine"],
                name="unique_medicine_per_purchase_order",
            ),
            models.CheckConstraint(
                condition=Q(quantity_ordered__gte=1),
                name="po_line_quantity_at_least_one",
            ),
            models.CheckConstraint(
                condition=Q(quantity_received__lte=models.F("quantity_ordered")),
                name="po_line_received_not_over_ordered",
            ),
        ]

    @property
    def outstanding_quantity(self):
        return self.quantity_ordered - self.quantity_received

    @property
    def line_total(self):
        return self.quantity_ordered * self.unit_cost

    def __str__(self):
        return f"{self.medicine} ({self.quantity_ordered})"


class GoodsReceipt(models.Model):
    receipt_number = models.CharField(max_length=30, unique=True, blank=True)
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.PROTECT, related_name="goods_receipts"
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="goods_receipts",
    )
    supplier_delivery_note = models.CharField(max_length=100, blank=True)
    received_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.receipt_number:
            self.receipt_number = f"GRN-{timezone.now():%Y}-{self.pk:06d}"
            super().save(update_fields=["receipt_number"])

    def __str__(self):
        return self.receipt_number or f"Goods Receipt {self.pk}"


class GoodsReceiptLine(models.Model):
    goods_receipt = models.ForeignKey(
        GoodsReceipt, on_delete=models.CASCADE, related_name="lines"
    )
    purchase_order_line = models.ForeignKey(
        PurchaseOrderLine, on_delete=models.PROTECT, related_name="receipt_lines"
    )
    batch_number = models.CharField(max_length=100)
    manufacture_date = models.DateField()
    expiry_date = models.DateField()
    quantity_received = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    purchase_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    stock_batch = models.ForeignKey(
        "inventory.StockBatch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="goods_receipt_lines",
    )

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity_received__gte=1),
                name="grn_line_quantity_at_least_one",
            ),
            models.CheckConstraint(
                condition=Q(expiry_date__gt=models.F("manufacture_date")),
                name="grn_expiry_after_manufacture",
            ),
        ]

    def __str__(self):
        return f"{self.batch_number} - {self.quantity_received}"
