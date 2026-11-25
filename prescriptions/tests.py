from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase

from patients.models import Patient
from medicines.models import Medicine, MedicineCategory
from .models import Prescription
from .services import (
    create_prescription,
    register_paper_prescription,
    add_prescription_line,
    submit_prescription,
    verify_prescription,
    reject_prescription,
    cancel_prescription,
)


User = get_user_model()


class PrescriptionWorkflowTests(TestCase):

    def setUp(self):
        self.doctor = User.objects.create_user(
            email="doctor@example.com",
            password="TestPassword123!"
        )
        self.pharmacist = User.objects.create_user(
            email="pharmacist@example.com",
            password="TestPassword123!"
        )

        from django.contrib.auth.models import Permission

        doctor_permissions = Permission.objects.filter(
            content_type__app_label="prescriptions",
            codename__in=[
                "can_create_prescription",
                "can_view_prescriptions",
                "can_cancel_prescription",
            ],
        )
        pharmacist_permissions = Permission.objects.filter(
            content_type__app_label="prescriptions",
            codename__in=[
                "can_view_prescriptions",
                "can_verify_prescription",
                "can_register_paper_prescription",
                "can_cancel_prescription",
            ],
        )

        self.doctor.user_permissions.add(*doctor_permissions)
        self.pharmacist.user_permissions.add(*pharmacist_permissions)

        self.patient = Patient.objects.create(
            first_name="Jane",
            last_name="Patient",
            date_of_birth=date.today() - timedelta(days=30 * 365),
            registered_by=self.doctor,
        )

        self.category = MedicineCategory.objects.create(
            name="Test Medicines"
        )
        self.medicine = Medicine.objects.create(
            category=self.category,
            generic_name="Paracetamol",
            strength="500 mg",
            dosage_form=Medicine.DosageForm.TABLET,
            unit_of_measure=Medicine.UnitOfMeasure.TABLET,
        )

    def add_line(self, prescription):
        return add_prescription_line(
            actor=prescription.recorded_by,
            prescription=prescription,
            medicine=self.medicine,
            dose="1 tablet",
            route="ORAL",
            frequency="Twice daily",
            duration_days=5,
            quantity=10,
        )

    def test_doctor_can_create_electronic_prescription(self):
        prescription = create_prescription(
            self.doctor,
            self.patient,
            diagnosis="Test diagnosis",
        )
        self.assertEqual(prescription.source, Prescription.Source.ELECTRONIC)
        self.assertTrue(prescription.prescription_number.startswith("RX-"))

    def test_doctor_cannot_prescribe_for_inactive_patient(self):
        self.patient.is_active = False
        self.patient.save()

        with self.assertRaises(ValidationError):
            create_prescription(self.doctor, self.patient)

    def test_medicine_can_be_added_to_draft(self):
        prescription = create_prescription(self.doctor, self.patient)
        line = self.add_line(prescription)
        self.assertEqual(line.quantity, 10)

    def test_inactive_medicine_cannot_be_added(self):
        prescription = create_prescription(self.doctor, self.patient)
        self.medicine.is_active = False
        self.medicine.save()

        with self.assertRaises(ValidationError):
            self.add_line(prescription)

    def test_cannot_submit_without_medicine(self):
        prescription = create_prescription(self.doctor, self.patient)

        with self.assertRaises(ValidationError):
            submit_prescription(self.doctor, prescription)

    def test_pharmacist_can_verify_submitted_prescription(self):
        prescription = create_prescription(self.doctor, self.patient)
        self.add_line(prescription)
        submit_prescription(self.doctor, prescription)

        verified = verify_prescription(self.pharmacist, prescription)

        self.assertEqual(verified.status, Prescription.Status.VERIFIED)
        self.assertEqual(verified.verified_by, self.pharmacist)

    def test_prescriber_cannot_verify_own_prescription(self):
        prescription = create_prescription(self.doctor, self.patient)
        self.add_line(prescription)
        submit_prescription(self.doctor, prescription)

        with self.assertRaises(PermissionDenied):
            verify_prescription(self.doctor, prescription)

    def test_pharmacist_can_register_paper_prescription(self):
        prescription = register_paper_prescription(
            actor=self.pharmacist,
            patient=self.patient,
            prescriber_name="External Doctor",
            prescriber_registration="REG-123",
        )

        self.assertEqual(prescription.source, Prescription.Source.PAPER)
        self.assertEqual(prescription.paper_prescriber_name, "External Doctor")

    def test_pharmacist_can_reject_with_reason(self):
        prescription = create_prescription(self.doctor, self.patient)
        self.add_line(prescription)
        submit_prescription(self.doctor, prescription)

        rejected = reject_prescription(
            self.pharmacist,
            prescription,
            "The prescribed dose needs clarification.",
        )

        self.assertEqual(rejected.status, Prescription.Status.REJECTED)
        self.assertEqual(
            rejected.rejection_reason,
            "The prescribed dose needs clarification.",
        )

    def test_cannot_edit_after_submission(self):
        prescription = create_prescription(self.doctor, self.patient)
        self.add_line(prescription)
        submit_prescription(self.doctor, prescription)

        with self.assertRaises(ValidationError):
            self.add_line(prescription)

    def test_creator_can_cancel_draft(self):
        prescription = create_prescription(self.doctor, self.patient)
        cancelled = cancel_prescription(self.doctor, prescription)

        self.assertEqual(cancelled.status, Prescription.Status.CANCELLED)
