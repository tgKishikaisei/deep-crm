from rest_framework import permissions

from .access import is_crm_admin


class IsOwnerOrAdmin(permissions.BasePermission):
    """Доступ к объекту только владельцу (менеджеру/исполнителю) или админу.

    Основная защита — фильтрация queryset в crm/access.py; это второй рубеж.
    """

    def has_object_permission(self, request, view, obj):
        if is_crm_admin(request.user):
            return True
        owner_id = getattr(obj, 'manager_id', None) or getattr(obj, 'assignee_id', None)
        return owner_id == request.user.id
