"""Тесты: SQLite в памяти, локальный кэш, Celery выполняет задачи сразу — Redis и Postgres не нужны."""
from .base import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = 'test-only-secret-key-' + 'x' * 40
ALLOWED_HOSTS = ['testserver', 'localhost']

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
# Троттлинг DRF в тестах мешает (кэш общий между тестами).
REST_FRAMEWORK = {**REST_FRAMEWORK, 'DEFAULT_THROTTLE_CLASSES': []}  # noqa: F405
AXES_ENABLED = True

# whitenoise: без сканирования STATIC_ROOT при старте (collectstatic здесь не запускается)
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
