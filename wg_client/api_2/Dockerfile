FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/srv
WORKDIR /srv
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir fastapi uvicorn httpx pydantic
COPY app/ /srv/app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8082"]


