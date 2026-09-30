"""Локальная разработка: DEBUG, debug-toolbar, Browsable API, письма в консоль."""
import importlib.util
import socket

from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE, REST_FRAMEWORK, config

DEBUG = True
# Для разработки допускаем ключ-заглушку, но только здесь.
SECRET_KEY = config('SECRET_KEY', default='dev-only-insecure-key-do-not-use-in-production')
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# debug-toolbar ставится из requirements-dev.txt; без него dev-настройки тоже работают (например, в Docker).
if importlib.util.find_spec('debug_toolbar'):
    INSTALLED_APPS = [*INSTALLED_APPS, 'debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware', *MIDDLEWARE]

INTERNAL_IPS = ['127.0.0.1']
# В Docker запросы приходят со шлюза сети контейнера (x.x.x.1).
try:
    _, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += [ip[: ip.rfind('.')] + '.1' for ip in ips]
except OSError:
    pass

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# В dev статика отдаётся без манифеста (не нужно запускать collectstatic).
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

# whitenoise: без сканирования STATIC_ROOT при старте (collectstatic здесь не запускается)
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
