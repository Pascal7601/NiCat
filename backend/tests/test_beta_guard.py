"""Sprint 9 production guard tests; no database or shared fixtures required."""
from django.test import override_settings

from apps.beta_guard.checks import nicat_beta_deployment_checks


SAFE = {
    "NICAT_BETA_ENV": "production",
    "DEBUG": False,
    "ALLOWED_HOSTS": ["api.nicat.example"],
    "DATABASES": {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "test"}},
    "SESSION_COOKIE_SECURE": True,
    "CSRF_COOKIE_SECURE": True,
    "SECURE_SSL_REDIRECT": True,
    "SECURE_HSTS_SECONDS": 300,
    "CORS_ALLOW_ALL_ORIGINS": False,
    "NICAT_AI_PROVIDER": "openai",
    "NICAT_AI_MARKING_ENABLED": False,
    "NICAT_AI_TUTOR_ENABLED": False,
    "NICAT_AI_TUTOR_GENERATION_ENABLED": False,
    "NICAT_AI_FOLLOWUPS_ENABLED": False,
    "REST_FRAMEWORK": {"DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"]},
}


def ids():
    return {check.id for check in nicat_beta_deployment_checks()}


def test_guard_is_noop_outside_production():
    with override_settings(NICAT_BETA_ENV="development", DEBUG=True):
        assert not nicat_beta_deployment_checks()


def test_safe_configuration_has_no_nicat_findings():
    with override_settings(**SAFE):
        assert not ids()


def test_guard_fails_closed_for_insecure_settings():
    bad = dict(SAFE)
    bad.update(DEBUG=True, ALLOWED_HOSTS=["*"], SESSION_COOKIE_SECURE=False,
               CSRF_COOKIE_SECURE=False, SECURE_SSL_REDIRECT=False,
               SECURE_HSTS_SECONDS=0, CORS_ALLOW_ALL_ORIGINS=True,
               DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3"}},
               REST_FRAMEWORK={"DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"]})
    with override_settings(**bad):
        assert {f"nicat.E90{i}" for i in range(1, 10)} <= ids()


def test_mock_ai_is_blocked_in_real_beta():
    with override_settings(**{**SAFE, "NICAT_AI_PROVIDER": "mock", "NICAT_AI_TUTOR_ENABLED": True}):
        assert "nicat.E910" in ids()


def test_unimplemented_live_followups_are_blocked():
    with override_settings(**{**SAFE, "NICAT_AI_FOLLOWUPS_ENABLED": True}):
        assert "nicat.E911" in ids()


def test_live_generation_requires_backend_secret():
    with override_settings(**{**SAFE, "NICAT_AI_MARKING_ENABLED": True, "NICAT_AI_API_KEY": ""}):
        assert "nicat.E912" in ids()
