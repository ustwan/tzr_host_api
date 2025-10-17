FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y pigz && rm -rf /var/lib/apt/lists/*
COPY app/ /app/
CMD ["python", "compress.py"]
