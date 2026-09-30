"""Сброс кэша дашборда при изменении данных: новая или закрытая сделка сразу видна в цифрах."""
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Client, Deal, Task


def _drop(*user_ids):
    from .views import dashboard_cache_key

    keys = [dashboard_cache_key(uid) for uid in user_ids if uid]
    if keys:
        cache.delete_many(keys)


@receiver([post_save, post_delete], sender=Deal)
@receiver([post_save, post_delete], sender=Client)
def _deal_or_client_changed(sender, instance, **kwargs):
    _drop(instance.manager_id)


@receiver([post_save, post_delete], sender=Task)
def _task_changed(sender, instance, **kwargs):
    _drop(instance.assignee_id)
