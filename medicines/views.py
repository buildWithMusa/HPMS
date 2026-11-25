
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import MedicineForm
from .models import Medicine
from .services import (
    create_medicine,
    update_medicine,
    change_medicine_status,
)


@login_required
@permission_required("medicines.view_medicine", raise_exception=True)
def medicine_directory(request):
    medicines = Medicine.objects.select_related("category").all()

    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    category_id = request.GET.get("category", "")

    if search:
        medicines = medicines.filter(
            Q(generic_name__icontains=search)
            | Q(brand_name__icontains=search)
            | Q(strength__icontains=search)
        )

    if status == "active":
        medicines = medicines.filter(is_active=True)
    elif status == "inactive":
        medicines = medicines.filter(is_active=False)

    if category_id.isdigit():
        medicines = medicines.filter(category_id=int(category_id))

    paginator = Paginator(medicines, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "medicines/directory.html",
        {
            "page_obj": page_obj,
            "search": search,
            "status": status,
            "category_id": category_id,
        },
    )


@login_required
@permission_required("medicines.view_medicine", raise_exception=True)
def medicine_detail(request, medicine_id):
    medicine = get_object_or_404(
        Medicine.objects.select_related("category"),
        pk=medicine_id
    )

    return render(
        request,
        "medicines/detail.html",
        {"medicine": medicine},
    )


@login_required
@permission_required("medicines.add_medicine", raise_exception=True)
def medicine_create(request):
    form = MedicineForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            try:
                medicine = create_medicine(
                    actor=request.user,
                    medicine_data=form.cleaned_data,
                )

                messages.success(
                    request,
                    "Medicine registered successfully."
                )

                return redirect(
                    "medicines:detail",
                    medicine_id=medicine.pk
                )

            except ValidationError as error:
                form.add_error(None, error)

    return render(
        request,
        "medicines/form.html",
        {
            "form": form,
            "page_title": "Register Medicine",
        },
    )


@login_required
@permission_required("medicines.change_medicine", raise_exception=True)
def medicine_update(request, medicine_id):
    medicine = get_object_or_404(Medicine, pk=medicine_id)

    form = MedicineForm(
        request.POST or None,
        instance=medicine
    )

    if request.method == "POST":
        if form.is_valid():
            try:
                updated_medicine = update_medicine(
                    actor=request.user,
                    medicine=medicine,
                    medicine_data=form.cleaned_data,
                )

                messages.success(
                    request,
                    "Medicine information updated successfully."
                )

                return redirect(
                    "medicines:detail",
                    medicine_id=updated_medicine.pk
                )

            except ValidationError as error:
                form.add_error(None, error)

    return render(
        request,
        "medicines/form.html",
        {
            "form": form,
            "page_title": "Edit Medicine",
        },
    )


@login_required
@permission_required(
    "medicines.can_manage_medicine_status",
    raise_exception=True
)
@require_POST
def medicine_change_status(request, medicine_id):
    medicine = get_object_or_404(Medicine, pk=medicine_id)

    action = request.POST.get("action")

    if action == "activate":
        new_status = True
    elif action == "deactivate":
        new_status = False
    else:
        messages.error(request, "Invalid medicine status action.")
        return redirect(
            "medicines:detail",
            medicine_id=medicine.pk
        )

    try:
        change_medicine_status(
            actor=request.user,
            medicine=medicine,
            new_status=new_status,
        )

        if new_status:
            messages.success(request, "Medicine activated successfully.")
        else:
            messages.success(request, "Medicine deactivated successfully.")

    except ValidationError as error:
        messages.error(request, str(error))

    return redirect(
        "medicines:detail",
        medicine_id=medicine.pk
    )
from django.shortcuts import render

# Create your views here.
