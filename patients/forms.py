
from django import forms
from django.forms import formset_factory

from .models import Patient, PatientIdentifier, PatientGuardian


class PatientRegistrationForm(forms.ModelForm):

    class Meta:
        model = Patient
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "date_of_birth",
            "sex",
            "phone_number",
            "email",
            "address",
            "county",
            "sub_county",
        ]

        widgets = {
            "date_of_birth": forms.DateInput(
                attrs={"type": "date"}
            ),
            "address": forms.Textarea(
                attrs={"rows": 3}
            ),
        }

        labels = {
            "first_name": "First name",
            "middle_name": "Middle name",
            "last_name": "Last name",
            "date_of_birth": "Date of birth",
            "sex": "Sex",
            "phone_number": "Phone number",
            "email": "Email address",
        }


class PatientIdentifierForm(forms.ModelForm):

    class Meta:
        model = PatientIdentifier
        fields = [
            "identifier_type",
            "identifier_value",
            "is_primary",
        ]

        labels = {
            "identifier_type": "Document type",
            "identifier_value": "Document number",
            "is_primary": "Primary document",
        }


class PatientGuardianForm(forms.ModelForm):

    class Meta:
        model = PatientGuardian
        fields = [
            "full_name",
            "relationship",
            "phone_number",
            "email",
            "national_id",
            "is_primary",
        ]

        labels = {
            "full_name": "Guardian's full name",
            "relationship": "Relationship to patient",
            "phone_number": "Guardian's phone number",
            "email": "Guardian's email",
            "national_id": "Guardian's national ID",
            "is_primary": "Primary guardian",
        }


PatientIdentifierFormSet = formset_factory(
    PatientIdentifierForm,
    extra=1,
    max_num=5,
    validate_max=True,
)

PatientGuardianFormSet = formset_factory(
    PatientGuardianForm,
    extra=1,
    max_num=3,
    validate_max=True,
)


class PatientUpdateForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "date_of_birth",
            "sex",
            "phone_number",
            "email",
            "address",
            "county",
            "sub_county",
        ]

        widgets = {
            "date_of_birth": forms.DateInput(
                attrs={"type": "date"}
            ),
            "address": forms.Textarea(
                attrs={"rows": 3}
            ),
        }

        labels = {
            "first_name": "First Name",
            "middle_name": "Middle Name",
            "last_name": "Last Name",
            "date_of_birth": "Date of Birth",
            "sex": "Sex",
            "phone_number": "Phone Number",
            "email": "Email Address",
            "address": "Physical Address",
            "county": "County",
            "sub_county": "Sub-county",
        }


