
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import PatientUpdateForm
from .services import update_patient
from django.shortcuts import render, redirect, get_object_or_404

from .forms import (
    PatientRegistrationForm,
    PatientIdentifierFormSet,
    PatientGuardianFormSet,
)
from .models import Patient
from .services import change_patient_status
from .services import register_patient


def check_patient_registration_permission(user):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied("You must have an active account.")

    if not user.has_perm("patients.can_register_patient"):
        raise PermissionDenied(
            "You do not have permission to register patients."
        )


def check_patient_view_permission(user):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied("You must have an active account.")

    if not user.has_perm("patients.can_view_patient_records"):
        raise PermissionDenied(
            "You do not have permission to view patient records."
        )


@login_required
def register_patient_view(request):
    check_patient_registration_permission(request.user)

    if request.method == "POST":
        patient_form = PatientRegistrationForm(request.POST)

        identifier_formset = PatientIdentifierFormSet(
            request.POST,
            prefix="identifiers",
        )

        guardian_formset = PatientGuardianFormSet(
            request.POST,
            prefix="guardians",
        )

        # Validate each form independently.
        patient_valid = patient_form.is_valid()
        identifiers_valid = identifier_formset.is_valid()
        guardians_valid = guardian_formset.is_valid()

        if patient_valid and identifiers_valid and guardians_valid:

            patient_data = patient_form.cleaned_data

            identifiers = [
                form.cleaned_data
                for form in identifier_formset
                if form.cleaned_data
            ]

            guardians = [
                form.cleaned_data
                for form in guardian_formset
                if form.cleaned_data
            ]

            try:
                patient = register_patient(
                    actor=request.user,
                    patient_data=patient_data,
                    identifiers=identifiers,
                    guardians=guardians,
                )

                messages.success(
                    request,
                    f"Patient {patient.full_name} registered successfully.",
                )

                return redirect(
                    "patients:registration_success",
                    patient_id=patient.pk,
                )

            except ValidationError as exc:
                patient_form.add_error(None, exc)

    else:
        patient_form = PatientRegistrationForm()

        identifier_formset = PatientIdentifierFormSet(
            prefix="identifiers"
        )

        guardian_formset = PatientGuardianFormSet(
            prefix="guardians"
        )

    return render(
        request,
        "patients/register.html",
        {
            "patient_form": patient_form,
            "identifier_formset": identifier_formset,
            "guardian_formset": guardian_formset,
        },
    )


@login_required
def registration_success(request, patient_id):
    check_patient_view_permission(request.user)

    patient = get_object_or_404(
        Patient,
        pk=patient_id,
    )

    return render(
        request,
        "patients/registration_success.html",
        {"patient": patient},
    )


@login_required
def patient_directory(request):
    check_patient_view_permission(request.user)

    patients = Patient.objects.select_related(
        "registered_by"
    ).all()

    # Search
    query = request.GET.get("q", "").strip()

    if query:
        patients = patients.filter(
            Q(hospital_number__icontains=query)
            | Q(first_name__icontains=query)
            | Q(middle_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(phone_number__icontains=query)
            | Q(email__icontains=query)
        )

    # Filter by sex
    sex = request.GET.get("sex", "").strip()

    valid_sexes = [
        choice[0] for choice in Patient.Sex.choices
    ]

    if sex in valid_sexes:
        patients = patients.filter(sex=sex)
    else:
        sex = ""

    # Filter by registration status
    status = request.GET.get("status", "all")

    if status == "active":
        patients = patients.filter(is_active=True)

    elif status == "inactive":
        patients = patients.filter(is_active=False)

    else:
        status = "all"

    # Pagination
    paginator = Paginator(patients, 20)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "patients/directory.html",
        {
            "page_obj": page_obj,
            "query": query,
            "sex": sex,
            "status": status,
            "sex_choices": Patient.Sex.choices,
            "total_patients": paginator.count,
        },
    )


@login_required
def patient_profile(request, patient_id):
    check_patient_view_permission(request.user)

    patient = get_object_or_404(
        Patient.objects.select_related(
            "registered_by"
        ).prefetch_related(
            "identifiers",
            "guardians",
        ),
        pk=patient_id,
    )

    # Do not display full identification numbers
    # on the general patient profile.
    return render(
        request,
        "patients/profile.html",
        {"patient": patient},
    )


@login_required
def update_patient_view(request, patient_id):
    if not request.user.is_active:
        raise PermissionDenied("Your account is inactive.")

    if not request.user.has_perm(
        "patients.can_update_patient_records"
    ):
        raise PermissionDenied(
            "You do not have permission to update patient records."
        )

    patient = get_object_or_404(
        Patient,
        pk=patient_id,
    )

    if request.method == "POST":
        form = PatientUpdateForm(
            request.POST,
            instance=patient,
        )

        if form.is_valid():
            try:
                updated_patient = update_patient(
                    actor=request.user,
                    patient=patient,
                    patient_data=form.cleaned_data,
                )

                messages.success(
                    request,
                    "Patient information updated successfully.",
                )

                return redirect(
                    "patients:profile",
                    patient_id=updated_patient.pk,
                )

            except ValidationError as exc:
                form.add_error(None, exc)

    else:
        form = PatientUpdateForm(instance=patient)

    return render(
        request,
        "patients/update.html",
        {
            "form": form,
            "patient": patient,
        },
    )


@login_required
def change_patient_status_view(request, patient_id):

    if request.method != "POST":
        return redirect(
            "patients:profile",
            patient_id=patient_id,
        )

    if not request.user.is_active:
        raise PermissionDenied(
            "Your account is inactive."
        )

    if not request.user.has_perm(
        "patients.can_manage_patient_status"
    ):
        raise PermissionDenied(
            "You do not have permission to change patient status."
        )

    patient = get_object_or_404(
        Patient,
        pk=patient_id,
    )

    action = request.POST.get("action")

    if action == "deactivate":
        new_status = False

    elif action == "activate":
        new_status = True

    else:
        messages.error(
            request,
            "Invalid patient status action.",
        )

        return redirect(
            "patients:profile",
            patient_id=patient.pk,
        )

    try:
        patient = change_patient_status(
            actor=request.user,
            patient=patient,
            new_status=new_status,
        )

        if patient.is_active:
            messages.success(
                request,
                "Patient record activated successfully.",
            )
        else:
            messages.success(
                request,
                "Patient record deactivated successfully.",
            )

    except ValidationError as exc:
        messages.error(request, str(exc))

    return redirect(
        "patients:profile",
        patient_id=patient.pk,
    )


