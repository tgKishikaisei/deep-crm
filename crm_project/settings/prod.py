"""
Продакшен. Старт без обязательных переменных окружения невозможен — это намеренно.

Обязательно: SECRET_KEY (≥ 50 символов), ALLOWED_HOSTS, DB_PASSWORD.
Рекомендуется: CSRF_TRUSTED_ORIGINS (https://crm.example.com), TRUSTED_PROXY_COUNT=1 за nginx.
"""
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import SECRET_KEY, Csv, config

DEBUG = False

_PLACEHOLDERS = {'', 'your_secret_key_here', 'change-me', 'changeme', 'secret'}
if SECRET_KEY in _PLACEHOLDERS or len(SECRET_KEY) < 50 or SECRET_KEY.startswith('django-insecure'):
    raise ImproperlyConfigured(
        'SECRET_KEY не задан или слабый. Сгенерируйте: '
        'python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"'
    )

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS должен содержать конкретные домены.')
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# HTTPS терминируется на nginx/балансировщике: доверяем его заголовку о схеме.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
# Health-check контейнера ходит по http внутри сети — без редиректа.
SECURE_REDIRECT_EXEMPT = [r'^healthz/$']
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=False, cast=bool)
if not SECURE_HSTS_PRELOAD:
    # Preload-список браузеров — необратимое решение для всего домена; включайте осознанно.
    SILENCED_SYSTEM_CHECKS = ['security.W021']
SESSION_COOKIE_AGE = 60 * 60 * 12

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_TIMEOUT = 10
