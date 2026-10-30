"""Reusable DRF permission classes."""

from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsAuthenticatedUser(BasePermission):
    """Require a valid, active, authenticated user."""

    message = "Authentication required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_active)


class IsOwner(BasePermission):
    """Allow access when the object belongs to the request user."""

    message = "You do not have permission to access this object."
    owner_field = "user_id"

    def has_object_permission(self, request, view, obj) -> bool:
        owner_id = getattr(obj, self.owner_field, None)
        return owner_id is not None and str(owner_id) == str(request.user.pk)
