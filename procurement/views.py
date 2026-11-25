from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Supplier, PurchaseOrder, GoodsReceipt
from .forms import (
    SupplierForm,
    PurchaseOrderForm,
    PurchaseOrderLineForm,
    RejectPurchaseOrderForm,
    GoodsReceiptLineForm,
    GoodsReceiptHeaderForm,
)
from .services import (
    create_supplier,
    create_purchase_order,
    add_purchase_order_line,
    submit_purchase_order,
    approve_purchase_order,
    reject_purchase_order,
    receive_purchase_order,
)


def _check_permission(user, permission):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied("You must be logged in.")
    if not user.has_perm(permission):
        raise PermissionDenied("You do not have permission to perform this action.")


@login_required
def dashboard(request):
    _check_permission(request.user, "procurement.can_view_procurement")

    context = {
        "supplier_count": Supplier.objects.filter(is_active=True).count(),
        "total_orders": PurchaseOrder.objects.count(),
        "pending_orders": PurchaseOrder.objects.filter(
            status=PurchaseOrder.Status.SUBMITTED
        ).count(),
        "approved_orders": PurchaseOrder.objects.filter(
            status=PurchaseOrder.Status.APPROVED
        ).count(),
        "partial_orders": PurchaseOrder.objects.filter(
            status=PurchaseOrder.Status.PARTIALLY_RECEIVED
        ).count(),
        "recent_orders": PurchaseOrder.objects.select_related(
            "supplier", "created_by"
        )[:8],
    }
    return render(request, "procurement/dashboard.html", context)


@login_required
def supplier_list(request):
    _check_permission(request.user, "procurement.can_view_procurement")
    suppliers = Supplier.objects.all()

    query = request.GET.get("q", "").strip()
    if query:
        suppliers = suppliers.filter(name__icontains=query)

    return render(request, "procurement/supplier_list.html", {
        "suppliers": suppliers,
        "query": query,
    })


@login_required
def supplier_create(request):
    _check_permission(request.user, "procurement.can_manage_suppliers")

    form = SupplierForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            create_supplier(request.user, **form.cleaned_data)
            messages.success(request, "Supplier registered successfully.")
            return redirect("procurement:supplier_list")
        except (ValidationError, PermissionDenied) as exc:
            form.add_error(None, exc)

    return render(request, "procurement/form.html", {
        "form": form,
        "page_title": "Register supplier",
        "cancel_url": "procurement:supplier_list",
    })


@login_required
def purchase_order_list(request):
    _check_permission(request.user, "procurement.can_view_procurement")

    orders = PurchaseOrder.objects.select_related(
        "supplier", "created_by", "approved_by"
    ).prefetch_related("lines")

    status = request.GET.get("status", "").strip()
    if status in PurchaseOrder.Status.values:
        orders = orders.filter(status=status)

    query = request.GET.get("q", "").strip()
    if query:
        orders = orders.filter(
            order_number__icontains=query
        ) | orders.filter(supplier__name__icontains=query)

    return render(request, "procurement/purchase_order_list.html", {
        "orders": orders,
        "status_choices": PurchaseOrder.Status.choices,
        "selected_status": status,
        "query": query,
    })


@login_required
def purchase_order_create(request):
    _check_permission(request.user, "accounts.can_create_purchase_order")

    form = PurchaseOrderForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            order = create_purchase_order(
                actor=request.user,
                supplier=form.cleaned_data["supplier"],
                expected_delivery_date=form.cleaned_data["expected_delivery_date"],
                notes=form.cleaned_data["notes"],
            )
            messages.success(request, "Draft purchase order created.")
            return redirect("procurement:purchase_order_detail", pk=order.pk)
        except (ValidationError, PermissionDenied) as exc:
            form.add_error(None, exc)

    return render(request, "procurement/form.html", {
        "form": form,
        "page_title": "Create purchase order",
        "cancel_url": "procurement:purchase_order_list",
    })


@login_required
def purchase_order_detail(request, pk):
    _check_permission(request.user, "procurement.can_view_procurement")

    order = get_object_or_404(
        PurchaseOrder.objects.select_related(
            "supplier", "created_by", "approved_by", "rejected_by"
        ).prefetch_related("lines__medicine", "goods_receipts__lines"),
        pk=pk,
    )

    line_form = PurchaseOrderLineForm()
    if request.method == "POST":
        _check_permission(request.user, "accounts.can_create_purchase_order")
        line_form = PurchaseOrderLineForm(request.POST)
        if line_form.is_valid():
            try:
                add_purchase_order_line(
                    actor=request.user,
                    purchase_order=order,
                    **line_form.cleaned_data,
                )
                messages.success(request, "Medicine added to purchase order.")
                return redirect("procurement:purchase_order_detail", pk=order.pk)
            except (ValidationError, PermissionDenied) as exc:
                line_form.add_error(None, exc)

    return render(request, "procurement/purchase_order_detail.html", {
        "order": order,
        "line_form": line_form,
        "receipts": order.goods_receipts.all(),
    })


@login_required
@require_POST
def purchase_order_submit(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    try:
        submit_purchase_order(request.user, order)
        messages.success(request, "Purchase order submitted for approval.")
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, str(exc))
    return redirect("procurement:purchase_order_detail", pk=pk)


@login_required
@require_POST
def purchase_order_approve(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    try:
        approve_purchase_order(request.user, order)
        messages.success(request, "Purchase order approved.")
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, str(exc))
    return redirect("procurement:purchase_order_detail", pk=pk)


@login_required
def purchase_order_reject(request, pk):
    _check_permission(request.user, "accounts.can_approve_purchase_order")
    order = get_object_or_404(PurchaseOrder, pk=pk)

    form = RejectPurchaseOrderForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            reject_purchase_order(
                request.user, order, form.cleaned_data["reason"]
            )
            messages.success(request, "Purchase order rejected.")
            return redirect("procurement:purchase_order_detail", pk=pk)
        except (ValidationError, PermissionDenied) as exc:
            form.add_error(None, exc)

    return render(request, "procurement/form.html", {
        "form": form,
        "page_title": f"Reject {order.order_number}",
        "cancel_url": "procurement:purchase_order_detail",
        "cancel_pk": order.pk,
    })


@login_required
def goods_receipt_create(request, pk):
    _check_permission(request.user, "procurement.can_receive_purchase_order")
    order = get_object_or_404(
        PurchaseOrder.objects.prefetch_related("lines__medicine"),
        pk=pk,
    )

    ReceiptLineFormSet = formset_factory(
        GoodsReceiptLineForm,
        extra=1,
        can_delete=False,
    )

    if request.method == "POST":
        header_form = GoodsReceiptHeaderForm(request.POST)
        formset = ReceiptLineFormSet(
            request.POST,
            form_kwargs={"purchase_order": order},
        )

        if header_form.is_valid() and formset.is_valid():
            lines = [
                form.cleaned_data
                for form in formset
                if form.cleaned_data
            ]
            try:
                receipt = receive_purchase_order(
                    actor=request.user,
                    purchase_order=order,
                    received_lines=lines,
                    supplier_delivery_note=header_form.cleaned_data[
                        "supplier_delivery_note"
                    ],
                    notes=header_form.cleaned_data["notes"],
                )
                messages.success(
                    request,
                    f"Goods received successfully. GRN: {receipt.receipt_number}",
                )
                return redirect("procurement:goods_receipt_detail", pk=receipt.pk)
            except (ValidationError, PermissionDenied) as exc:
                messages.error(request, str(exc))
    else:
        header_form = GoodsReceiptHeaderForm()
        formset = ReceiptLineFormSet(
            form_kwargs={"purchase_order": order}
        )

    return render(request, "procurement/goods_receipt_form.html", {
        "order": order,
        "header_form": header_form,
        "formset": formset,
    })


@login_required
def goods_receipt_detail(request, pk):
    _check_permission(request.user, "procurement.can_view_procurement")
    receipt = get_object_or_404(
        GoodsReceipt.objects.select_related(
            "purchase_order", "received_by", "purchase_order__supplier"
        ).prefetch_related(
            "lines__purchase_order_line__medicine", "lines__stock_batch"
        ),
        pk=pk,
    )
    return render(request, "procurement/goods_receipt_detail.html", {
        "receipt": receipt,
    })
