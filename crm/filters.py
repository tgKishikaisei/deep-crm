import django_filters
from .models import Client, Deal
from users.models import User  # Для фильтрации по менеджеру


class ClientFilter(django_filters.FilterSet):
    # Поиск по названию компании (case-insensitive contains)
    company_name = django_filters.CharFilter(
        field_name='company_name',
        lookup_expr='icontains',
        label='Название компании содержит'
    )

    # фильтрация по менеджеру (выпадающий список)
    # Используем djangi_filters.ModelChoiceFilter для ForeignKey полей
    manager = django_filters.ModelChoiceFilter(
        queryset=User.objects.filter(role='MANAGER'),  # Показываем только пользователей сс ролью 'MANAGER'
        label='Менеджер',
        empty_label='Все менеджеры'  # Опция "Выбрать всех"
    )

    class Meta:
        model = Client
        fields = ['company_name', 'manager']  # Поля, которые мы будем использовать для фильтрации
