FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc wget \
    g++ \
    libpq-dev \
    pigz \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установка переменных окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/app

# Создание рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY ./api_4/requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
# Copy only app subtree to stable path and also shared
COPY ./api_4/. .
COPY ./shared /app/shared

# Копирование нового парсера
COPY ./example /app/example

# Копирование скриптов миграций и entrypoint
COPY ./api_4/apply_migrations.sh /app/apply_migrations.sh
COPY ./api_4/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/apply_migrations.sh /app/entrypoint.sh

# Создание пользователя для безопасности
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Открытие порта
EXPOSE 8084

# Entrypoint для автоматических миграций
ENTRYPOINT ["/app/entrypoint.sh"]

# Команда запуска
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8084", "--workers", "1"]
