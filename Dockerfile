
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home nicat

COPY backend /app/backend
COPY data /app/data

WORKDIR /app/backend

# Build static assets without injecting production secrets.
RUN DJANGO_SETTINGS_MODULE=config.settings.base \
    python manage.py collectstatic --noinput

USER nicat

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-"]