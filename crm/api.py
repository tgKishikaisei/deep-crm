from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .access import clients_for, deals_for, is_crm_admin, tasks_for
from .permissions import IsOwnerOrAdmin
from .serializers import ClientSerializer, DealSerializer, TaskSerializer


class ClientViewSet(viewsets.ModelViewSet):
    """Клиенты: менеджер видит и меняет только своих (чужой id → 404)."""
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        return clients_for(self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(manager=self.request.user)

    def perform_destroy(self, instance):
        # Удаление клиента (каскадом со сделками) — только админ, как и в веб-интерфейсе.
        if not is_crm_admin(self.request.user):
            self.permission_denied(self.request, message='Удалять клиентов может только администратор.')
        instance.delete()


class DealViewSet(viewsets.ModelViewSet):
    serializer_class = DealSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        return deals_for(self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(manager=self.request.user)

    def perform_destroy(self, instance):
        if not is_crm_admin(self.request.user):
            self.permission_denied(self.request, message='Удалять сделки может только администратор.')
        instance.delete()


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return tasks_for(self.request.user).order_by('due_date')

    def perform_create(self, serializer):
        serializer.save(assignee=self.request.user)
