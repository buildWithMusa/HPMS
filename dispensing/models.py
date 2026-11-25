from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from prescriptions.models import Prescription, PrescriptionLine
from inventory.models import StockBatch, StockMovement


class Dispensing(models.Model):
    reference = models.CharField(
        max_length=40, unique=True, blank=True, editable=False
    )
    prescription = models.ForeignKey(
        Prescription, on_delete=models.PROTECT,
        related_name="dispensing_records"
    )
    prescription_line = models.ForeignKey(
        PrescriptionLine, on_delete=models.PROTECT,
        related_name="dispensing_records"
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    dispensed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="medicine_dispensings"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("can_dispense_prescription", "Can dispense verified prescriptions"),
            ("can_view_dispensing", "Can view dispensing records"),
        ]
        indexes = [
            models.Index(fields=["prescription", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.reference:
            year = timezone.localtime(self.created_at).year
            self.reference = f"DSP-{year}-{self.pk:08d}"
            super().save(update_fields=["reference"])

    def __str__(self):
        return self.reference or f"Dispensing {self.pk}"


class DispensingBatchAllocation(models.Model):
    dispensing = models.ForeignKey(
        Dispensing, on_delete=models.PROTECT,
        related_name="batch_allocations"
    )
    batch = models.ForeignKey(
        StockBatch, on_delete=models.PROTECT,
        related_name="dispensing_allocations"
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    stock_movement = models.OneToOneField(
        StockMovement, on_delete=models.PROTECT,
        related_name="dispensing_allocation"
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.batch.batch_number}: {self.quantity}"
