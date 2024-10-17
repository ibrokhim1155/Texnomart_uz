from rest_framework.permissions import BasePermission


class IsSuperAdminOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_authenticated:
            if (request.user.is_superuser or request.user.is_staff) and request.method =='Delete':
                return True
            return False
