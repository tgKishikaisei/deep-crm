from django.contrib import admin

# Register your models here.

from .models import Client, Deal, Task


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_person',
                    'email', 'phone', 'created_at')
    search_fields = ('company_name', 'contact_person',
                     'email')
    list_filter = ('created_at',)


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'amount', 'stage',
                    'manager', 'created_at')
    search_fields = ('title', 'client__company_name')
    list_filter = ('stage', 'manager', 'created_at')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'deal', 'due_date', 'status',
                    'assignee')
    search_fields = ('title', 'deal__title')
    list_filter = ('status', 'assignee', 'due_date')


