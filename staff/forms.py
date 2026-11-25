
from django import forms
from django.contrib.auth.models import Group

from hospital.models import Department, ServiceArea
from .models import StaffProfile


class StaffRegistrationForm(forms.Form):

    email = forms.EmailField(
        label="Staff email address"
    )

    staff_number = forms.CharField(
        max_length=30
    )

    first_name = forms.CharField(
        max_length=100
    )

    middle_name = forms.CharField(
        max_length=100,
        required=False
    )

    last_name = forms.CharField(
        max_length=100
    )

    job_title = forms.CharField(
        max_length=100
    )

    phone_number = forms.CharField(
        max_length=20,
        required=False
    )

    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True)
    )

    service_area = forms.ModelChoiceField(
        queryset=ServiceArea.objects.filter(is_active=True),
        required=False
    )

    role = forms.ModelChoiceField(
        queryset=Group.objects.none()
    )

    date_employed = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["role"].queryset = Group.objects.filter(
            name__in=[
                "Hospital Administrator",
                "Hospital Manager",
                "Pharmacist",
                "Pharmacy Technician",
                "Store Manager",
                "Doctor",
                "Nurse",
                "Procurement Officer",
                "Finance Officer",
                "Cashier",
            ]
        ).order_by("name")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        from accounts.models import User

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def clean_staff_number(self):
        staff_number = self.cleaned_data["staff_number"].strip()

        if StaffProfile.objects.filter(
            staff_number__iexact=staff_number
        ).exists():
            raise forms.ValidationError(
                "This staff number is already registered."
            )

        return staff_number

    def clean(self):
        cleaned_data = super().clean()

        department = cleaned_data.get("department")
        service_area = cleaned_data.get("service_area")

        if (
            department
            and service_area
            and service_area.department_id != department.id
        ):
            self.add_error(
                "service_area",
                "The selected service area does not belong to this department."
            )

        return cleaned_data
