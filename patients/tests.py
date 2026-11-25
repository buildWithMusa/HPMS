
from datetime import date, timedelta
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from .services import register_patient

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Patient, PatientIdentifier, PatientGuardian


User = get_user_model()


class PatientModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="patienttester@example.com",
            password="TestPassword123!"
        )

    def create_patient(self, **kwargs):
        defaults = {
            "first_name": "John",
            "last_name": "Doe",
            "registered_by": self.user,
        }
        defaults.update(kwargs)
        return Patient.objects.create(**defaults)

    def test_patient_hospital_number_is_generated(self):
        patient = self.create_patient()

        self.assertTrue(patient.hospital_number.startswith("HPMS-"))
        self.assertEqual(len(patient.hospital_number), 18)

    def test_hospital_numbers_are_unique(self):
        first = self.create_patient()
        second = self.create_patient()

        self.assertNotEqual(
            first.hospital_number,
            second.hospital_number
        )

    def test_patient_can_be_registered_without_identifier(self):
        patient = self.create_patient()

        self.assertEqual(patient.identifiers.count(), 0)

    def test_patient_can_be_registered_without_guardian(self):
        patient = self.create_patient()

        self.assertEqual(patient.guardians.count(), 0)

    def test_patient_can_have_multiple_identifiers(self):
        patient = self.create_patient()

        PatientIdentifier.objects.create(
            patient=patient,
            identifier_type="NATIONAL_ID",
            identifier_value="12345678"
        )

        PatientIdentifier.objects.create(
            patient=patient,
            identifier_type="PASSPORT",
            identifier_value="AB123456"
        )

        self.assertEqual(patient.identifiers.count(), 2)

    def test_duplicate_identifier_is_rejected(self):
        first = self.create_patient()
        second = self.create_patient()

        PatientIdentifier.objects.create(
            patient=first,
            identifier_type="NATIONAL_ID",
            identifier_value="12345678"
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PatientIdentifier.objects.create(
                    patient=second,
                    identifier_type="NATIONAL_ID",
                    identifier_value="12345678"
                )

    def test_identifier_value_is_trimmed(self):
        patient = self.create_patient()

        identifier = PatientIdentifier.objects.create(
            patient=patient,
            identifier_type="NATIONAL_ID",
            identifier_value="  12345678  "
        )

        self.assertEqual(identifier.identifier_value, "12345678")

    def test_patient_can_have_a_guardian(self):
        patient = self.create_patient()

        guardian = PatientGuardian.objects.create(
            patient=patient,
            full_name="Jane Doe",
            relationship="MOTHER",
            phone_number="0712345678",
            is_primary=True
        )

        self.assertEqual(patient.guardians.count(), 1)
        self.assertTrue(guardian.is_primary)

    def test_only_one_active_primary_guardian_is_allowed(self):
        patient = self.create_patient()

        PatientGuardian.objects.create(
            patient=patient,
            full_name="Jane Doe",
            relationship="MOTHER",
            phone_number="0712345678",
            is_primary=True
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PatientGuardian.objects.create(
                    patient=patient,
                    full_name="Peter Doe",
                    relationship="FATHER",
                    phone_number="0798765432",
                    is_primary=True
                )

    def test_future_date_of_birth_is_rejected(self):
        patient = self.create_patient(
            date_of_birth=date.today() + timedelta(days=1)
        )

        with self.assertRaises(ValidationError):
            patient.full_clean()

    def test_full_name_property(self):
        patient = self.create_patient(
            first_name="John",
            middle_name="Peter",
            last_name="Doe"
        )

        self.assertEqual(patient.full_name, "John Peter Doe")

class PatientRegistrationServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="registration@example.com",
            password="TestPassword123!"
        )

        permission = Permission.objects.get(
            content_type__app_label="patients",
            codename="can_register_patient"
        )

        self.user.user_permissions.add(permission)

        self.patient_data = {
            "first_name": "Mary",
            "last_name": "Wanjiku",
            "sex": "FEMALE",
            "phone_number": "0712345678",
        }

    def test_successful_patient_registration(self):

        patient = register_patient(
            actor=self.user,
            patient_data=self.patient_data
        )

        self.assertIsNotNone(patient.pk)
        self.assertTrue(patient.hospital_number.startswith("HPMS-"))
        self.assertEqual(
            patient.registered_by,
            self.user
        )

    def test_registration_with_identifier(self):

        patient = register_patient(
            actor=self.user,
            patient_data=self.patient_data,
            identifiers=[
                {
                    "identifier_type": "NATIONAL_ID",
                    "identifier_value": "12345678",
                    "is_primary": True,
                }
            ]
        )

        self.assertEqual(patient.identifiers.count(), 1)

    def test_registration_with_guardian(self):

        patient = register_patient(
            actor=self.user,
            patient_data=self.patient_data,
            guardians=[
                {
                    "full_name": "Jane Wanjiku",
                    "relationship": "MOTHER",
                    "phone_number": "0798765432",
                    "is_primary": True,
                }
            ]
        )

        self.assertEqual(patient.guardians.count(), 1)

    def test_patient_and_guardian_register_together(self):

        patient = register_patient(
            actor=self.user,
            patient_data=self.patient_data,
            guardians=[
                {
                    "full_name": "Jane Wanjiku",
                    "relationship": "MOTHER",
                    "phone_number": "0798765432",
                    "is_primary": True,
                }
            ],
            identifiers=[
                {
                    "identifier_type": "NATIONAL_ID",
                    "identifier_value": "12345678",
                    "is_primary": True,
                }
            ]
        )

        self.assertEqual(patient.identifiers.count(), 1)
        self.assertEqual(patient.guardians.count(), 1)

    def test_unauthorized_user_cannot_register(self):

        unauthorized_user = User.objects.create_user(
            email="unauthorized@example.com",
            password="TestPassword123!"
        )

        with self.assertRaises(PermissionDenied):
            register_patient(
                actor=unauthorized_user,
                patient_data=self.patient_data
            )

    def test_invalid_guardian_rolls_back_patient_creation(self):

        initial_count = Patient.objects.count()

        with self.assertRaises(ValidationError):
            register_patient(
                actor=self.user,
                patient_data=self.patient_data,
                guardians=[
                    {
                        "full_name": "Jane Wanjiku",
                        "relationship": "MOTHER",
                        "phone_number": "",
                        "is_primary": True,
                    }
                ]
            )

        self.assertEqual(
            Patient.objects.count(),
            initial_count
        )

    def test_duplicate_identifier_rolls_back_registration(self):

        PatientIdentifier.objects.create(
            patient=Patient.objects.create(
                first_name="Existing",
                last_name="Patient"
            ),
            identifier_type="NATIONAL_ID",
            identifier_value="12345678"
        )

        initial_count = Patient.objects.count()

        with self.assertRaises(ValidationError):
            register_patient(
                actor=self.user,
                patient_data=self.patient_data,
                identifiers=[
                    {
                        "identifier_type": "NATIONAL_ID",
                        "identifier_value": "12345678",
                    }
                ]
            )

        self.assertEqual(
            Patient.objects.count(),
            initial_count
        )

    def test_multiple_primary_identifiers_are_rejected(self):

        with self.assertRaises(ValidationError):
            register_patient(
                actor=self.user,
                patient_data=self.patient_data,
                identifiers=[
                    {
                        "identifier_type": "NATIONAL_ID",
                        "identifier_value": "12345678",
                        "is_primary": True,
                    },
                    {
                        "identifier_type": "PASSPORT",
                        "identifier_value": "AB123456",
                        "is_primary": True,
                    }
                ]
            )

        self.assertEqual(
            Patient.objects.count(),
            0
        )

