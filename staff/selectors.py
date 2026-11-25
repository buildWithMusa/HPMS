
from django.contrib.auth.models import Group
from django.db.models import Prefetch, Q
from django.utils import timezone

from hospital.models import Department
from .models import StaffProfile, StaffAssignment


def get_staff_directory(
    search="",
    department_id="",
    employment_status="",
    role="",
):
    """
    Retrieve staff records for the HPMS staff directory.

    Supports:
    - Searching by employee name, email or staff number.
    - Filtering by department.
    - Filtering by employment status.
    - Filtering by system role.
    - Loading current primary assignments efficiently.
    """

    today = timezone.localdate()

    # Current primary assignments only.
    current_assignments = (
        StaffAssignment.objects
        .filter(
            is_active=True,
            is_primary=True,
        )
        .filter(
            Q(end_date__isnull=True) |
            Q(end_date__gte=today)
        )
        .select_related(
            "department",
            "service_area",
        )
        .order_by("-start_date", "-created_at")
    )

    # Base staff queryset.
    queryset = (
        StaffProfile.objects
        .select_related("user")
        .prefetch_related(
    "user__groups",
    Prefetch(
        "assignments",
        queryset=current_assignments,
        to_attr="current_assignments",
    )
)
    )

    # Search employee information.
    if search:
        queryset = queryset.filter(
            Q(first_name__icontains=search) |
            Q(middle_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(staff_number__icontains=search) |
            Q(user__email__icontains=search)
        )

    # Filter by department.
    if department_id:
        queryset = queryset.filter(
            assignments__department_id=department_id,
            assignments__is_active=True,
            assignments__is_primary=True,
        ).filter(
            Q(assignments__end_date__isnull=True) |
            Q(assignments__end_date__gte=today)
        )

    # Filter by employment status.
    if employment_status:
        valid_statuses = dict(
            StaffProfile.EmploymentStatus.choices
        )

        if employment_status in valid_statuses:
            queryset = queryset.filter(
                employment_status=employment_status
            )

    # Filter by HPMS system role.
    if role:
        queryset = queryset.filter(
            user__groups__name=role
        )

    return queryset.distinct().order_by("staff_number")


def get_staff_directory_filters():
    """
    Return available departments, employment statuses
    and system roles for directory filters.
    """

    return {
        "departments": Department.objects.filter(
            is_active=True
        ).order_by("name"),

        "employment_statuses": (
            StaffProfile.EmploymentStatus.choices
        ),

        "roles": Group.objects.order_by("name"),
    }
