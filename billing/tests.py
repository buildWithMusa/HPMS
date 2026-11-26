from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from patients.models import Patient
from medicines.models import Medicine, MedicineCategory
from inventory.models import (
    StockLocation,
    StockBatch,
    StockBalance,
)
from prescriptions.models import Prescription, PrescriptionLine
from dispensing.services import dispense_prescription_line

from .models import Invoice, InvoiceLine, Payment
from .services import create_invoice, simulate_payment


User = get_user_model()


class BillingServiceTests(TestCase):

    def setUp(self):
        self.pharmacist = User.objects.create_user(
            email="pharmacist@example.com",
            password="TestPassword123!"
        )

        self.cashier = User.objects.create_user(
            email="cashier@example.com",
            password="TestPassword123!"
        )

        self.unauthorized_user = User.objects.create_user(
            email="unauthorized@example.com",
            password="TestPassword123!"
        )

        permission_codes = [
            ("billing", "can_create_invoice"),
            ("billing", "can_view_billing"),
            ("billing", "can_initiate_payment"),
            ("billing", "can_record_cash_payment"),
            ("dispensing", "can_dispense_prescription"),
            ("inventory", "can_dispense_stock"),
        ]

        for app, code in permission_codes:
            permission = Permission.objects.get(
                content_type__app_label=app,
                codename=code,
            )

            self.pharmacist.user_permissions.add(permission)

        cashier_codes = [
            "can_create_invoice",
            "can_view_billing",
            "can_initiate_payment",
            "can_record_cash_payment",
        ]

        for code in cashier_codes:
            permission = Permission.objects.get(
                content_type__app_label="billing",
                codename=code,
            )
            self.cashier.user_permissions.add(permission)

        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
        )

        category = MedicineCategory.objects.create(
            name="Analgesics"
        )

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
            selling_price=Decimal("2.50"),
        )

        self.balance = StockBalance.objects.create(
            batch=self.batch,
            location=self.location,
            quantity=100,
        )

        self.prescription = Prescription.objects.create(
            patient=self.patient,
            source="ELECTRONIC",
            prescribed_by=self.pharmacist,
            recorded_by=self.pharmacist,
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

        self.dispensing = dispense_prescription_line(
            actor=self.pharmacist,
            prescription=self.prescription,
            prescription_line=self.line,
            quantity=4,
        )

        self.invoice = create_invoice(
            actor=self.cashier,
            dispensing=self.dispensing,
        )

    def test_invoice_created_from_dispensing(self):
        self.assertEqual(self.invoice.patient, self.patient)
        self.assertEqual(self.invoice.total_amount, Decimal("10.00"))
        self.assertEqual(self.invoice.status, Invoice.Status.UNPAID)

        self.assertEqual(self.invoice.lines.count(), 1)

        invoice_line = self.invoice.lines.first()

        self.assertEqual(invoice_line.medicine_name, "Paracetamol 500 mg - Tablet")
        self.assertEqual(invoice_line.batch_number, "PARA-001")
        self.assertEqual(invoice_line.quantity, 4)
        self.assertEqual(invoice_line.unit_price, Decimal("2.50"))
        self.assertEqual(invoice_line.line_total, Decimal("10.00"))

    def test_duplicate_invoice_is_not_created(self):
        second_invoice = create_invoice(
            actor=self.cashier,
            dispensing=self.dispensing,
        )

        self.assertEqual(second_invoice.pk, self.invoice.pk)
        self.assertEqual(
            Invoice.objects.filter(dispensing=self.dispensing).count(),
            1,
        )

    def test_successful_simulated_mpesa_payment(self):
        payment = simulate_payment(
            actor=self.cashier,
            invoice=self.invoice,
            amount=Decimal("10.00"),
            method=Payment.Method.MPESA,
            outcome="SUCCESSFUL",
            phone_number="0712345678",
        )

        self.invoice.refresh_from_db()

        self.assertEqual(payment.status, Payment.Status.SUCCESSFUL)
        self.assertTrue(payment.receipt_number)
        self.assertTrue(payment.completed_at)

        self.assertEqual(self.invoice.amount_paid, Decimal("10.00"))
        self.assertEqual(self.invoice.balance, Decimal("0.00"))
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)

    def test_partial_payment_updates_invoice_balance(self):
        payment = simulate_payment(
            actor=self.cashier,
            invoice=self.invoice,
            amount=Decimal("4.00"),
            method=Payment.Method.MPESA,
            outcome="SUCCESSFUL",
            phone_number="0712345678",
        )

        self.invoice.refresh_from_db()

        self.assertEqual(payment.status, Payment.Status.SUCCESSFUL)
        self.assertEqual(self.invoice.amount_paid, Decimal("4.00"))
        self.assertEqual(self.invoice.balance, Decimal("6.00"))
        self.assertEqual(
            self.invoice.status,
            Invoice.Status.PARTIALLY_PAID,
        )

    def test_failed_payment_does_not_reduce_balance(self):
        payment = simulate_payment(
            actor=self.cashier,
            invoice=self.invoice,
            amount=Decimal("10.00"),
            method=Payment.Method.MPESA,
            outcome="FAILED",
            phone_number="0712345678",
        )

        self.invoice.refresh_from_db()

        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertIsNone(payment.receipt_number)
        self.assertEqual(self.invoice.amount_paid, Decimal("0.00"))
        self.assertEqual(self.invoice.balance, Decimal("10.00"))
        self.assertEqual(self.invoice.status, Invoice.Status.UNPAID)

    def test_cancelled_payment_does_not_mark_invoice_paid(self):
        payment = simulate_payment(
            actor=self.cashier,
            invoice=self.invoice,
            amount=Decimal("10.00"),
            method=Payment.Method.MPESA,
            outcome="CANCELLED",
            phone_number="0712345678",
        )

        self.invoice.refresh_from_db()

        self.assertEqual(payment.status, Payment.Status.CANCELLED)
        self.assertIsNone(payment.receipt_number)
        self.assertEqual(self.invoice.status, Invoice.Status.UNPAID)
        self.assertEqual(self.invoice.balance, Decimal("10.00"))

    def test_cannot_pay_more_than_invoice_balance(self):
        with self.assertRaises(ValidationError):
            simulate_payment(
                actor=self.cashier,
                invoice=self.invoice,
                amount=Decimal("15.00"),
                method=Payment.Method.MPESA,
                outcome="SUCCESSFUL",
                phone_number="0712345678",
            )

        self.assertEqual(Payment.objects.count(), 0)

    def test_cannot_pay_already_paid_invoice_again(self):
        simulate_payment(
            actor=self.cashier,
            invoice=self.invoice,
            amount=Decimal("10.00"),
            method=Payment.Method.MPESA,
            outcome="SUCCESSFUL",
            phone_number="0712345678",
        )

        with self.assertRaises(ValidationError):
            simulate_payment(
                actor=self.cashier,
                invoice=self.invoice,
                amount=Decimal("1.00"),
                method=Payment.Method.MPESA,
                outcome="SUCCESSFUL",
                phone_number="0712345678",
            )

        self.assertEqual(Payment.objects.count(), 1)

    def test_cash_payment_is_supported(self):
        payment = simulate_payment(
            actor=self.cashier,
            invoice=self.invoice,
            amount=Decimal("10.00"),
            method=Payment.Method.CASH,
            outcome="SUCCESSFUL",
        )

        self.invoice.refresh_from_db()

        self.assertEqual(payment.method, Payment.Method.CASH)
        self.assertEqual(payment.status, Payment.Status.SUCCESSFUL)
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)

    def test_unauthorized_user_cannot_create_invoice(self):
        with self.assertRaises(PermissionDenied):
            create_invoice(
                actor=self.unauthorized_user,
                dispensing=self.dispensing,
            )

    def test_unauthorized_user_cannot_initiate_payment(self):
        with self.assertRaises(PermissionDenied):
            simulate_payment(
                actor=self.unauthorized_user,
                invoice=self.invoice,
                amount=Decimal("10.00"),
                method=Payment.Method.MPESA,
                outcome="SUCCESSFUL",
                phone_number="0712345678",
            )

    def test_zero_or_negative_payment_is_rejected(self):
        for amount in [
            Decimal("0.00"),
            Decimal("-5.00"),
        ]:
            with self.subTest(amount=amount):
                with self.assertRaises(ValidationError):
                    simulate_payment(
                        actor=self.cashier,
                        invoice=self.invoice,
                        amount=amount,
                        method=Payment.Method.MPESA,
                        outcome="SUCCESSFUL",
                        phone_number="0712345678",
                    )
