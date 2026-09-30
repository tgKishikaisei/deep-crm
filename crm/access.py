"""
Единые правила доступа к данным CRM.

Админ (role=ADMIN или superuser) видит всё; менеджер — только своих клиентов,
свои сделки и задачи по своим сделкам / назначенные ему. Все представления и
API берут данные только через эти функции, поэтому чужой объект по id даёт 404.
"""
from django.db.models import Q

from .models import Client, Deal, Task


def is_crm_admin(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_superuser or user.role == 'ADMIN'))


def clients_for(user):
    qs = Client.objects.all()
    return qs if is_crm_admin(user) else qs.filter(manager=user)


def deals_for(user):
    qs = Deal.objects.select_related('client', 'manager')
    return qs if is_crm_admin(user) else qs.filter(manager=user)


def tasks_for(user):
    qs = Task.objects.select_related('deal', 'assignee')
    return qs if is_crm_admin(user) else qs.filter(Q(assignee=user) | Q(deal__manager=user)).distinct()
