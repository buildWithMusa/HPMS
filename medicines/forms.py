from django import forms
from .models import Medicine, MedicineCategory


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = [
            "category",
            "generic_name",
            "brand_name",
            "strength",
            "dosage_form",
            "unit_of_measure",
            "description",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = MedicineCategory.objects.filter(
            is_active=True
        )

    def clean_generic_name(self):
        return self.cleaned_data["generic_name"].strip()

    def clean_brand_name(self):
        return self.cleaned_data["brand_name"].strip()

    def clean_strength(self):
        return self.cleaned_data["strength"].strip()


class MedicineCategoryForm(forms.ModelForm):
    class Meta:
        model = MedicineCategory
        fields = ["name", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_name(self):
        return self.cleaned_data["name"].strip()
