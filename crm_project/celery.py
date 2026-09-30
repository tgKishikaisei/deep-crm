# crm_project/celery.py
import os
from celery import Celery

# Указываем Django, где искать настройки
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings.prod')

app = Celery('crm_project')

# Загружаем настройки из settings.py, все, что начинается с CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим tasks.py во всех приложениях
app.autodiscover_tasks()