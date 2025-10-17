FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/srv
WORKDIR /srv
RUN pip install --no-cache-dir redis pymysql
COPY app/ /srv/app/
CMD ["python", "-m", "app.main"]
