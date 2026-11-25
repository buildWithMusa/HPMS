from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from medicines.models import Medicine, MedicineCategory
from .models import StockLocation, StockBalance, StockMovement
from .services import (
    receive_stock,
    dispense_stock,
    dispense_medicine_fefo,
    adjust_stock,
)


User = get_user_model()


class InventoryServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="inventory-test@hpms.local",
            password="TestPassword123!",
        )

        permissions = Permission.objects.filter(
            codename__in=[
                "can_receive_stock",
                "can_dispense_stock",
                "can_adjust_stock",
                "can_transfer_stock",
                "can_view_inventory",
            ]
        )
        self.user.user_permissions.add(*permissions)

        self.category = MedicineCategory.objects.create(
            name="Test Medicines",
        )

        self.medicine = Medicine.objects.create(
            category=self.category,
            generic_name="Paracetamol",
            brand_name="",
            strength="500 mg",
            dosage_form=Medicine.DosageForm.TABLET,
            unit_of_measure=Medicine.UnitOfMeasure.TABLET,
        )

        self.central = StockLocation.objects.get(
            location_type=StockLocation.LocationType.CENTRAL
        ) if StockLocation.objects.filter(
            location_type=StockLocation.LocationType.CENTRAL
        ).exists() else StockLocation.objects.create(
            name="Central Pharmacy",
            location_type=StockLocation.LocationType.CENTRAL,
        )

        self.today = timezone.localdate()
        self.manufacture_date = self.today - timedelta(days=30)

    def receive(self, batch_number, quantity, expiry_days):
        return receive_stock(
            actor=self.user,
            medicine=self.medicine,
            batch_number=batch_number,
            manufacture_date=self.manufacture_date,
            expiry_date=self.today + timedelta(days=expiry_days),
            quantity=quantity,
            purchase_price=Decimal("5.00"),
            selling_price=Decimal("8.00"),
            notes="Automated test receipt",
        )

    def test_receiving_stock_creates_batch_balance_and_movement(self):
        batch = self.receive("TEST-001", 100, 180)

        balance = StockBalance.objects.get(
            batch=batch,
            location=self.central,
        )

        self.assertEqual(balance.quantity, 100)
        self.assertTrue(
            StockMovement.objects.filter(
                batch=batch,
                movement_type=StockMovement.MovementType.RECEIPT,
                quantity=100,
            ).exists()
        )

    def test_receiving_same_batch_adds_to_existing_balance(self):
        batch = self.receive("TEST-002", 50, 180)
        self.receive("TEST-002", 30, 180)

        balance = StockBalance.objects.get(
            batch=batch,
            location=self.central,
        )

        self.assertEqual(balance.quantity, 80)

    def test_fefo_dispensing_uses_earliest_expiry_first(self):
        first_batch = self.receive("FEFO-001", 4, 30)
        second_batch = self.receive("FEFO-002", 10, 90)

        allocations = dispense_medicine_fefo(
            actor=self.user,
            medicine=self.medicine,
            location=self.central,
            quantity=7,
            reference="FEFO-TEST",
        )

        self.assertEqual(
            [(item["batch"].pk, item["quantity"]) for item in allocations],
            [(first_batch.pk, 4), (second_batch.pk, 3)],
        )

        first_balance = StockBalance.objects.get(
            batch=first_batch,
            location=self.central,
        )
        second_balance = StockBalance.objects.get(
            batch=second_batch,
            location=self.central,
        )

        self.assertEqual(first_balance.quantity, 0)
        self.assertEqual(second_balance.quantity, 7)

    def test_fefo_rejects_insufficient_stock_without_changing_balances(self):
        self.receive("FEFO-003", 5, 60)

        with self.assertRaises(ValidationError):
            dispense_medicine_fefo(
                actor=self.user,
                medicine=self.medicine,
                location=self.central,
                quantity=8,
            )

        balance = StockBalance.objects.get(
            location=self.central,
            batch__batch_number="FEFO-003",
        )

        self.assertEqual(balance.quantity, 5)

    def test_direct_dispensing_reduces_stock(self):
        batch = self.receive("DISPENSE-001", 20, 60)

        dispense_stock(
            actor=self.user,
            batch=batch,
            location=self.central,
            quantity=6,
            reference="PATIENT-001",
        )

        balance = StockBalance.objects.get(
            batch=batch,
            location=self.central,
        )

        self.assertEqual(balance.quantity, 14)

    def test_adjustment_cannot_create_negative_stock(self):
        batch = self.receive("ADJUST-001", 5, 60)

        with self.assertRaises(ValidationError):
            adjust_stock(
                actor=self.user,
                batch=batch,
                location=self.central,
                quantity_change=-10,
                reason="Testing negative stock protection",
            )

        balance = StockBalance.objects.get(
            batch=batch,
            location=self.central,
        )

        self.assertEqual(balance.quantity, 5)

    def test_positive_adjustment_increases_stock(self):
        batch = self.receive("ADJUST-002", 5, 60)

        adjust_stock(
            actor=self.user,
            batch=batch,
            location=self.central,
            quantity_change=3,
            reason="Physical stock count correction",
        )

        balance = StockBalance.objects.get(
            batch=batch,
            location=self.central,
        )

        self.assertEqual(balance.quantity, 8)

    def test_unauthorized_user_cannot_receive_stock(self):
        unauthorized = User.objects.create_user(
            email="unauthorized@hpms.local",
            password="TestPassword123!",
        )

        with self.assertRaises(Exception):
            receive_stock(
                actor=unauthorized,
                medicine=self.medicine,
                batch_number="UNAUTHORIZED-001",
                manufacture_date=self.manufacture_date,
                expiry_date=self.today + timedelta(days=90),
                quantity=10,
                purchase_price=Decimal("5.00"),
                selling_price=Decimal("8.00"),
            )
