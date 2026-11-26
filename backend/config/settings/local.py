"""Local-only settings. Never deploy this module to production."""
import os
from .base import *  # noqa: F403,F401
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
if os.environ.get("POSTGRES_HOST"):
    DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "nicat"),
        "USER": os.environ.get("POSTGRES_USER", "nicat"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "nicat_dev_only"),
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": os.environ.get("POSTGRES_PORT", "5432")}}
# SQLite fallback is for quick onboarding. CI runs the same tests on PostgreSQL.

NICAT_CLAMAV_HOST = "127.0.0.1"
NICAT_CLAMAV_PORT = 3310