
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser ,Permission
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser, Permission
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404, HttpResponse
from django.test import RequestFactory
from staff.access import (
    department_access_required,
    service_area_access_required,
)
from django.core.exceptions import (
    ImproperlyConfigured,
    PermissionDenied,
)

from hospital.models import Department, ServiceArea
from staff.models import StaffProfile, StaffAssignment
from staff.access import (
    has_cross_department_access,
    get_active_staff_assignments,
    has_department_access,
    has_service_area_access,
    get_accessible_department_ids,
    get_accessible_service_area_ids,
    require_department_access,
    require_service_area_access,
)

User = get_user_model()
@department_access_required(department_kwarg="department_id")
def protected_department_view(request, department_id):
    return HttpResponse("Department access granted")


@service_area_access_required(service_area_kwarg="service_area_id")
def protected_service_area_view(request, service_area_id):
    return HttpResponse("Service area access granted")


class StaffAccessTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.pharmacy = Department.objects.create(
            code="PHARM",
            name="Pharmacy",
        )

        cls.medical = Department.objects.create(
            code="MED",
            name="Medical Services",
        )

        cls.opd = ServiceArea.objects.create(
            department=cls.medical,
            code="OPD",
            name="Outpatient Department",
        )

        cls.ipd = ServiceArea.objects.create(
            department=cls.medical,
            code="IPD",
            name="Inpatient Department",
        )

        cls.doctor_user = User.objects.create_user(
            email="doctor-test@hpms.local",
            password="TestPassword123!",
        )

        cls.pharmacist_user = User.objects.create_user(
            email="pharmacist-test@hpms.local",
            password="TestPassword123!",
        )

        cls.manager_user = User.objects.create_user(
            email="manager-test@hpms.local",
            password="TestPassword123!",
        )

        cls.doctor = StaffProfile.objects.create(
            user=cls.doctor_user,
            staff_number="TEST-DOCTOR-001",
            first_name="Test",
            last_name="Doctor",
            job_title="Medical Doctor",
        )

        cls.pharmacist = StaffProfile.objects.create(
            user=cls.pharmacist_user,
            staff_number="TEST-PHARM-001",
            first_name="Test",
            last_name="Pharmacist",
            job_title="Pharmacist",
        )

        cls.manager = StaffProfile.objects.create(
            user=cls.manager_user,
            staff_number="TEST-MANAGER-001",
            first_name="Test",
            last_name="Manager",
            job_title="Hospital Manager",
        )

        today = timezone.localdate()

        StaffAssignment.objects.create(
            staff=cls.doctor,
            department=cls.medical,
            service_area=cls.ipd,
            is_primary=True,
            start_date=today,
        )

        StaffAssignment.objects.create(
            staff=cls.pharmacist,
            department=cls.pharmacy,
            is_primary=True,
            start_date=today,
        )

        cls.manager_assignment = StaffAssignment.objects.create(
            staff=cls.manager,
            department=cls.medical,
            is_primary=True,
            start_date=today,
        )

        permission = Permission.objects.get(
            content_type__app_label="accounts",
            codename="can_access_all_departments",
        )

        cls.manager_user.user_permissions.add(permission)

    # --------------------------------------------------
    # AUTHENTICATION AND ACCOUNT STATUS
    # --------------------------------------------------

    def test_anonymous_user_has_no_department_access(self):
        anonymous_user = AnonymousUser()
        self.assertFalse(
        has_department_access(
            anonymous_user,
            self.pharmacy,
        )
    )



    def test_inactive_user_has_no_department_access(self):
        self.doctor_user.is_active = False
        self.doctor_user.save()

        self.assertFalse(
            has_department_access(
                self.doctor_user,
                self.medical,
            )
        )

    # --------------------------------------------------
    # DEPARTMENT ACCESS
    # --------------------------------------------------

    def test_staff_can_access_assigned_department(self):
        self.assertTrue(
            has_department_access(
                self.doctor_user,
                self.medical,
            )
        )

    def test_staff_cannot_access_unassigned_department(self):
        self.assertFalse(
            has_department_access(
                self.doctor_user,
                self.pharmacy,
            )
        )

    def test_manager_with_cross_department_permission_can_access_all(self):
        self.assertTrue(
            has_cross_department_access(self.manager_user)
        )

        self.assertTrue(
            has_department_access(
                self.manager_user,
                self.pharmacy,
            )
        )

    def test_department_access_is_denied_without_assignment(self):
        with self.assertRaises(PermissionDenied):
            require_department_access(
                self.doctor_user,
                self.pharmacy,
            )

    # --------------------------------------------------
    # SERVICE-AREA ACCESS
    # --------------------------------------------------

    def test_staff_can_access_assigned_service_area(self):
        self.assertTrue(
            has_service_area_access(
                self.doctor_user,
                self.ipd,
            )
        )

    def test_staff_cannot_access_unassigned_service_area(self):
        self.assertFalse(
            has_service_area_access(
                self.doctor_user,
                self.opd,
            )
        )

    def test_service_area_access_is_denied_without_assignment(self):
        with self.assertRaises(PermissionDenied):
            require_service_area_access(
                self.doctor_user,
                self.opd,
            )

    def test_department_wide_assignment_allows_all_areas(self):
        StaffAssignment.objects.create(
            staff=self.pharmacist,
            department=self.medical,
            service_area=None,
            is_active=True,
            start_date=timezone.localdate(),
        )

        self.assertTrue(
            has_service_area_access(
                self.pharmacist_user,
                self.opd,
            )
        )

        self.assertTrue(
            has_service_area_access(
                self.pharmacist_user,
                self.ipd,
            )
        )

    # --------------------------------------------------
    # ACTIVE ASSIGNMENT RULES
    # --------------------------------------------------

    def test_inactive_assignment_grants_no_access(self):
        self.manager_assignment.is_active = False
        self.manager_assignment.save()

        self.manager_user.user_permissions.clear()

        self.assertFalse(
            has_department_access(
                self.manager_user,
                self.medical,
            )
        )

    def test_future_assignment_grants_no_access(self):
        future_user = User.objects.create_user(
            email="future-test@hpms.local",
            password="TestPassword123!",
        )

        future_staff = StaffProfile.objects.create(
            user=future_user,
            staff_number="TEST-FUTURE-001",
            first_name="Future",
            last_name="Employee",
            job_title="Doctor",
        )

        StaffAssignment.objects.create(
            staff=future_staff,
            department=self.medical,
            start_date=timezone.localdate() + timedelta(days=5),
        )

        self.assertFalse(
            has_department_access(
                future_user,
                self.medical,
            )
        )

    def test_expired_assignment_grants_no_access(self):
        expired_user = User.objects.create_user(
            email="expired-test@hpms.local",
            password="TestPassword123!",
        )

        expired_staff = StaffProfile.objects.create(
            user=expired_user,
            staff_number="TEST-EXPIRED-001",
            first_name="Expired",
            last_name="Employee",
            job_title="Doctor",
        )

        today = timezone.localdate()

        StaffAssignment.objects.create(
            staff=expired_staff,
            department=self.medical,
            start_date=today - timedelta(days=30),
            end_date=today - timedelta(days=1),
            is_active=True,
        )

        self.assertFalse(
            has_department_access(
                expired_user,
                self.medical,
            )
        )

    def test_non_active_employment_status_grants_no_access(self):
        self.doctor.employment_status = (
            StaffProfile.EmploymentStatus.SUSPENDED
        )
        self.doctor.save()

        self.assertFalse(
            has_department_access(
                self.doctor_user,
                self.medical,
            )
        )

    # --------------------------------------------------
    # ACCESSIBLE ID QUERYSETS
    # --------------------------------------------------

    def test_accessible_department_ids_only_include_assigned_departments(self):
        ids = list(
            get_accessible_department_ids(self.doctor_user)
        )

        self.assertEqual(ids, [self.medical.pk])

    def test_accessible_service_area_ids_only_include_assigned_areas(self):
        ids = list(
            get_accessible_service_area_ids(self.doctor_user)
        )

        self.assertEqual(ids, [self.ipd.pk])

    def test_manager_can_access_all_department_ids(self):
        ids = set(
            get_accessible_department_ids(self.manager_user)
        )

        self.assertEqual(
            ids,
            {self.pharmacy.pk, self.medical.pk},
        )

    def test_manager_can_access_all_service_area_ids(self):
        ids = set(
            get_accessible_service_area_ids(self.manager_user)
        )

        self.assertEqual(
            ids,
            {self.opd.pk, self.ipd.pk},
        )

class AccessDecoratorTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(
            code="TEST-DEP",
            name="Test Department",
        )

        cls.other_department = Department.objects.create(
            code="TEST-OTHER",
            name="Other Department",
        )

        cls.service_area = ServiceArea.objects.create(
            department=cls.department,
            code="TEST-AREA",
            name="Test Service Area",
        )

        cls.user = User.objects.create_user(
            email="decorator-test@hpms.local",
            password="TestPassword123!",
        )

        cls.other_user = User.objects.create_user(
            email="other-test@hpms.local",
            password="TestPassword123!",
        )

        cls.staff = StaffProfile.objects.create(
            user=cls.user,
            staff_number="DEC-001",
            first_name="Decorator",
            last_name="Tester",
            job_title="Test Officer",
        )

        StaffAssignment.objects.create(
            staff=cls.staff,
            department=cls.department,
            service_area=cls.service_area,
            start_date=timezone.localdate(),
            is_active=True,
        )

    def setUp(self):
        self.factory = RequestFactory()

    # ------------------------------------------
    # DEPARTMENT DECORATOR
    # ------------------------------------------

    def test_assigned_user_can_access_department_view(self):
        request = self.factory.get("/test/department/")
        request.user = self.user

        response = protected_department_view(
            request,
            department_id=self.department.pk,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.content,
            b"Department access granted",
        )

    def test_unassigned_user_is_denied_department_view(self):
        request = self.factory.get("/test/department/")
        request.user = self.other_user

        with self.assertRaises(PermissionDenied):
            protected_department_view(
                request,
                department_id=self.department.pk,
            )

    def test_anonymous_user_is_denied_department_view(self):
        request = self.factory.get("/test/department/")
        request.user = AnonymousUser()

        with self.assertRaises(PermissionDenied):
            protected_department_view(
                request,
                department_id=self.department.pk,
            )

    def test_missing_department_url_argument_raises_configuration_error(self):
        request = self.factory.get("/test/department/")
        request.user = self.user

        with self.assertRaises(ImproperlyConfigured):
            protected_department_view(request)

    def test_nonexistent_department_returns_404(self):
        request = self.factory.get("/test/department/")
        request.user = self.user

        with self.assertRaises(Http404):
            protected_department_view(
                request,
                department_id=999999,
            )

    # ------------------------------------------
    # SERVICE-AREA DECORATOR
    # ------------------------------------------

    def test_assigned_user_can_access_service_area_view(self):
        request = self.factory.get("/test/service-area/")
        request.user = self.user

        response = protected_service_area_view(
            request,
            service_area_id=self.service_area.pk,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.content,
            b"Service area access granted",
        )

    def test_unassigned_user_is_denied_service_area_view(self):
        request = self.factory.get("/test/service-area/")
        request.user = self.other_user

        with self.assertRaises(PermissionDenied):
            protected_service_area_view(
                request,
                service_area_id=self.service_area.pk,
            )

    def test_anonymous_user_is_denied_service_area_view(self):
        request = self.factory.get("/test/service-area/")
        request.user = AnonymousUser()

        with self.assertRaises(PermissionDenied):
            protected_service_area_view(
                request,
                service_area_id=self.service_area.pk,
            )

    def test_missing_service_area_argument_raises_configuration_error(self):
        request = self.factory.get("/test/service-area/")
        request.user = self.user

        with self.assertRaises(ImproperlyConfigured):
            protected_service_area_view(request)

    def test_nonexistent_service_area_returns_404(self):
        request = self.factory.get("/test/service-area/")
        request.user = self.user

        with self.assertRaises(Http404):
            protected_service_area_view(
                request,
                service_area_id=999999,
            )
