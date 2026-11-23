FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home django
COPY apps/ ./apps/
COPY config/ ./config/
COPY tests/ ./tests/
COPY manage.py .
RUN install -d -o django -g django /app/staticfiles /app/media
USER django

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && exec gunicorn --bind 0.0.0.0:8000 --workers 2 config.wsgi:application"]
