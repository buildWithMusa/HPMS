
from django.db import models
from django.core.validators import MinLengthValidator


class MedicineCategory(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        validators=[MinLengthValidator(2)]
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Medicine categories"

    def __str__(self):
        return self.name


class Medicine(models.Model):

    class DosageForm(models.TextChoices):
        TABLET = "TABLET", "Tablet"
        CAPSULE = "CAPSULE", "Capsule"
        SYRUP = "SYRUP", "Syrup"
        SUSPENSION = "SUSPENSION", "Suspension"
        INJECTION = "INJECTION", "Injection"
        CREAM = "CREAM", "Cream"
        OINTMENT = "OINTMENT", "Ointment"
        DROPS = "DROPS", "Drops"
        INHALER = "INHALER", "Inhaler"
        SUPPOSITORY = "SUPPOSITORY", "Suppository"
        OTHER = "OTHER", "Other"

    class UnitOfMeasure(models.TextChoices):
        TABLET = "TABLET", "Tablet"
        CAPSULE = "CAPSULE", "Capsule"
        BOTTLE = "BOTTLE", "Bottle"
        VIAL = "VIAL", "Vial"
        AMPOULE = "AMPOULE", "Ampoule"
        TUBE = "TUBE", "Tube"
        PACK = "PACK", "Pack"
        SACHET = "SACHET", "Sachet"
        PIECE = "PIECE", "Piece"

    category = models.ForeignKey(
        MedicineCategory,
        on_delete=models.PROTECT,
        related_name="medicines"
    )

    generic_name = models.CharField(max_length=200)
    brand_name = models.CharField(max_length=200, blank=True)

    strength = models.CharField(
        max_length=100,
        help_text="For example: 500 mg, 250 mg/5 ml or 10 mg/ml."
    )

    dosage_form = models.CharField(
        max_length=20,
        choices=DosageForm.choices
    )

    unit_of_measure = models.CharField(
        max_length=20,
        choices=UnitOfMeasure.choices
    )

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["generic_name", "strength"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "generic_name",
                    "brand_name",
                    "strength",
                    "dosage_form",
                ],
                name="unique_medicine_identity"
            )
        ]
        permissions = [
            (
                "can_manage_medicine_status",
                "Can activate and deactivate medicines"
            ),
        ]

    @property
    def display_name(self):
        if self.brand_name:
            return (
                f"{self.generic_name} ({self.brand_name}) "
                f"{self.strength} - {self.get_dosage_form_display()}"
            )

        return (
            f"{self.generic_name} {self.strength} "
            f"- {self.get_dosage_form_display()}"
        )

    def __str__(self):
        return self.display_name
