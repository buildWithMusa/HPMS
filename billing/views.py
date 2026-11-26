from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from dispensing.models import Dispensing

from .forms import SimulatedPaymentForm
from .models import Invoice, Payment
from .services import create_invoice, simulate_payment


@login_required
@permission_required("billing.can_view_billing", raise_exception=True)
def dashboard(request):
    invoices = Invoice.objects.select_related(
        "patient",
        "dispensing"
    ).order_by("-created_at")

    unbilled = Dispensing.objects.select_related(
        "prescription",
        "prescription__patient"
    ).filter(
        prescription__status__in=[
            "PARTIALLY_DISPENSED",
            "DISPENSED"
        ]
    ).exclude(
        pk__in=Invoice.objects.values("dispensing_id")
    ).order_by("-created_at")

    return render(
        request,
        "billing/dashboard.html",
        {
            "invoices": invoices[:100],
            "unbilled": unbilled[:100],
        }
    )


@login_required
@permission_required("billing.can_create_invoice", raise_exception=True)
def create_invoice_view(request, dispensing_id):
    dispensing = get_object_or_404(
        Dispensing,
        pk=dispensing_id
    )

    if request.method == "POST":
        try:
            invoice = create_invoice(
                actor=request.user,
                dispensing=dispensing
            )
            messages.success(
                request,
                "Invoice created successfully."
            )
            return redirect(
                "billing:invoice_detail",
                invoice_id=invoice.pk
            )
        except ValidationError as exc:
            messages.error(request, str(exc))

    return redirect("billing:dashboard")


@login_required
@permission_required("billing.can_view_billing", raise_exception=True)
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related("patient"),
        pk=invoice_id
    )

    return render(
        request,
        "billing/invoice_detail.html",
        {"invoice": invoice}
    )


@login_required
@permission_required("billing.can_view_billing", raise_exception=True)
def payment_create(request, invoice_id):
    invoice = get_object_or_404(
        Invoice,
        pk=invoice_id
    )

    form = SimulatedPaymentForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data

        try:
            payment = simulate_payment(
                actor=request.user,
                invoice=invoice,
                amount=data["amount"],
                method=data["method"],
                outcome=data["outcome"],
                phone_number=data["phone_number"]
            )

            if payment.status == Payment.Status.SUCCESSFUL:
                messages.success(
                    request,
                    "SIMULATED payment successful."
                )
                return redirect(
                    "billing:receipt",
                    payment_id=payment.pk
                )

            messages.warning(
                request,
                f"Simulated payment {payment.status.lower()}."
            )
            return redirect(
                "billing:invoice_detail",
                invoice_id=invoice.pk
            )

        except ValidationError as exc:
            form.add_error(None, str(exc))

    return render(
        request,
        "billing/payment_form.html",
        {
            "invoice": invoice,
            "form": form
        }
    )


@login_required
@permission_required("billing.can_view_billing", raise_exception=True)
def payment_history(request):
    payments = Payment.objects.select_related(
        "invoice",
        "invoice__patient",
        "initiated_by"
    ).order_by("-created_at")

    return render(
        request,
        "billing/payment_history.html",
        {"payments": payments[:200]}
    )


@login_required
@permission_required("billing.can_view_billing", raise_exception=True)
def receipt(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related(
            "invoice",
            "invoice__patient"
        ),
        pk=payment_id,
        status=Payment.Status.SUCCESSFUL
    )

    return render(
        request,
        "billing/receipt.html",
        {"payment": payment}
    )
