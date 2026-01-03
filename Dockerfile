# 1. Берем базовый образ Python (Linux)
FROM python:3.10-slim

# 2. Отключаем создание мусора (.pyc файлов) и буферизацию вывода
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# 4. Устанавливаем зависимости для Postgres (нужны для Linux)
RUN apt-get update \
    && apt-get install -y gcc libpq-dev \
    && apt-get clean

# 5. Копируем файл зависимостей и устанавливаем их
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 6. Копируем весь код проекта внутрь контейнера
COPY . /app/

# 7. Команда по умолчанию (будет переопределена в docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]