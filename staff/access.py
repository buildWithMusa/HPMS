
from functools import wraps

from django.core.exceptions import (
    ImproperlyConfigured,
    PermissionDenied,
)
from django.shortcuts import get_object_or_404

from hospital.models import Department, ServiceArea
from staff.models import StaffProfile, StaffAssignment
from django.db.models import Q


CROSS_DEPARTMENT_PERMISSION = (
    "accounts.can_access_all_departments"
)


def has_cross_department_access(user):
    """
    Checks whether a user has permission to access
    records across all hospital departments.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False

    return user.has_perm(CROSS_DEPARTMENT_PERMISSION)


def get_active_staff_assignments(user):
    """
    Returns the user's currently valid staff assignments.

    An assignment is valid when:
    - The user is authenticated and active.
    - The staff profile is active.
    - The assignment is active.
    - Its start date has arrived.
    - Its end date has not passed.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return StaffAssignment.objects.none()

    from django.db.models import Q
    from django.utils import timezone

    today = timezone.localdate()

    return StaffAssignment.objects.filter(
        staff__user=user,
        staff__employment_status=StaffProfile.EmploymentStatus.ACTIVE,
        is_active=True,
        start_date__lte=today,
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    ).select_related(
        "staff",
        "department",
        "service_area",
    )


def has_department_access(user, department):
    """
    Checks whether a user may access a department.

    Cross-department permission grants access to all departments.
    Otherwise, the user must have an active assignment there.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False

    if has_cross_department_access(user):
        return True

    department_id = getattr(department, "pk", department)

    if department_id is None:
        return False

    return get_active_staff_assignments(user).filter(
        department_id=department_id
    ).exists()


def has_service_area_access(user, service_area):
    """
    Checks whether a user may access a service area.

    A department-wide assignment (service_area=None) grants
    access to service areas within that assigned department.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False

    if has_cross_department_access(user):
        return True

    service_area_id = getattr(service_area, "pk", service_area)

    if service_area_id is None:
        return False

    target = ServiceArea.objects.filter(
        pk=service_area_id
    ).values(
        "department_id"
    ).first()

    if target is None:
        return False

    return get_active_staff_assignments(user).filter(
        department_id=target["department_id"]
    ).filter(
        Q(service_area_id=service_area_id)
        | Q(service_area__isnull=True)
    ).exists()


def require_department_access(user, department):
    """
    Raises PermissionDenied if the user cannot access a department.
    """
    if not has_department_access(user, department):
        raise PermissionDenied(
            "You are not assigned to this department."
        )

    return True


def require_service_area_access(user, service_area):
    """
    Raises PermissionDenied if the user cannot access a service area.
    """
    if not has_service_area_access(user, service_area):
        raise PermissionDenied(
            "You are not assigned to this service area."
        )

    return True


def department_access_required(*, department_kwarg="department"):
    """
    Protects a view using a Department object or department ID
    passed through the view's keyword arguments.
    """
    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            department_value = kwargs.get(department_kwarg)

            if department_value is None:
                raise ImproperlyConfigured(
                    f"Missing URL argument: {department_kwarg}"
                )

            if isinstance(department_value, Department):
                department = department_value
            else:
                department = get_object_or_404(
                    Department,
                    pk=department_value
                )

            require_department_access(
                request.user,
                department
            )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def service_area_access_required(*, service_area_kwarg="service_area"):
    """
    Protects a view using a ServiceArea object or service-area ID
    passed through the view's keyword arguments.
    """
    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            service_area_value = kwargs.get(service_area_kwarg)

            if service_area_value is None:
                raise ImproperlyConfigured(
                    f"Missing URL argument: {service_area_kwarg}"
                )

            if isinstance(service_area_value, ServiceArea):
                service_area = service_area_value
            else:
                service_area = get_object_or_404(
                    ServiceArea,
                    pk=service_area_value
                )

            require_service_area_access(
                request.user,
                service_area
            )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator

def get_accessible_department_ids(user):
    """
    Returns IDs of all departments accessible to the user.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return Department.objects.none().values_list("pk", flat=True)

    if has_cross_department_access(user):
        return Department.objects.values_list("pk", flat=True)

    return get_active_staff_assignments(user).values_list(
        "department_id",
        flat=True,
    ).distinct()


def get_accessible_service_area_ids(user):
    """
    Returns IDs of service areas accessible to the user.

    Department-wide assignments grant access to all service
    areas within that department.
    Specific assignments grant access only to those areas.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return ServiceArea.objects.none().values_list("pk", flat=True)

    if has_cross_department_access(user):
        return ServiceArea.objects.values_list("pk", flat=True)

    assignments = get_active_staff_assignments(user)

    department_wide_ids = assignments.filter(
        service_area__isnull=True
    ).values_list("department_id", flat=True)

    specific_area_ids = assignments.filter(
        service_area__isnull=False
    ).values_list("service_area_id", flat=True)

    return ServiceArea.objects.filter(
        Q(department_id__in=department_wide_ids)
        | Q(pk__in=specific_area_ids)
    ).values_list("pk", flat=True).distinct()

