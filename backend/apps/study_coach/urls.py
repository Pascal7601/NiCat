from django.urls import path
from .views import followups, recommendations

urlpatterns = [
    path(
        "study-coach/attempts/<uuid:attempt_id>/questions/<uuid:question_id>/followups/",
        followups, name="coach-followups",
    ),
    path("study-coach/recommendations/", recommendations, name="coach-recommendations"),
]
