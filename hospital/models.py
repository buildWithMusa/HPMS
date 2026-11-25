
from django.db import models
from django.core.validators import MinValueValidator


class Department(models.Model):
    """
    Represents an organizational department
    within the hospital.
    """

    code = models.CharField(
        max_length=20,
        unique=True
    )

    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return f"{self.code} - {self.name}"


class ServiceArea(models.Model):
    """
    Represents a clinical or operational
    service area belonging to a department.
    """

    class AreaType(models.TextChoices):
        OUTPATIENT = "OUTPATIENT", "Outpatient"
        INPATIENT = "INPATIENT", "Inpatient"
        MATERNITY = "MATERNITY", "Maternity"
        EMERGENCY = "EMERGENCY", "Emergency"
        MENTAL_HEALTH = "MENTAL_HEALTH", "Mental Health"
        CHILDREN = "CHILDREN", "Children's Services"
        OTHER = "OTHER", "Other"

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="service_areas"
    )

    code = models.CharField(
        max_length=20
    )

    name = models.CharField(
        max_length=100
    )

    area_type = models.CharField(
        max_length=20,
        choices=AreaType.choices,
        default=AreaType.OTHER
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Service Area"
        verbose_name_plural = "Service Areas"

        constraints = [
            models.UniqueConstraint(
                fields=["department", "code"],
                name="unique_service_area_code_per_department"
            ),
            models.UniqueConstraint(
                fields=["department", "name"],
                name="unique_service_area_name_per_department"
            ),
        ]

    def __str__(self):
        return f"{self.department.name} - {self.name}"


class Ward(models.Model):
    """
    Represents a physical ward or inpatient unit
    belonging to a hospital service area.
    """

    class WardType(models.TextChoices):
        GENERAL = "GENERAL", "General Ward"
        MATERNITY = "MATERNITY", "Maternity Ward"
        PEDIATRIC = "PEDIATRIC", "Paediatric Ward"
        EMERGENCY = "EMERGENCY", "Emergency Ward"
        MENTAL_HEALTH = "MENTAL_HEALTH", "Mental Health Ward"
        ICU = "ICU", "Intensive Care Unit"
        OTHER = "OTHER", "Other"

    service_area = models.ForeignKey(
        ServiceArea,
        on_delete=models.PROTECT,
        related_name="wards"
    )

    code = models.CharField(
        max_length=20
    )

    name = models.CharField(
        max_length=100
    )

    ward_type = models.CharField(
        max_length=20,
        choices=WardType.choices,
        default=WardType.GENERAL
    )

    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)]
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Ward"
        verbose_name_plural = "Wards"

        constraints = [
            models.UniqueConstraint(
                fields=["service_area", "code"],
                name="unique_ward_code_per_service_area"
            ),
            models.UniqueConstraint(
                fields=["service_area", "name"],
                name="unique_ward_name_per_service_area"
            ),
        ]

    def __str__(self):
        return f"{self.service_area.name} - {self.name}"
