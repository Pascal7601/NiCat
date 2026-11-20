"""Production settings with explicit environment requirements."""
import os
from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F403,F401

def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Missing required production setting: {name}")
    return value

SECRET_KEY = required("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = [x.strip() for x in required("DJANGO_ALLOWED_HOSTS").split(",") if x.strip()]
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql",
    "NAME": required("POSTGRES_DB"), "USER": required("POSTGRES_USER"),
    "PASSWORD": required("POSTGRES_PASSWORD"), "HOST": required("POSTGRES_HOST"),
    "PORT": os.environ.get("POSTGRES_PORT", "5432"), "CONN_MAX_AGE": 60}}
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [x.strip() for x in required("DJANGO_CSRF_TRUSTED_ORIGINS").split(",") if x.strip()]

SIMPLE_JWT["SIGNING_KEY"] = required("JWT_SIGNING_KEY")
