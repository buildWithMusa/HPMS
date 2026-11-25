from django import forms

from medicines.models import Medicine
from .models import StockBatch, StockLocation


class StockReceivingForm(forms.Form):
    medicine = forms.ModelChoiceField(
        queryset=Medicine.objects.filter(is_active=True),
        empty_label="Select medicine"
    )
    batch_number = forms.CharField(max_length=100)
    manufacture_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
    )
    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
    )
    quantity = forms.IntegerField(min_value=1)
    purchase_price = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0
    )
    selling_price = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3})
    )

    def clean_batch_number(self):
        return self.cleaned_data["batch_number"].strip()


class StockTransferForm(forms.Form):
    batch = forms.ModelChoiceField(
        queryset=StockBatch.objects.filter(is_active=True),
        empty_label="Select medicine batch"
    )
    source_location = forms.ModelChoiceField(
        queryset=StockLocation.objects.filter(is_active=True),
        empty_label="Select source location"
    )
    destination_location = forms.ModelChoiceField(
        queryset=StockLocation.objects.filter(is_active=True),
        empty_label="Select destination location"
    )
    quantity = forms.IntegerField(min_value=1)
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3})
    )


class StockAdjustmentForm(forms.Form):
    batch = forms.ModelChoiceField(
        queryset=StockBatch.objects.filter(is_active=True),
        empty_label="Select medicine batch"
    )
    location = forms.ModelChoiceField(
        queryset=StockLocation.objects.filter(is_active=True),
        empty_label="Select stock location"
    )
    quantity_change = forms.IntegerField(
        help_text="Positive number adds stock; negative number removes stock."
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3})
    )

    def clean_quantity_change(self):
        value = self.cleaned_data["quantity_change"]

        if value == 0:
            raise forms.ValidationError("Adjustment cannot be zero.")

        return value
