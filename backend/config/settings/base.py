"""Shared settings; production overrides fail closed on required secrets."""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "development-only-not-for-deployment")
DEBUG = False
ALLOWED_HOSTS: list[str] = []
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "drf_spectacular", "rest_framework_simplejwt.token_blacklist",
    "apps.accounts", "apps.academics", "apps.resources", "apps.questions",
    "apps.exams", "apps.attempts", "apps.analytics", "apps.common", "apps.study_tutor",
    "apps.study_coach",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
              "DIRS": [], "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.debug",
                  "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
                  "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"  # API/persistence UTC; frontend displays Africa/Nairobi.
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle",
                                 "rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "30/min", "user": "240/min"},
}
SPECTACULAR_SETTINGS = {"TITLE": "NiCat API", "DESCRIPTION": "Independent exam practice platform",
                        "VERSION": "0.3.0", "SERVE_INCLUDE_SCHEMA": False}
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # Next.js sends X-CSRFToken; token is not a login credential.
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024

# JWT-only for the API. Django admin retains its own session authentication.
# Next.js should hold refresh tokens in server-side / HttpOnly cookie storage,
# not in localStorage. See docs/JWT_AUTH.md.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "ALGORITHM": "HS256",
    "SIGNING_KEY": os.environ.get("JWT_SIGNING_KEY", SECRET_KEY),
    "JTI_CLAIM": "jti",
    "CHECK_REVOKE_TOKEN": True,
}

# Sprint 6: AI-assisted essay marking

if "apps.ai_tutor" not in INSTALLED_APPS:
    INSTALLED_APPS.append("apps.ai_tutor")

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["ai_marking"] = "10/hour"

NICAT_AI_FOLLOWUPS_ENABLED = os.environ.get("NICAT_AI_FOLLOWUPS_ENABLED", "false").lower() == "true"
NICAT_AI_RECOMMENDATIONS_ENABLED = os.environ.get("NICAT_AI_RECOMMENDATIONS_ENABLED", "false").lower() == "true"
NICAT_COACH_STUDENT_DAILY_LIMIT = int(os.environ.get("NICAT_COACH_STUDENT_DAILY_LIMIT", "3"))
NICAT_COACH_GLOBAL_DAILY_LIMIT = int(os.environ.get("NICAT_COACH_GLOBAL_DAILY_LIMIT", "100"))
REST_FRAMEWORK.setdefault("DEFAULT_THROTTLE_RATES", {})["coach_followups"] = "20/hour"

NICAT_AI_MARKING_ENABLED = (
    os.environ.get("NICAT_AI_MARKING_ENABLED", "false").lower()
    == "true"
)

NICAT_AI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

NICAT_AI_MODEL = os.environ.get("NICAT_AI_MODEL", "")

NICAT_AI_TUTOR_ENABLED = os.environ.get("NICAT_AI_TUTOR_ENABLED", "false").lower() == "true"
NICAT_AI_TUTOR_GENERATION_ENABLED = (
    os.environ.get("NICAT_AI_TUTOR_GENERATION_ENABLED", "false").lower() == "true"
)
NICAT_AI_TUTOR_MODEL = os.environ.get("NICAT_AI_TUTOR_MODEL", "") or os.environ.get("NICAT_AI_MODEL", "")
REST_FRAMEWORK.setdefault("DEFAULT_THROTTLE_RATES", {})["tutor_drafts"] = "8/hour"

NICAT_AI_PROVIDER = os.environ.get(
    "NICAT_AI_PROVIDER", "openai"
).lower()