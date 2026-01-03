
from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Разрешает доступ только Владельцу объекта (менеджеру) или Админу.
    """

    def has_object_permission(self, request, view, obj):
        # 1. Админу можно всё
        if request.user.role == 'ADMIN':
            return True

        # 2. Проверяем, есть ли у объекта атрибут 'manager' или 'assignee'
        # (для сделок/клиентов это manager, для задач - assignee)
        owner = getattr(obj, 'manager', getattr(obj, 'assignee', None))

        # 3. Разрешаем, только если текущий юзер совпадает с владельцем
        return obj == request.user or owner == request.user