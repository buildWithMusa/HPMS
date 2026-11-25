from django.contrib import admin
from .models import (
    Supplier,
    PurchaseOrder,
    PurchaseOrderLine,
    GoodsReceipt,
    GoodsReceiptLine,
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_person", "phone", "email", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "contact_person", "phone", "kra_pin")


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 0
    readonly_fields = ("quantity_received",)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number", "supplier", "status", "created_by",
        "approved_by", "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("order_number", "supplier__name")
    readonly_fields = (
        "order_number", "created_by", "submitted_at",
        "approved_by", "approved_at", "rejected_by", "rejected_at",
    )
    inlines = [PurchaseOrderLineInline]


class GoodsReceiptLineInline(admin.TabularInline):
    model = GoodsReceiptLine
    extra = 0
    readonly_fields = ("stock_batch",)


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_number", "purchase_order", "received_by", "received_at",
    )
    search_fields = ("receipt_number", "purchase_order__order_number")
    readonly_fields = ("receipt_number", "received_by", "received_at")
    inlines = [GoodsReceiptLineInline]
