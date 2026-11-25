from django import forms

from medicines.models import Medicine
from .models import Supplier, PurchaseOrder, PurchaseOrderLine


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "name", "contact_person", "phone", "email",
            "address", "kra_pin", "notes", "is_active",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["supplier", "expected_delivery_date", "notes"]
        widgets = {
            "expected_delivery_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["supplier"].queryset = Supplier.objects.filter(is_active=True)


class PurchaseOrderLineForm(forms.Form):
    medicine = forms.ModelChoiceField(
        queryset=Medicine.objects.filter(is_active=True),
        empty_label="Select medicine",
    )
    quantity_ordered = forms.IntegerField(min_value=1)
    unit_cost = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    selling_price = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    notes = forms.CharField(required=False, max_length=255)


class RejectPurchaseOrderForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Reason for rejection",
    )


class GoodsReceiptLineForm(forms.Form):
    purchase_order_line = forms.ModelChoiceField(
        queryset=PurchaseOrderLine.objects.none(),
        label="Ordered medicine",
    )
    batch_number = forms.CharField(max_length=100)
    manufacture_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
    )
    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
    )
    quantity_received = forms.IntegerField(min_value=1)
    purchase_price = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0
    )
    selling_price = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0
    )

    def __init__(self, *args, purchase_order=None, **kwargs):
        super().__init__(*args, **kwargs)
        if purchase_order:
            self.fields["purchase_order_line"].queryset = (
                purchase_order.lines.filter(
                    quantity_received__lt=models_F("quantity_ordered")
                ).select_related("medicine")
            )

    def clean(self):
        cleaned = super().clean()
        manufacture = cleaned.get("manufacture_date")
        expiry = cleaned.get("expiry_date")
        if manufacture and expiry and expiry <= manufacture:
            self.add_error("expiry_date", "Expiry must be after manufacture.")
        return cleaned


def models_F(field):
    from django.db.models import F
    return F(field)


class GoodsReceiptHeaderForm(forms.Form):
    supplier_delivery_note = forms.CharField(max_length=100, required=False)
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
