from django.urls import path
from . import views, review_views
urlpatterns = [
    path("review/pending/", review_views.review_queue, name="review-pending"),
    path("review/grade-items/<uuid:item_id>/mark/", review_views.first_review, name="review-grade-mark"),
    path("review/grade-items/<uuid:item_id>/correct/", review_views.correction, name="review-grade-correct"),
    path("attempts/<uuid:attempt_id>/", views.detail, name="attempt-detail"),
    path("attempts/<uuid:attempt_id>/responses/<uuid:question_id>/", views.save, name="attempt-save"),
    path("attempts/<uuid:attempt_id>/submit/", views.submit, name="attempt-submit"),
    path("attempts/<uuid:attempt_id>/result/", views.result, name="attempt-result"),
    path("me/attempts/", views.history, name="attempt-history"),
]
