from django.contrib import admin

# Register your models here.
from django.contrib.auth.admin import UserAdmin
from .models import User


# Мы создаем кастомный класс для отображения пользователей в админке,
# наследуясь от стандартного UserAdmin.
class CustomUserAdmin(UserAdmin):
    # UserAdmin имеет предопределенные наборы полей (fieldsets).
    # Мы копируем их и добавляем наш собственный набор с полем 'role'.

    # Это поля, которые будут отображаться на странице со списком пользователей
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')

    # Это фильтр справа
    list_filter = ('role', 'is_staff', 'is_active', 'groups')

    # Копируем оригинальные fieldsets
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('role',)}),
    )

    # Это поля, которые будут на странице создания пользователя
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительная информация', {'fields': ('role',)}),
    )


# Регистрируем нашу модель User с нашим кастомным классом CustomUserAdmin.
admin.site.register(User, CustomUserAdmin)
