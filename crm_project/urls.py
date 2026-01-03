"""
URL configuration for crm_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
   openapi.Info(
      title="Deep CRM API",
      default_version='v1',
      description="Документация для мобильного приложения и партнеров",
      contact=openapi.Contact(email="admin@deepcrm.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Стало (придумай что-то сложное):
    path('secret-control-panel-999/', admin.site.urls),

    path('admin/', include('admin_honeypot.urls',
                           namespace='admin_honeypot')),  # ЛОВУШКА
    # Подключаем все стандартные URL-адреса для аутентификации
    # (login, logout, password_reset, password_change и т.д)
    # по адресу /accounts/
    path('accounts/', include('django.contrib.auth.urls')),
    # Наши CRM URL-м
    path('', include('crm.urls')),
    # --- ПУТИ ДЛЯ ДОКУМЕНТАЦИИ ---
    # Обычный Swagger (самый популярный)
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    # Redoc (более современный дизайн, но только для чтения)
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # Ссылка на JSON файл схемы (нужна для некоторых инструментов)
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),

]

"""
Мы подключили 'django.contrib.auth.urls' Это избавляет нас от необходимости вручную
создавать URL-ы и представления для таких страниц как '/account/login/', '/accounts/logout/' 
и других. Django все сделает за нас

Теперь нас нужно сказать Django, что делать после входа и выхода
м куда перенаправлять пользователя, если он пытается зайти на защищенную странницу 
без авторизации 
"""


# Добавляем этот блок для Debug Toolbar
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns



