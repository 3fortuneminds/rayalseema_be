from rest_framework.permissions import BasePermission


class IsRole(BasePermission):
    """Base class — subclass and set `role`."""

    role = None

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == self.role
        )


class IsCustomer(IsRole):
    role = "customer"


class IsRestaurantOwner(IsRole):
    role = "restaurant"


class IsDeliveryPartner(IsRole):
    role = "delivery"


class IsAdminRole(IsRole):
    role = "admin"


class IsOwnerOrAdmin(BasePermission):
    """Object-level: request.user must own the object (via `user` attr) or be admin."""

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True
        owner = getattr(obj, "user", None)
        return owner == request.user
