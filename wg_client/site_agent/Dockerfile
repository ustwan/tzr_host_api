FROM python:3.11-slim

WORKDIR /app

# Копируем shared utils (для логирования)
COPY ../shared /app/shared

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код агента
COPY app /app/app

# Переменные окружения по умолчанию (будут переопределены в docker-compose)
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Точка входа
CMD ["python", "-m", "app.interfaces.main"]

