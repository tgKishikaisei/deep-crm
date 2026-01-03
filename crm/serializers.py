
from rest_framework import serializers
from .models import Client, Deal, Task

# Сериализация для клиентов
class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'company_name', 'contact_person', 'email', 'phone', 'created_at']

# Сериализация для Сделок
class DealSerializer(serializers.ModelSerializer):
    # Чтобы вместо ID клиента видеть его название (для чтения)
    client_name = serializers.CharField(source='client.company_name', read_only=True)

    class Meta:
        model = Deal
        # client = это ID (чтобы привязать), client_name - это текст (чтобы прочитать)
        fields = ['id', 'title', 'amount', 'stage', 'client', 'client_name', 'created_at']


# Сериализатор для задач
class TaskSerializer(serializers.ModelSerializer):
     class Meta:
         model = Task
         fields = ['id', 'title', 'description', 'due_date', 'status', 'deal']


