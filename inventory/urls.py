from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.inventory_dashboard, name="dashboard"),
    path("balances/", views.stock_balances, name="stock_balances"),
    path("receive/", views.receive_stock_view, name="receive_stock"),
    path("transfer/", views.transfer_stock_view, name="transfer_stock"),
    path("adjust/", views.adjust_stock_view, name="adjust_stock"),
    path("movements/", views.movement_history, name="movement_history"),
    path("expiry/", views.expiry_report, name="expiry_report"),
    path("batch/<int:batch_id>/", views.batch_detail, name="batch_detail"),
]
