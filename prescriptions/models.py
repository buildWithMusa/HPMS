from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from patients.models import Patient
from medicines.models import Medicine


class Prescription(models.Model):

    class Source(models.TextChoices):
        ELECTRONIC = "ELECTRONIC", "Electronic"
        PAPER = "PAPER", "Paper"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        VERIFIED = "VERIFIED", "Verified"
        PARTIALLY_DISPENSED = "PARTIALLY_DISPENSED", "Partially Dispensed"
        DISPENSED = "DISPENSED", "Dispensed"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    prescription_number = models.CharField(
        max_length=40,
        unique=True,
        blank=True,
        editable=False
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="prescriptions"
    )

    source = models.CharField(
        max_length=15,
        choices=Source.choices,
        default=Source.ELECTRONIC
    )

    prescribed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="issued_prescriptions"
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_prescriptions"
    )

    paper_prescriber_name = models.CharField(
        max_length=200,
        blank=True
    )

    paper_prescriber_registration = models.CharField(
        max_length=100,
        blank=True
    )

    external_reference = models.CharField(
        max_length=100,
        blank=True
    )

    diagnosis = models.CharField(max_length=255, blank=True)
    clinical_notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.DRAFT
    )

    submitted_at = models.DateTimeField(null=True, blank=True)

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="verified_prescriptions"
    )

    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("can_create_prescription", "Can create electronic prescriptions"),
            ("can_view_prescriptions", "Can view prescription records"),
            ("can_verify_prescription", "Can verify prescriptions"),
            ("can_register_paper_prescription", "Can register paper prescriptions"),
            ("can_cancel_prescription", "Can cancel prescriptions"),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["patient", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.prescription_number:
            year = timezone.localtime(self.created_at).year
            self.prescription_number = (
                f"RX-{year}-{self.pk:08d}"
            )
            super().save(update_fields=["prescription_number"])

    def clean(self):
        super().clean()

        if self.source == self.Source.ELECTRONIC:
            if not self.prescribed_by_id:
                raise ValidationError({
                    "prescribed_by": "An electronic prescription must have a prescriber."
                })

        if self.source == self.Source.PAPER:
            if not self.paper_prescriber_name.strip():
                raise ValidationError({
                    "paper_prescriber_name": "Enter the name of the paper prescription's prescriber."
                })

    def __str__(self):
        return self.prescription_number or f"Prescription {self.pk}"


class PrescriptionLine(models.Model):

    class Route(models.TextChoices):
        ORAL = "ORAL", "Oral"
        INTRAVENOUS = "IV", "Intravenous"
        INTRAMUSCULAR = "IM", "Intramuscular"
        SUBCUTANEOUS = "SC", "Subcutaneous"
        TOPICAL = "TOPICAL", "Topical"
        INHALATION = "INHALATION", "Inhalation"
        OPHTHALMIC = "OPHTHALMIC", "Eye"
        OTIC = "OTIC", "Ear"
        RECTAL = "RECTAL", "Rectal"
        OTHER = "OTHER", "Other"

    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.PROTECT,
        related_name="lines"
    )

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="prescription_lines"
    )

    dose = models.CharField(
        max_length=100,
        help_text="For example: 1 tablet or 5 ml."
    )

    route = models.CharField(
        max_length=20,
        choices=Route.choices,
        default=Route.ORAL
    )

    frequency = models.CharField(
        max_length=100,
        help_text="For example: Twice daily or every 8 hours."
    )

    duration_days = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)]
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    instructions = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["prescription", "medicine"],
                name="unique_medicine_per_prescription"
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="prescription_line_quantity_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(duration_days__gte=1),
                name="prescription_line_duration_positive"
            ),
        ]

    def clean(self):
        super().clean()

        if self.medicine_id and not self.medicine.is_active:
            raise ValidationError({
                "medicine": "An inactive medicine cannot be prescribed."
            })

        if self.prescription_id:
            if self.prescription.status != Prescription.Status.DRAFT:
                raise ValidationError(
                    "Medicine lines can only be changed while the prescription is a draft."
                )

    def __str__(self):
        return f"{self.medicine} - {self.dose}"
