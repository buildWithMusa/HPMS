
"""
Reusable authorization functions for HPMS.

These functions are intended to be used in views,
services and business-operation workflows.
"""

from django.core.exceptions import PermissionDenied


def has_hpms_permission(user, permission):
    """
    Return True when an authenticated, active user
    has the requested Django permission.

    Superusers are handled by Django's has_perm().
    """

    if not user or not user.is_authenticated:
        return False

    if not user.is_active:
        return False

    return user.has_perm(permission)


def require_hpms_permission(user, permission):
    """
    Require a specific HPMS permission.

    Raises PermissionDenied when access is not allowed.
    """

    if not has_hpms_permission(user, permission):
        raise PermissionDenied(
            "You are not authorized to perform this operation."
        )

    return True


def require_any_hpms_permission(user, permissions):
    """
    Require at least one permission from a supplied list.
    """

    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionDenied(
            "Authentication is required."
        )

    if not any(
        user.has_perm(permission)
        for permission in permissions
    ):
        raise PermissionDenied(
            "You do not have the required permission."
        )

    return True


def authorize_approval(actor, initiator, permission):
    """
    Check whether a user can approve an operation.

    Requirements:
    1. The actor must be authenticated and active.
    2. The actor must have the required approval permission.
    3. The actor must not be the person who initiated the operation.

    The transaction-specific service must still validate
    transaction status, approval limits and audit records.
    """

    require_hpms_permission(actor, permission)

    if initiator is None:
        raise PermissionDenied(
            "The transaction initiator could not be identified."
        )

    if actor.pk == initiator.pk:
        raise PermissionDenied(
            "You cannot approve an operation that you initiated."
        )

    return True
