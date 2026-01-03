
from rest_framework import viewsets
from .models import Client, Deal, Task
from .serializers import ClientSerializer, DealSerializer, TaskSerializer
from .permissions import IsOwnerOrAdmin
from rest_framework.permissions import IsAuthenticated

# API для Клиентов
class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer

    def get_queryset(self):
        # Middle-уровень фильтруем данные, чтобы менеджер видел только своих
        user = self.request.user
        if user.role == 'ADMIN':
            return Client.objects.all()
        return Client.objects.filter(manager=user)

    def perform_create(self, serializer):
        # Автоматически назначаем менеджера при создании через API
        serializer.save(menager=self.request.user)


# API для Сделок
class DealViewSet(viewsets.ModelViewSet):
    serializer_class = DealSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Deal.objects.select_related('client').all()
        return Deal.objects.select_related('client').filter(manager=user)

    def perform_create(self, serializer):
        serializer.save(manager=self.request.user)


# API для Задач
class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.filter(assignee=self.request.user)

    def perform_create(self, serializer):
        serializer.save(assignee=self.request.user)