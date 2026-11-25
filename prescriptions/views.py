from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from accounts.authorization import require_hpms_permission

from .models import Prescription
from .forms import (
    PrescriptionForm,
    PaperPrescriptionForm,
    PrescriptionLineForm,
    RejectionForm,
)
from .services import (
    create_prescription,
    register_paper_prescription,
    add_prescription_line,
    submit_prescription,
    verify_prescription,
    reject_prescription,
    cancel_prescription,
)


def _check(user, permission):
    require_hpms_permission(user, permission)


@login_required
def dashboard(request):
    _check(request.user, "prescriptions.can_view_prescriptions")

    prescriptions = Prescription.objects.select_related(
        "patient", "recorded_by", "prescribed_by", "verified_by"
    )

    context = {
        "total": prescriptions.count(),
        "draft_count": prescriptions.filter(
            status=Prescription.Status.DRAFT
        ).count(),
        "pending_count": prescriptions.filter(
            status=Prescription.Status.SUBMITTED
        ).count(),
        "verified_count": prescriptions.filter(
            status=Prescription.Status.VERIFIED
        ).count(),
        "recent_prescriptions": prescriptions[:10],
    }
    return render(request, "prescriptions/dashboard.html", context)


@login_required
def prescription_list(request):
    _check(request.user, "prescriptions.can_view_prescriptions")

    status = request.GET.get("status", "").strip()
    query = request.GET.get("q", "").strip()

    prescriptions = Prescription.objects.select_related(
        "patient", "recorded_by", "prescribed_by"
    )

    if status in Prescription.Status.values:
        prescriptions = prescriptions.filter(status=status)

    if query:
        from django.db.models import Q
        prescriptions = prescriptions.filter(
            Q(prescription_number__icontains=query)
            | Q(patient__hospital_number__icontains=query)
            | Q(patient__first_name__icontains=query)
            | Q(patient__last_name__icontains=query)
        )

    return render(
        request,
        "prescriptions/list.html",
        {
            "prescriptions": prescriptions[:200],
            "selected_status": status,
            "query": query,
            "statuses": Prescription.Status.choices,
        },
    )


@login_required
def prescription_create(request):
    _check(request.user, "prescriptions.can_create_prescription")

    form = PrescriptionForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            prescription = create_prescription(
                actor=request.user,
                patient=form.cleaned_data["patient"],
                diagnosis=form.cleaned_data["diagnosis"],
                clinical_notes=form.cleaned_data["clinical_notes"],
            )
            messages.success(request, "Prescription created. Add its medicines.")
            return redirect(
                "prescriptions:detail",
                pk=prescription.pk
            )
        except (ValidationError, PermissionDenied) as exc:
            form.add_error(None, str(exc))

    return render(
        request,
        "prescriptions/form.html",
        {"form": form, "page_title": "Create Electronic Prescription"},
    )


@login_required
def paper_prescription_create(request):
    _check(
        request.user,
        "prescriptions.can_register_paper_prescription"
    )

    form = PaperPrescriptionForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            data = form.cleaned_data
            prescription = register_paper_prescription(
                actor=request.user,
                patient=data["patient"],
                prescriber_name=data["prescriber_name"],
                prescriber_registration=data["prescriber_registration"],
                external_reference=data["external_reference"],
                diagnosis=data["diagnosis"],
                clinical_notes=data["clinical_notes"],
            )
            messages.success(
                request,
                "Paper prescription registered. Add its medicines."
            )
            return redirect(
                "prescriptions:detail",
                pk=prescription.pk
            )
        except (ValidationError, PermissionDenied) as exc:
            form.add_error(None, str(exc))

    return render(
        request,
        "prescriptions/form.html",
        {"form": form, "page_title": "Register Paper Prescription"},
    )


@login_required
def prescription_detail(request, pk):
    _check(request.user, "prescriptions.can_view_prescriptions")

    prescription = get_object_or_404(
        Prescription.objects.select_related(
            "patient", "recorded_by", "prescribed_by", "verified_by"
        ).prefetch_related("lines__medicine"),
        pk=pk,
    )

    line_form = PrescriptionLineForm()

    if request.method == "POST":
        line_permission = (
            "prescriptions.can_register_paper_prescription"
            if prescription.source == Prescription.Source.PAPER
            else "prescriptions.can_create_prescription"
        )
        _check(request.user, line_permission)
        line_form = PrescriptionLineForm(request.POST)

        if line_form.is_valid():
            data = line_form.cleaned_data
            try:
                add_prescription_line(
                    actor=request.user,
                    prescription=prescription,
                    medicine=data["medicine"],
                    dose=data["dose"],
                    route=data["route"],
                    frequency=data["frequency"],
                    duration_days=data["duration_days"],
                    quantity=data["quantity"],
                    instructions=data["instructions"],
                )
                messages.success(request, "Medicine added to prescription.")
                return redirect(
                    "prescriptions:detail",
                    pk=prescription.pk
                )
            except (ValidationError, PermissionDenied) as exc:
                line_form.add_error(None, str(exc))

    return render(
        request,
        "prescriptions/detail.html",
        {
            "prescription": prescription,
            "line_form": line_form,
            "can_add_line": (
                request.user.has_perm("prescriptions.can_register_paper_prescription")
                if prescription.source == Prescription.Source.PAPER
                else request.user.has_perm("prescriptions.can_create_prescription")
            ),
            "can_submit": (
                request.user.has_perm("prescriptions.can_register_paper_prescription")
                if prescription.source == Prescription.Source.PAPER
                else request.user.has_perm("prescriptions.can_create_prescription")
            ),
            "can_verify": request.user.has_perm(
                "prescriptions.can_verify_prescription"
            ),
            "can_cancel": request.user.has_perm(
                "prescriptions.can_cancel_prescription"
            ),
        },
    )


@login_required
@require_POST
def prescription_submit(request, pk):
    _check(request.user, "prescriptions.can_create_prescription")
    prescription = get_object_or_404(Prescription, pk=pk)

    try:
        submit_prescription(request.user, prescription)
        messages.success(request, "Prescription submitted for pharmacist verification.")
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, str(exc))

    return redirect("prescriptions:detail", pk=pk)


@login_required
@require_POST
def prescription_verify(request, pk):
    _check(request.user, "prescriptions.can_verify_prescription")
    prescription = get_object_or_404(Prescription, pk=pk)

    try:
        verify_prescription(request.user, prescription)
        messages.success(request, "Prescription verified successfully.")
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, str(exc))

    return redirect("prescriptions:detail", pk=pk)


@login_required
@require_POST
def prescription_reject(request, pk):
    _check(request.user, "prescriptions.can_verify_prescription")
    prescription = get_object_or_404(Prescription, pk=pk)
    form = RejectionForm(request.POST)

    if form.is_valid():
        try:
            reject_prescription(
                request.user,
                prescription,
                form.cleaned_data["reason"],
            )
            messages.success(request, "Prescription rejected.")
        except (ValidationError, PermissionDenied) as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "Enter a valid rejection reason.")

    return redirect("prescriptions:detail", pk=pk)


@login_required
@require_POST
def prescription_cancel(request, pk):
    _check(request.user, "prescriptions.can_cancel_prescription")
    prescription = get_object_or_404(Prescription, pk=pk)

    try:
        cancel_prescription(request.user, prescription)
        messages.success(request, "Prescription cancelled.")
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, str(exc))

    return redirect("prescriptions:detail", pk=pk)
