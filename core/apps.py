from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'


class AdminHoneypotConfig(AppConfig):
    """admin_honeypot без своего AppConfig: его миграции созданы с AutoField.

    Без этого класса DEFAULT_AUTO_FIELD=BigAutoField заставлял makemigrations
    генерировать миграцию прямо внутри site-packages.
    """
    name = 'admin_honeypot'
    default_auto_field = 'django.db.models.AutoField'
    verbose_name = 'Admin honeypot'
