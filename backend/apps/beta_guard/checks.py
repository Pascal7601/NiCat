"""NiCat-specific production deployment checks.

Django's built-in `check --deploy` must also pass. These checks do NOT prove
application security or substitute for penetration testing and code review.
Run with NICAT_BETA_ENV=production, using the production Django settings module.
"""
from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def nicat_beta_deployment_checks(app_configs=None, **kwargs):
    if getattr(settings, "NICAT_BETA_ENV", "development") != "production":
        return []

    problems = []

    def fail(code, message, hint):
        problems.append(Error(message, hint=hint, id=f"nicat.{code}"))

    if settings.DEBUG:
        fail("E901", "Production beta must not run with DEBUG=True.", "Set DEBUG=False using the production settings module.")

    hosts = getattr(settings, "ALLOWED_HOSTS", [])
    if not hosts or "*" in hosts:
        fail("E902", "ALLOWED_HOSTS must be an explicit list of beta hostnames.", "Remove wildcards; specify exact API hostnames.")

    db = settings.DATABASES.get("default", {})
    if db.get("ENGINE") != "django.db.backends.postgresql":
        fail("E903", "Production beta requires PostgreSQL.", "Use a backed-up PostgreSQL database, not the local SQLite fallback.")

    if not getattr(settings, "SESSION_COOKIE_SECURE", False):
        fail("E904", "Django admin session cookies must be Secure.", "Set SESSION_COOKIE_SECURE=True.")
    if not getattr(settings, "CSRF_COOKIE_SECURE", False):
        fail("E905", "Django CSRF cookies must be Secure.", "Set CSRF_COOKIE_SECURE=True.")
    if not getattr(settings, "SECURE_SSL_REDIRECT", False):
        fail("E906", "Django must require HTTPS.", "Set SECURE_SSL_REDIRECT=True and configure your trusted TLS proxy correctly.")
    if not getattr(settings, "SECURE_HSTS_SECONDS", 0):
        fail("E907", "HSTS must be explicitly configured for the beta hostname.",
             "Start with a short HSTS interval after confirming end-to-end HTTPS; increase gradually. Don't enable includeSubDomains/preload casually.")

    if getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False):
        fail("E908", "Wildcard CORS must not be enabled in beta.", "List exact trusted origins if cross-origin traffic is unavoidable.")

    permissions = settings.REST_FRAMEWORK.get("DEFAULT_PERMISSION_CLASSES", [])
    if "rest_framework.permissions.IsAuthenticated" not in permissions:
        fail("E909", "Default API permissions must deny anonymous users.",
             "Keep IsAuthenticated as the DRF default; explicitly whitelist intended public endpoints.")

    provider = getattr(settings, "NICAT_AI_PROVIDER", "openai").lower()
    ai_visible = any(getattr(settings, flag, False) for flag in (
        "NICAT_AI_MARKING_ENABLED", "NICAT_AI_TUTOR_ENABLED",
        "NICAT_AI_TUTOR_GENERATION_ENABLED", "NICAT_AI_FOLLOWUPS_ENABLED",
    ))
    if provider == "mock" and ai_visible:
        fail("E910", "Mock AI mode must not be exposed in a real-student beta.",
             "Use a non-mock, independently evaluated provider or disable AI features and prevent access to all mock data.")
    if provider == "openai" and any(getattr(settings, name, False) for name in (
        "NICAT_AI_MARKING_ENABLED", "NICAT_AI_TUTOR_GENERATION_ENABLED"
    )) and not getattr(settings, "NICAT_AI_API_KEY", ""):
        fail("E912", "An enabled live AI generation feature has no server-side API key.",
             "Set the supported provider key in the server-side secret store, or turn generation off.")
    if getattr(settings, "NICAT_AI_FOLLOWUPS_ENABLED", False) and provider != "mock":
        # Sprint 8's create_followup currently rejects all non-mock providers.
        fail("E911", "Sprint 8 follow-up generation does not support a live provider.",
             "Disable follow-up submissions for the real beta or implement and test a safe, budgeted provider first.")

    return problems
