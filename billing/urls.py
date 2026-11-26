from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path(
        "dispensing/<int:dispensing_id>/invoice/",
        views.create_invoice_view,
        name="create_invoice"
    ),
    path(
        "invoice/<int:invoice_id>/",
        views.invoice_detail,
        name="invoice_detail"
    ),
    path(
        "invoice/<int:invoice_id>/pay/",
        views.payment_create,
        name="payment_create"
    ),
    path(
        "history/",
        views.payment_history,
        name="payment_history"
    ),
    path(
        "receipt/<int:payment_id>/",
        views.receipt,
        name="receipt"
    ),
]
