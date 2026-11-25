from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.common.views import health, readiness

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.academics.urls")),
    path("api/v1/", include("apps.exams.urls")),
    path("api/v1/", include("apps.attempts.urls")),
    path(
    "_internal/ready/",
    readiness,
    name="readiness",
    ),
    path("api/v1/", include("apps.study_tutor.urls")),
    path("api/v1/", include("apps.ai_tutor.urls")),
    path("api/v1/", include("apps.study_coach.urls")),
    path("api/v1/", include("apps.contributions.urls")),
    path("api/v1/", include("apps.staff_workspace.urls")),
    path("api/v1/", include("apps.document_intake.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
