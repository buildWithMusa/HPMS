
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Patient(models.Model):

    class Sex(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"
        UNKNOWN = "UNKNOWN", "Unknown"

    hospital_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        editable=False
    )

    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)

    date_of_birth = models.DateField(
        null=True,
        blank=True
    )

    sex = models.CharField(
        max_length=10,
        choices=Sex.choices,
        default=Sex.UNKNOWN
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True
    )

    email = models.EmailField(blank=True)

    address = models.TextField(blank=True)
    county = models.CharField(max_length=100, blank=True)
    sub_county = models.CharField(max_length=100, blank=True)

    is_active = models.BooleanField(default=True)

    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registered_patients"
    )

    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-registered_at"]
        permissions = [
    ("can_register_patient", "Can register patients"),
    ("can_view_patient_records", "Can view patient records"),
    ("can_update_patient_records", "Can update patient records"),
    ("can_manage_patient_status", "Can activate and deactivate patients"),
]

    def clean(self):
        super().clean()

        if (
            self.date_of_birth
            and self.date_of_birth > timezone.localdate()
        ):
            raise ValidationError({
                "date_of_birth": "Date of birth cannot be in the future."
            })

    @property
    def full_name(self):
        return " ".join(
            part for part in [
                self.first_name,
                self.middle_name,
                self.last_name
            ] if part
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.hospital_number:
            year = timezone.localtime(self.registered_at).year

            self.hospital_number = (
                f"HPMS-{year}-{self.pk:08d}"
            )

            super().save(
                update_fields=["hospital_number"]
            )

    def __str__(self):
        return f"{self.hospital_number} - {self.full_name}"


class PatientIdentifier(models.Model):

    class IdentifierType(models.TextChoices):
        NATIONAL_ID = "NATIONAL_ID", "National ID"
        BIRTH_CERTIFICATE = "BIRTH_CERTIFICATE", "Birth Certificate"
        PASSPORT = "PASSPORT", "Passport"
        OTHER = "OTHER", "Other"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="identifiers"
    )

    identifier_type = models.CharField(
        max_length=30,
        choices=IdentifierType.choices
    )

    identifier_value = models.CharField(max_length=100)

    is_primary = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "identifier_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["identifier_type", "identifier_value"],
                name="unique_patient_identifier_value"
            ),
            models.UniqueConstraint(
                fields=["patient"],
                condition=Q(is_primary=True),
                name="one_primary_identifier_per_patient"
            )
        ]

    def save(self, *args, **kwargs):
        self.identifier_value = " ".join(
            self.identifier_value.split()
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.get_identifier_type_display()}: "
            f"{self.identifier_value}"
        )


class PatientGuardian(models.Model):

    class Relationship(models.TextChoices):
        MOTHER = "MOTHER", "Mother"
        FATHER = "FATHER", "Father"
        SIBLING = "SIBLING", "Sibling"
        SPOUSE = "SPOUSE", "Spouse"
        RELATIVE = "RELATIVE", "Other Relative"
        LEGAL_GUARDIAN = "LEGAL_GUARDIAN", "Legal Guardian"
        OTHER = "OTHER", "Other"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="guardians"
    )

    full_name = models.CharField(max_length=200)

    relationship = models.CharField(
        max_length=30,
        choices=Relationship.choices
    )

    phone_number = models.CharField(max_length=20)

    email = models.EmailField(blank=True)

    national_id = models.CharField(
        max_length=50,
        blank=True
    )

    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["patient"],
                condition=Q(
                    is_primary=True,
                    is_active=True
                ),
                name="one_active_primary_guardian_per_patient"
            )
        ]

    def __str__(self):
        return f"{self.full_name} - {self.patient.hospital_number}"
