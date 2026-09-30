"""Корневые маршруты Deep CRM."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from core.views import healthz

# Документация API — только для сотрудников (is_staff).
schema_view = get_schema_view(
    openapi.Info(
        title="Deep CRM API",
        default_version='v1',
        description="Документация для мобильного приложения и партнеров",
    ),
    public=False,
    permission_classes=(permissions.IsAdminUser,),
)

urlpatterns = [
    # Настоящая админка — на неочевидном адресе (можно переопределить через ADMIN_URL).
    path(getattr(settings, 'ADMIN_URL', 'secret-control-panel-999/'), admin.site.urls),
    # Ловушка: /admin/ показывает фальшивую форму входа и логирует попытки.
    path('admin/', include('admin_honeypot.urls', namespace='admin_honeypot')),
    # login, logout, password_reset, password_change и т.д.
    path('accounts/', include('django.contrib.auth.urls')),
    path('healthz/', healthz, name='healthz'),
    path('', include('crm.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]

if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    urlpatterns = [path('__debug__/', include('debug_toolbar.urls')), *urlpatterns]
