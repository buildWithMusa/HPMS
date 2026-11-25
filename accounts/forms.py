
from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    UserChangeForm,
)

from .models import User


class HPMSUserCreationForm(UserCreationForm):
    """
    Form for registering new hospital staff.
    """

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
        )


class HPMSUserChangeForm(UserChangeForm):
    """
    Form for updating existing hospital staff accounts.
    """

    class Meta:
        model = User
        fields = "__all__"
