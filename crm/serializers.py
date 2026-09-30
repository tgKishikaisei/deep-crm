from rest_framework import serializers

from .access import clients_for, deals_for
from .models import Client, Deal, Task


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'company_name', 'contact_person', 'email', 'phone', 'created_at']
        read_only_fields = ['created_at']


class _UserScopedRelatedField(serializers.PrimaryKeyRelatedField):
    """Связь только с объектами текущего пользователя.

    Иначе менеджер мог бы привязать свою сделку к чужому клиенту или создать
    задачу в чужой сделке.
    """

    scope = None

    def get_queryset(self):
        request = self.context.get('request')
        if request is None:
            return self.queryset.none()
        return type(self).scope(request.user)


class _ClientField(_UserScopedRelatedField):
    scope = staticmethod(clients_for)


class _DealField(_UserScopedRelatedField):
    scope = staticmethod(deals_for)


class DealSerializer(serializers.ModelSerializer):
    client = _ClientField(queryset=Client.objects.all())
    # Название клиента (для чтения), client — id (для привязки).
    client_name = serializers.CharField(source='client.company_name', read_only=True)

    class Meta:
        model = Deal
        fields = ['id', 'title', 'amount', 'stage', 'client', 'client_name', 'created_at']
        read_only_fields = ['created_at']


class TaskSerializer(serializers.ModelSerializer):
    deal = _DealField(queryset=Deal.objects.all())

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'due_date', 'status', 'deal']
