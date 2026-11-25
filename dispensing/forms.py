from django import forms
from django.db.models import Sum

from prescriptions.models import PrescriptionLine


class DispensingForm(forms.Form):
    prescription_line = forms.ModelChoiceField(
        queryset=PrescriptionLine.objects.none(),
        label="Prescription medicine",
    )
    quantity = forms.IntegerField(min_value=1, label="Quantity to dispense")
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Dispensing notes",
    )

    def __init__(self, *args, prescription, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["prescription_line"].queryset = (
            PrescriptionLine.objects.filter(
                prescription=prescription
            ).select_related("medicine")
        )
