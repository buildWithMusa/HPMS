from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UserManager(BaseUserManager):
    """Manager for creating hospital staff accounts using email."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model for the Hospital Pharmacy Management System."""

    username = None

    email = models.EmailField(
        unique=True,
        verbose_name="Email Address"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

class HPMSAccessPolicy(models.Model):
    """
    Central catalogue for HPMS business-level permissions.

    This model does not create a database table.
    Django registers its custom permissions in auth_permission.
    """

    class Meta:
        managed = False
        default_permissions = ()

        verbose_name = "HPMS Access Policy"
        verbose_name_plural = "HPMS Access Policies"

        permissions = [
            (
                "can_create_prescription",
                "Can create electronic prescriptions",
            ),
            (
                "can_verify_prescription",
                "Can verify prescriptions",
            ),
            (
                "can_dispense_medicine",
                "Can dispense medicine",
            ),
            (
                "can_request_ward_stock",
                "Can request ward stock",
            ),
            (
                "can_receive_stock",
                "Can receive medicine stock",
            ),
            (
                "can_approve_stock_adjustment",
                "Can approve stock adjustments",
            ),
            (
                "can_create_purchase_order",
                "Can create purchase orders",
            ),
            (
                "can_approve_purchase_order",
                "Can approve purchase orders",
            ),
            (
                "can_process_patient_payment",
                "Can process patient payments",
            ),
            (
                "can_reconcile_payments",
                "Can reconcile payments",
            ),
            (
                "can_view_financial_reports",
                "Can view financial reports",
            ),
            (
                "can_authorize_refund",
                "Can authorize patient refunds",
            ),
            (
                "can_manage_staff_access",
                "Can manage staff access and roles",
            ),
            (  "can_access_all_departments",
                "Can access all hospital departments"),
        ]

