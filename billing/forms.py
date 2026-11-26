from django import forms

from .models import Payment


class SimulatedPaymentForm(forms.Form):

    method = forms.ChoiceField(
        choices=[
            (Payment.Method.MPESA, "Simulated M-Pesa"),
            (Payment.Method.CASH, "Cash"),
        ]
    )

    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01
    )

    phone_number = forms.CharField(
        max_length=20,
        required=False,
        help_text="Enter a demonstration phone number."
    )

    outcome = forms.ChoiceField(
        choices=[
            ("SUCCESSFUL", "Simulate successful payment"),
            ("FAILED", "Simulate failed payment"),
            ("CANCELLED", "Simulate cancelled payment"),
        ]
    )

    def clean(self):
        cleaned_data = super().clean()

        method = cleaned_data.get("method")
        phone = cleaned_data.get("phone_number", "")

        if method == Payment.Method.MPESA and not phone.strip():
            self.add_error(
                "phone_number",
                "Enter a demonstration phone number."
            )

        return cleaned_data
