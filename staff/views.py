
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
)
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.contrib.auth.forms import (
    AuthenticationForm,
    SetPasswordForm,
)
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render, redirect
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from .selectors import (
    get_staff_directory,
    get_staff_directory_filters,
)

from .forms import StaffRegistrationForm
from .services import (
    register_staff,
    send_staff_activation_email,
)


User = get_user_model()


# =========================================================
# 1. STAFF REGISTRATION
# =========================================================

@login_required
@permission_required(
    "staff.add_staffprofile",
    raise_exception=True
)
def register_staff_view(request):

    if request.method == "POST":
        form = StaffRegistrationForm(request.POST)

        if form.is_valid():

            try:
                staff = register_staff(form.cleaned_data)

                send_staff_activation_email(
                    request,
                    staff.user
                )

                messages.success(
                    request,
                    f"Staff account for {staff.first_name} "
                    f"{staff.last_name} was created successfully. "
                    "An activation email has been generated."
                )

                return redirect("staff:register")

            except Exception:
                messages.error(
                    request,
                    "Staff registration could not be completed. "
                    "Please check the server logs."
                )

    else:
        form = StaffRegistrationForm()

    return render(
        request,
        "staff/register.html",
        {"form": form}
    )


# =========================================================
# 2. STAFF ACCOUNT ACTIVATION
# =========================================================

def activate_staff_account(request, uidb64, token):

    user = None

    try:
        uid = force_str(
            urlsafe_base64_decode(uidb64)
        )

        user = User.objects.get(pk=uid)

    except (
        TypeError,
        ValueError,
        OverflowError,
        User.DoesNotExist
    ):
        user = None

    if (
        user is not None
        and default_token_generator.check_token(user, token)
        and not user.is_active
    ):

        form = SetPasswordForm(
            user,
            request.POST or None
        )

        if request.method == "POST":

            if form.is_valid():

                form.save()

                # Activate the account after password creation.
                user.is_active = True
                user.save(update_fields=["is_active"])

                messages.success(
                    request,
                    "Your HPMS account has been activated. "
                    "You can now log in."
                )

                return redirect(
                    "staff:activation_success"
                )

        return render(
            request,
            "staff/set_password.html",
            {"form": form}
        )

    return render(
        request,
        "staff/activation_invalid.html"
    )


# =========================================================
# 3. ACTIVATION SUCCESS
# =========================================================

def activation_success(request):

    return render(
        request,
        "staff/activation_success.html"
    )


# =========================================================
# 4. STAFF LOGIN
# =========================================================

def staff_login(request):

    if request.user.is_authenticated:
        return redirect("staff:dashboard")

    if request.method == "POST":

        form = AuthenticationForm(
            request,
            data=request.POST
        )

        if form.is_valid():

            user = form.get_user()

            login(request, user)

            messages.success(
                request,
                "Welcome to the Hospital Pharmacy Management System."
            )

            return redirect("staff:dashboard")

    else:
        form = AuthenticationForm()

    return render(
        request,
        "staff/login.html",
        {"form": form}
    )


# =========================================================
# 5. STAFF DASHBOARD
# =========================================================

@login_required
def staff_dashboard(request):

    staff = getattr(
        request.user,
        "staffprofile",
        None
    )

    context = {
        "staff": staff,
        "user": request.user,
    }

    return render(
        request,
        "staff/dashboard.html",
        context
    )


# =========================================================
# 6. STAFF LOGOUT
# =========================================================

@login_required
@require_POST
def staff_logout(request):

    logout(request)

    messages.success(
        request,
        "You have successfully logged out."
    )

    return redirect("staff:login")

# =========================================================
# 7. STAFF DIRECTORY
# =========================================================

@login_required
@permission_required(
    "staff.view_staffprofile",
    raise_exception=True
)
def staff_directory(request):
    """
    Display the hospital staff directory.

    Supports searching, filtering and pagination.
    """

    # 1. Read filter values from the URL.
    search = request.GET.get("search", "").strip()

    department_id = request.GET.get(
        "department", ""
    ).strip()

    employment_status = request.GET.get(
        "status", ""
    ).strip()

    role = request.GET.get(
        "role", ""
    ).strip()

    # Validate department ID before using it.
    if not department_id.isdigit():
        department_id = ""

    # 2. Retrieve matching staff records.
    staff_queryset = get_staff_directory(
        search=search,
        department_id=department_id,
        employment_status=employment_status,
        role=role,
    )

    # 3. Paginate results.
    paginator = Paginator(
        staff_queryset,
        20
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    # 4. Retrieve available filter options.
    filter_options = get_staff_directory_filters()

    # 5. Prepare page context.
    context = {
        "page_obj": page_obj,
        "staff_members": page_obj.object_list,

        "total_staff": paginator.count,

        "search": search,
        "selected_department": department_id,
        "selected_status": employment_status,
        "selected_role": role,

        **filter_options,
    }

    return render(
        request,
        "staff/directory.html",
        context
    )

