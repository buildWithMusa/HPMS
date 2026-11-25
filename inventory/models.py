from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from hospital.models import Ward
from medicines.models import Medicine


class StockLocation(models.Model):

    class LocationType(models.TextChoices):
        CENTRAL = "CENTRAL", "Central Pharmacy"
        WARD = "WARD", "Hospital Ward"

    name = models.CharField(max_length=150)

    location_type = models.CharField(
        max_length=20,
        choices=LocationType.choices
    )

    ward = models.OneToOneField(
        Ward,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_location"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["location_type"],
                condition=Q(location_type="CENTRAL"),
                name="one_central_pharmacy_location"
            ),
            models.CheckConstraint(
                condition=(
                    Q(location_type="CENTRAL", ward__isnull=True)
                    | Q(location_type="WARD", ward__isnull=False)
                ),
                name="stock_location_type_matches_ward"
            ),
        ]

    def clean(self):
        super().clean()

        if self.location_type == self.LocationType.CENTRAL and self.ward_id:
            raise ValidationError(
                {"ward": "The central pharmacy cannot be linked to a ward."}
            )

        if self.location_type == self.LocationType.WARD and not self.ward_id:
            raise ValidationError(
                {"ward": "A ward stock location must be linked to a ward."}
            )

    def __str__(self):
        if self.ward_id:
            return f"{self.name} - {self.ward.name}"
        return self.name


class StockBatch(models.Model):

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="stock_batches"
    )

    batch_number = models.CharField(max_length=100)

    manufacture_date = models.DateField()

    expiry_date = models.DateField()

    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    notes = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expiry_date", "batch_number"]

        constraints = [
            models.UniqueConstraint(
                fields=["medicine", "batch_number"],
                name="unique_medicine_batch_number"
            ),
            models.CheckConstraint(
                condition=Q(expiry_date__gt=models.F("manufacture_date")),
                name="batch_expiry_after_manufacture"
            ),
        ]

        indexes = [
            models.Index(fields=["expiry_date", "is_active"]),
            models.Index(fields=["medicine", "batch_number"]),
        ]

    def clean(self):
        super().clean()

        if self.expiry_date and self.manufacture_date:
            if self.expiry_date <= self.manufacture_date:
                raise ValidationError(
                    {"expiry_date": "Expiry date must be after manufacture date."}
                )

    def __str__(self):
        return f"{self.medicine.display_name} - {self.batch_number}"


class StockBalance(models.Model):

    batch = models.ForeignKey(
        StockBatch,
        on_delete=models.PROTECT,
        related_name="balances"
    )

    location = models.ForeignKey(
        StockLocation,
        on_delete=models.PROTECT,
        related_name="stock_balances"
    )

    quantity = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["batch__expiry_date"]

        constraints = [
            models.UniqueConstraint(
                fields=["batch", "location"],
                name="unique_batch_stock_per_location"
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=0),
                name="stock_quantity_nonnegative"
            ),
        ]

    def __str__(self):
        return (
            f"{self.batch} at {self.location}: "
            f"{self.quantity}"
        )


class StockMovement(models.Model):

    class MovementType(models.TextChoices):
        RECEIPT = "RECEIPT", "Stock Received"
        TRANSFER = "TRANSFER", "Stock Transfer"
        DISPENSE = "DISPENSE", "Medicine Dispensed"
        ADJUSTMENT_IN = "ADJUSTMENT_IN", "Stock Adjustment In"
        ADJUSTMENT_OUT = "ADJUSTMENT_OUT", "Stock Adjustment Out"
        RETURN = "RETURN", "Stock Returned"

    batch = models.ForeignKey(
        StockBatch,
        on_delete=models.PROTECT,
        related_name="movements"
    )

    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices
    )

    source_location = models.ForeignKey(
        StockLocation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="outgoing_movements"
    )

    destination_location = models.ForeignKey(
        StockLocation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incoming_movements"
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_movements"
    )

    reference = models.CharField(max_length=100, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

        permissions = [
            ("can_transfer_stock", "Can transfer stock between locations"),
            ("can_adjust_stock", "Can adjust stock balances"),
            ("can_dispense_stock", "Can dispense stock"),
            ("can_view_inventory", "Can view inventory records"),
        ]

        indexes = [
            models.Index(fields=["movement_type", "created_at"]),
            models.Index(fields=["batch", "created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.get_movement_type_display()} - "
            f"{self.batch.batch_number} - {self.quantity}"
        )
