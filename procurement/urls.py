from django.urls import path
from . import views

app_name = "procurement"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("suppliers/", views.supplier_list, name="supplier_list"),
    path("suppliers/add/", views.supplier_create, name="supplier_create"),
    path("orders/", views.purchase_order_list, name="purchase_order_list"),
    path("orders/create/", views.purchase_order_create, name="purchase_order_create"),
    path("orders/<int:pk>/", views.purchase_order_detail, name="purchase_order_detail"),
    path("orders/<int:pk>/submit/", views.purchase_order_submit, name="purchase_order_submit"),
    path("orders/<int:pk>/approve/", views.purchase_order_approve, name="purchase_order_approve"),
    path("orders/<int:pk>/reject/", views.purchase_order_reject, name="purchase_order_reject"),
    path("orders/<int:pk>/receive/", views.goods_receipt_create, name="goods_receipt_create"),
    path("receipts/<int:pk>/", views.goods_receipt_detail, name="goods_receipt_detail"),
]
