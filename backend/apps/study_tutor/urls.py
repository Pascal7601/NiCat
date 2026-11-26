from django.urls import path
from .views import generate_draft, released_explanation

urlpatterns = [
    path("study-tutor/revisions/<uuid:revision_id>/draft/", generate_draft, name="tutor-generate-draft"),
    path("study-tutor/attempts/<uuid:attempt_id>/questions/<uuid:question_id>/explanation/",
         released_explanation, name="tutor-released-explanation"),
]
