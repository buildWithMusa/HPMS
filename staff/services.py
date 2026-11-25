
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import StaffProfile, StaffAssignment


User = get_user_model()


@transaction.atomic
def register_staff(validated_data):
    """
    Register a hospital employee.

    This operation:
    1. Creates the employee's login account.
    2. Assigns the selected HPMS role.
    3. Creates the employee's staff profile.
    4. Creates the employee's department assignment.

    All database operations are atomic.
    """

    # 1. Create the user account.
    user = User(
        email=validated_data["email"],
        first_name=validated_data["first_name"],
        last_name=validated_data["last_name"],
        is_active=False,
    )

    # Prevent login until the employee creates a password.
    user.set_unusable_password()
    user.save()

    # 2. Assign the selected HPMS role.
    role = validated_data["role"]
    user.groups.add(role)

    # 3. Create the employee's staff profile.
    staff = StaffProfile.objects.create(
        user=user,
        staff_number=validated_data["staff_number"],
        first_name=validated_data["first_name"],
        middle_name=validated_data.get("middle_name", ""),
        last_name=validated_data["last_name"],
        job_title=validated_data["job_title"],
        phone_number=validated_data.get("phone_number", ""),
        date_employed=validated_data.get("date_employed"),
    )

    # 4. Create the primary department assignment.
    StaffAssignment.objects.create(
        staff=staff,
        department=validated_data["department"],
        service_area=validated_data.get("service_area"),
        is_primary=True,
        is_active=True,
    )

    return staff


def send_staff_activation_email(request, user):
    """
    Generate a secure activation link and send it
    to the newly registered employee.
    """

    # Encode the user's database ID.
    uid = urlsafe_base64_encode(
        force_bytes(user.pk)
    )

    # Generate Django's secure activation token.
    token = default_token_generator.make_token(user)

    # Build the activation URL.
    activation_path = reverse(
        "staff:activate",
        kwargs={
            "uidb64": uid,
            "token": token,
        }
    )

    activation_link = request.build_absolute_uri(
        activation_path
    )

    # Prepare the activation email.
    subject = "Activate your HPMS staff account"

    message = f"""
Hello {user.first_name},

Your Hospital Pharmacy Management System account has been created.

To activate your account and create your password, open the link below:

{activation_link}

This link is time-limited and can only be used while it remains valid.

If you were not expecting this account, please contact your hospital administrator.

Hospital Pharmacy Management System
"""

    # Send the activation email.
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
