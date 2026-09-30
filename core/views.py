from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def healthz(request):
    """Проверка живости для Docker/балансировщика: приложение отвечает и БД доступна."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:  # noqa: BLE001 — любая ошибка БД = нездоров
        return JsonResponse({'status': 'error'}, status=503)
    return JsonResponse({'status': 'ok'})
