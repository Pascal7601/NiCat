from django.apps import AppConfig


class BetaGuardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.beta_guard"
    verbose_name = "NiCat Beta Security Checks"

    def ready(self):
        # Register deployment-only checks; never query the DB during app startup.
        from . import checks  # noqa: F401
