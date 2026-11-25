from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from patients.models import Patient
from medicines.models import Medicine, MedicineCategory
from inventory.models import StockLocation, StockBatch, StockBalance, StockMovement
from prescriptions.models import Prescription, PrescriptionLine
from .models import Dispensing
from .services import dispense_prescription_line


User = get_user_model()


class DispensingServiceTests(TestCase):
    def setUp(self):
        self.pharmacist = User.objects.create_user(
            email="pharmacist@example.com",
            password="TestPassword123!"
        )
        self.doctor = User.objects.create_user(
            email="doctor@example.com",
            password="TestPassword123!"
        )

        permission_codes = [
            ("dispensing", "can_dispense_prescription"),
            ("inventory", "can_dispense_stock"),
        ]
        for app, code in permission_codes:
            permission = Permission.objects.get(
                content_type__app_label=app,
                codename=code,
            )
            self.pharmacist.user_permissions.add(permission)

        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
        )
        category = MedicineCategory.objects.create(name="Analgesics")
        self.medicine = Medicine.objects.create(
            category=category,
            generic_name="Paracetamol",
            strength="500 mg",
            dosage_form="TABLET",
            unit_of_measure="TABLET",
        )
        self.location = StockLocation.objects.create(
            name="Central Pharmacy",
            location_type="CENTRAL",
        )

        today = timezone.localdate()
        self.batch = StockBatch.objects.create(
            medicine=self.medicine,
            batch_number="PARA-001",
            manufacture_date=today - timedelta(days=30),
            expiry_date=today + timedelta(days=365),
            purchase_price=Decimal("1.00"),
            selling_price=Decimal("2.00"),
        )
        self.balance = StockBalance.objects.create(
            batch=self.batch,
            location=self.location,
            quantity=100,
        )

        self.prescription = Prescription.objects.create(
            patient=self.patient,
            source="ELECTRONIC",
            prescribed_by=self.doctor,
            recorded_by=self.doctor,
            status="DRAFT",
        )
        self.line = PrescriptionLine.objects.create(
            prescription=self.prescription,
            medicine=self.medicine,
            dose="1 tablet",
            route="ORAL",
            frequency="Twice daily",
            duration_days=5,
            quantity=10,
        )
        self.prescription.status = Prescription.Status.VERIFIED
        self.prescription.save(update_fields=["status"])

    def test_dispensing_reduces_stock_and_records_batch(self):
        record = dispense_prescription_line(
            actor=self.pharmacist,
            prescription=self.prescription,
            prescription_line=self.line,
            quantity=4,
        )
        self.balance.refresh_from_db()

        self.assertEqual(self.balance.quantity, 96)
        self.assertEqual(record.quantity, 4)
        self.assertEqual(record.batch_allocations.count(), 1)
        self.assertEqual(
            record.batch_allocations.first().stock_movement.movement_type,
            StockMovement.MovementType.DISPENSE,
        )
        self.prescription.refresh_from_db()
        self.assertEqual(
            self.prescription.status,
            Prescription.Status.PARTIALLY_DISPENSED,
        )

    def test_partial_dispensings_can_complete_prescription(self):
        dispense_prescription_line(
            actor=self.pharmacist,
            prescription=self.prescription,
            prescription_line=self.line,
            quantity=4,
        )
        dispense_prescription_line(
            actor=self.pharmacist,
            prescription=self.prescription,
            prescription_line=self.line,
            quantity=6,
        )

        self.prescription.refresh_from_db()
        self.assertEqual(
            self.prescription.status,
            Prescription.Status.DISPENSED,
        )
        self.assertEqual(
            Dispensing.objects.filter(
                prescription_line=self.line
            ).aggregate(total=__import__("django").db.models.Sum("quantity"))["total"],
            10,
        )

    def test_cannot_dispense_more_than_prescribed(self):
        with self.assertRaises(ValidationError):
            dispense_prescription_line(
                actor=self.pharmacist,
                prescription=self.prescription,
                prescription_line=self.line,
                quantity=11,
            )

        self.balance.refresh_from_db()
        self.assertEqual(self.balance.quantity, 100)

    def test_cannot_dispense_unverified_prescription(self):
        self.prescription.status = Prescription.Status.SUBMITTED
        self.prescription.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            dispense_prescription_line(
                actor=self.pharmacist,
                prescription=self.prescription,
                prescription_line=self.line,
                quantity=2,
            )

        self.balance.refresh_from_db()
        self.assertEqual(self.balance.quantity, 100)

    def test_fefo_uses_earliest_expiry_batch_first(self):
        today = timezone.localdate()
        earlier = StockBatch.objects.create(
            medicine=self.medicine,
            batch_number="PARA-002",
            manufacture_date=today - timedelta(days=20),
            expiry_date=today + timedelta(days=60),
            purchase_price=Decimal("1.00"),
            selling_price=Decimal("2.00"),
        )
        StockBalance.objects.create(
            batch=earlier,
            location=self.location,
            quantity=3,
        )

        record = dispense_prescription_line(
            actor=self.pharmacist,
            prescription=self.prescription,
            prescription_line=self.line,
            quantity=5,
        )

        allocations = list(record.batch_allocations.order_by("id"))
        self.assertEqual(allocations[0].batch, earlier)
        self.assertEqual(allocations[0].quantity, 3)
        self.assertEqual(allocations[1].batch, self.batch)
        self.assertEqual(allocations[1].quantity, 2)
