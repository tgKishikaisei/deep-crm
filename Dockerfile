# syntax=docker/dockerfile:1
# --- Сборка зависимостей: только пакеты с проверенными хэшами из requirements.txt ---
FROM python:3.12-slim-bookworm AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.txt .
RUN pip install --require-hashes -r requirements.txt

# --- Рабочий образ: без компиляторов, не-root пользователь ---
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    DJANGO_SETTINGS_MODULE=crm_project.settings.prod
RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app . .
# Статика собирается при сборке образа (whitenoise отдаёт её с хэшами в именах).
# Ключ ниже нужен только чтобы загрузить prod-настройки; в рантайме он не используется.
RUN SECRET_KEY=build-only-collectstatic-key-not-used-at-runtime-0123456789 \
    ALLOWED_HOSTS=localhost python manage.py collectstatic --noinput \
    && chown -R app:app /app/staticfiles
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD \
    python -c "import os,sys,urllib.request as u; h=os.environ['ALLOWED_HOSTS'].split(',')[0]; r=u.urlopen(u.Request('http://127.0.0.1:8000/healthz/', headers={'Host': h}), timeout=3); sys.exit(r.status != 200)"
CMD ["gunicorn", "crm_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "30", "--access-logfile", "-", "--worker-tmp-dir", "/dev/shm"]
