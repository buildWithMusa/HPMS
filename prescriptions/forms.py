from django import forms

from patients.models import Patient
from medicines.models import Medicine

from .models import Prescription, PrescriptionLine


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ["patient", "diagnosis", "clinical_notes"]
        widgets = {
            "clinical_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = Patient.objects.filter(
            is_active=True
        )


class PaperPrescriptionForm(forms.Form):
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.filter(is_active=True)
    )
    prescriber_name = forms.CharField(max_length=200)
    prescriber_registration = forms.CharField(
        max_length=100,
        required=False
    )
    external_reference = forms.CharField(
        max_length=100,
        required=False
    )
    diagnosis = forms.CharField(max_length=255, required=False)
    clinical_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3})
    )


class PrescriptionLineForm(forms.ModelForm):
    class Meta:
        model = PrescriptionLine
        fields = [
            "medicine",
            "dose",
            "route",
            "frequency",
            "duration_days",
            "quantity",
            "instructions",
        ]
        widgets = {
            "instructions": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["medicine"].queryset = Medicine.objects.filter(
            is_active=True
        )


class RejectionForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        max_length=2000
    )
