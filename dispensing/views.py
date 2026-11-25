from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404

from accounts.authorization import require_hpms_permission
from prescriptions.models import Prescription
from .models import Dispensing
from .forms import DispensingForm
from .services import (
    dispense_prescription_line,
    get_remaining_quantity,
)


def _check(user, permission):
    require_hpms_permission(user, permission)


@login_required
def dashboard(request):
    _check(request.user, "dispensing.can_view_dispensing")

    pending = Prescription.objects.filter(
        status__in=[
            Prescription.Status.VERIFIED,
            Prescription.Status.PARTIALLY_DISPENSED,
        ]
    ).select_related("patient", "prescribed_by")

    recent = Dispensing.objects.select_related(
        "prescription", "prescription__patient",
        "prescription_line__medicine", "dispensed_by"
    )[:20]

    return render(request, "dispensing/dashboard.html", {
        "pending": pending,
        "recent": recent,
        "pending_count": pending.count(),
        "dispensing_count": Dispensing.objects.count(),
    })


@login_required
def dispensing_history(request):
    _check(request.user, "dispensing.can_view_dispensing")

    records = Dispensing.objects.select_related(
        "prescription", "prescription__patient",
        "prescription_line__medicine", "dispensed_by"
    ).prefetch_related("batch_allocations__batch")

    return render(request, "dispensing/history.html", {
        "records": records[:200],
    })


@login_required
def dispense(request, prescription_id):
    _check(request.user, "dispensing.can_dispense_prescription")

    prescription = get_object_or_404(
        Prescription.objects.select_related("patient").prefetch_related(
            "lines__medicine"
        ),
        pk=prescription_id,
    )

    if prescription.status not in [
        Prescription.Status.VERIFIED,
        Prescription.Status.PARTIALLY_DISPENSED,
    ]:
        messages.error(request, "This prescription is not ready for dispensing.")
        return redirect("prescriptions:detail", pk=prescription.pk)

    form = DispensingForm(
        request.POST or None,
        prescription=prescription,
    )

    if request.method == "POST" and form.is_valid():
        try:
            record = dispense_prescription_line(
                actor=request.user,
                prescription=prescription,
                prescription_line=form.cleaned_data["prescription_line"],
                quantity=form.cleaned_data["quantity"],
                notes=form.cleaned_data["notes"],
            )
            messages.success(
                request,
                f"Dispensing {record.reference} completed successfully."
            )
            return redirect("dispensing:history")
        except (ValidationError, PermissionDenied) as exc:
            form.add_error(None, str(exc))

    line_details = []
    for line in prescription.lines.select_related("medicine"):
        line_details.append({
            "line": line,
            "remaining": get_remaining_quantity(line),
        })

    return render(request, "dispensing/form.html", {
        "prescription": prescription,
        "form": form,
        "line_details": line_details,
    })
