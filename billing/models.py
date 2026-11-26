
from decimal import Decimal
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Invoice(models.Model):

    class Status(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    reference = models.CharField(
        max_length=30,
        unique=True,
        blank=True
    )

    dispensing = models.OneToOneField(
        "dispensing.Dispensing",
        on_delete=models.PROTECT,
        related_name="invoice"
    )

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="invoices"
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNPAID
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_hpms_invoices"
    )

    created_at = models.DateTimeField(
        default=timezone.now
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("can_create_invoice", "Can create invoices"),
            ("can_view_billing", "Can view billing records"),
            ("can_cancel_invoice", "Can cancel invoices"),
            ("can_initiate_payment", "Can initiate simulated payments"),
            ("can_record_cash_payment", "Can record cash payments"),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = (
                f"INV-{timezone.now().year}-"
                f"{uuid.uuid4().hex[:10].upper()}"
            )

        super().save(*args, **kwargs)

    @property
    def amount_paid(self):
        return self.payments.filter(
            status=Payment.Status.SUCCESSFUL
        ).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    def __str__(self):
        return self.reference


class InvoiceLine(models.Model):

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="lines"
    )

    dispensing_allocation = models.OneToOneField(
        "dispensing.DispensingBatchAllocation",
        on_delete=models.PROTECT,
        related_name="invoice_line"
    )

    medicine_name = models.CharField(
        max_length=255
    )

    batch_number = models.CharField(
        max_length=100
    )

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    def __str__(self):
        return self.medicine_name


class Payment(models.Model):

    class Method(models.TextChoices):
        MPESA = "MPESA", "Simulated M-Pesa"
        CASH = "CASH", "Cash"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESSFUL = "SUCCESSFUL", "Successful"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name="payments"
    )

    method = models.CharField(
        max_length=10,
        choices=Method.choices
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True
    )

    transaction_reference = models.CharField(
        max_length=40,
        unique=True
    )

    receipt_number = models.CharField(
        max_length=40,
        unique=True,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING
    )

    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="initiated_hpms_payments"
    )

    created_at = models.DateTimeField(
        default=timezone.now
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.transaction_reference
