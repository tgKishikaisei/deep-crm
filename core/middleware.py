"""Заголовки безопасности, которых нет в SecurityMiddleware Django 5.2 (CSP и Permissions-Policy).

CSP строгая для скриптов: встроенные <script> выполняются только с одноразовым nonce
текущего запроса (`nonce="{{ request.csp_nonce }}"` в шаблонах), inline-обработчики
вроде onclick="..." запрещены. Внедрённый через XSS скрипт nonce не знает и не выполнится.
"""
import secrets

# CDN, с которых шаблоны грузят библиотеки. Любой другой хост для скриптов заблокирован,
# так что внедрённый скрипт не сможет подтянуть код или отправить данные на чужой сервер.
_CDN = 'https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com'

PERMISSIONS_POLICY = 'camera=(), microphone=(), geolocation=(), payment=(), usb=()'


def build_csp(nonce: str, allow_eval: bool = False) -> str:
    script_src = f"script-src 'self' 'nonce-{nonce}' {_CDN}"
    if allow_eval:
        # Только для страниц, помеченных allow_eval_csp (3D-сцена Spline использует eval).
        script_src += " 'unsafe-eval' 'wasm-unsafe-eval'"
    return '; '.join([
        "default-src 'self'",
        script_src,
        # Встроенные атрибуты onclick и т.п. запрещены явно.
        "script-src-attr 'none'",
        # Стили пока допускают inline: шаблоны и библиотеки (ApexCharts, driver.js) их широко используют.
        f"style-src 'self' 'unsafe-inline' {_CDN}",
        f"font-src 'self' data: {_CDN}",
        "img-src 'self' data: blob: https://i.giphy.com https://app.spline.design",
        "media-src 'self' https://videos.pexels.com https://www.pexels.com https://cdn.pixabay.com",
        # Spline-viewer на странице «Лаборатория» скачивает сцену и wasm.
        f"connect-src 'self' https://prod.spline.design {_CDN}",
        "worker-src 'self' blob:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ])


def allow_eval_csp(response):
    """Пометить ответ: разрешить eval в CSP только для этой страницы."""
    response.csp_allow_eval = True
    return response


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        response.headers.setdefault('Permissions-Policy', PERMISSIONS_POLICY)
        # Страницы debug-toolbar и Swagger UI держат свои inline-ресурсы — им CSP не навязываем.
        if not request.path.startswith(('/__debug__/', '/swagger/', '/redoc/')):
            response.headers.setdefault(
                'Content-Security-Policy',
                build_csp(request.csp_nonce, allow_eval=getattr(response, 'csp_allow_eval', False)),
            )
        return response
