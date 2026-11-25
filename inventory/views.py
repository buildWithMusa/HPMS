from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    StockReceivingForm,
    StockTransferForm,
    StockAdjustmentForm,
)
from .models import (
    StockLocation,
    StockBatch,
    StockBalance,
    StockMovement,
)
from .services import (
    receive_stock,
    transfer_stock,
    adjust_stock,
    get_expiring_stock,
    get_expired_stock,
)


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def inventory_dashboard(request):
    balances = StockBalance.objects.filter(
        batch__is_active=True,
        location__is_active=True,
    )

    total_quantity = balances.aggregate(
        total=Sum("quantity")
    )["total"] or 0

    active_batches = StockBatch.objects.filter(
        is_active=True
    ).count()

    locations = StockLocation.objects.filter(
        is_active=True
    ).count()

    near_expiry = get_expiring_stock(days=90)
    expired = get_expired_stock()

    recent_movements = StockMovement.objects.select_related(
        "batch",
        "batch__medicine",
        "source_location",
        "destination_location",
        "performed_by",
    )[:10]

    return render(
        request,
        "inventory/dashboard.html",
        {
            "total_quantity": total_quantity,
            "active_batches": active_batches,
            "locations": locations,
            "near_expiry": near_expiry[:10],
            "near_expiry_count": near_expiry.count(),
            "expired": expired[:10],
            "expired_count": expired.count(),
            "recent_movements": recent_movements,
        }
    )


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def stock_balances(request):
    balances = StockBalance.objects.select_related(
        "batch",
        "batch__medicine",
        "location",
        "location__ward",
    ).filter(
        quantity__gt=0
    )

    location_id = request.GET.get("location", "")
    search = request.GET.get("q", "").strip()

    if location_id.isdigit():
        balances = balances.filter(location_id=int(location_id))

    if search:
        balances = balances.filter(
            batch__medicine__generic_name__icontains=search
        ) | balances.filter(
            batch__batch_number__icontains=search
        )

    paginator = Paginator(balances, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "inventory/balances.html",
        {
            "page_obj": page_obj,
            "locations": StockLocation.objects.filter(is_active=True),
            "location_id": location_id,
            "search": search,
        }
    )


@login_required
@permission_required("accounts.can_receive_stock", raise_exception=True)
def receive_stock_view(request):
    form = StockReceivingForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            batch = receive_stock(
                actor=request.user,
                **form.cleaned_data
            )

            messages.success(
                request,
                f"Stock received successfully for batch {batch.batch_number}."
            )

            return redirect("inventory:balances")

        except ValidationError as error:
            form.add_error(None, error)

    return render(
        request,
        "inventory/form.html",
        {
            "form": form,
            "page_title": "Receive Medicine Stock",
        }
    )


@login_required
@permission_required("inventory.can_transfer_stock", raise_exception=True)
def transfer_stock_view(request):
    form = StockTransferForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            transfer_stock(
                actor=request.user,
                **form.cleaned_data
            )

            messages.success(
                request,
                "Stock transferred successfully."
            )

            return redirect("inventory:balances")

        except ValidationError as error:
            form.add_error(None, error)

    return render(
        request,
        "inventory/form.html",
        {
            "form": form,
            "page_title": "Transfer Stock",
        }
    )


@login_required
@permission_required("inventory.can_adjust_stock", raise_exception=True)
def adjust_stock_view(request):
    form = StockAdjustmentForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            adjust_stock(
                actor=request.user,
                **form.cleaned_data
            )

            messages.success(
                request,
                "Stock adjustment completed successfully."
            )

            return redirect("inventory:balances")

        except ValidationError as error:
            form.add_error(None, error)

    return render(
        request,
        "inventory/form.html",
        {
            "form": form,
            "page_title": "Adjust Stock",
        }
    )


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def movement_history(request):
    movements = StockMovement.objects.select_related(
        "batch",
        "batch__medicine",
        "source_location",
        "destination_location",
        "performed_by",
    )

    movement_type = request.GET.get("type", "")

    if movement_type:
        movements = movements.filter(movement_type=movement_type)

    paginator = Paginator(movements, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "inventory/movements.html",
        {
            "page_obj": page_obj,
            "movement_types": StockMovement.MovementType.choices,
            "selected_type": movement_type,
        }
    )


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def expiry_report(request):
    near_expiry = get_expiring_stock(days=90)
    expired = get_expired_stock()

    return render(
        request,
        "inventory/expiry.html",
        {
            "near_expiry": near_expiry,
            "expired": expired,
        }
    )


@login_required
@permission_required("inventory.can_view_inventory", raise_exception=True)
def batch_detail(request, batch_id):
    batch = get_object_or_404(
        StockBatch.objects.select_related("medicine"),
        pk=batch_id
    )

    balances = batch.balances.select_related(
        "location",
        "location__ward",
    )

    movements = batch.movements.select_related(
        "source_location",
        "destination_location",
        "performed_by",
    )[:30]

    return render(
        request,
        "inventory/batch_detail.html",
        {
            "batch": batch,
            "balances": balances,
            "movements": movements,
        }
    )

