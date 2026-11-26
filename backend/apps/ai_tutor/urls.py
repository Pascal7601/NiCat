from django.urls import path

from .views import marking_suggestion

urlpatterns = [
    path("review/grade-items/<uuid:item_id>/ai-suggestion/", marking_suggestion, name="ai-marking-suggestion"),
]
