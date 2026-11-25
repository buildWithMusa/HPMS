
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

from hospital.models import Department, ServiceArea


class StaffProfile(models.Model):

    class EmploymentStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ON_LEAVE = "ON_LEAVE", "On Leave"
        SUSPENDED = "SUSPENDED", "Suspended"
        TERMINATED = "TERMINATED", "Terminated"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="staff_profile"
    )

    staff_number = models.CharField(
        max_length=30,
        unique=True
    )

    first_name = models.CharField(
        max_length=100
    )

    middle_name = models.CharField(
        max_length=100,
        blank=True
    )

    last_name = models.CharField(
        max_length=100
    )

    job_title = models.CharField(
        max_length=100
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True
    )

    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.ACTIVE
    )

    date_employed = models.DateField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["staff_number"]
        verbose_name = "Staff Profile"
        verbose_name_plural = "Staff Profiles"

    def __str__(self):
        return f"{self.staff_number} - {self.first_name} {self.last_name}"


class StaffAssignment(models.Model):

    staff = models.ForeignKey(
        StaffProfile,
        on_delete=models.PROTECT,
        related_name="assignments"
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="staff_assignments"
    )

    service_area = models.ForeignKey(
        ServiceArea,
        on_delete=models.PROTECT,
        related_name="staff_assignments",
        null=True,
        blank=True
    )

    is_primary = models.BooleanField(
        default=False
    )

    start_date = models.DateField(
        default=timezone.localdate
    )

    end_date = models.DateField(
        null=True,
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Staff Assignment"
        verbose_name_plural = "Staff Assignments"

    def __str__(self):
        return f"{self.staff} - {self.department.name}"
