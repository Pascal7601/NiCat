from django.urls import path
from . import views

urlpatterns = [
    path("past-papers/", views.papers),
    path("past-papers/<uuid:document_id>/questions/", views.questions),
    path("past-papers/<uuid:document_id>/questions/manual/", views.manual_question),
    path("past-papers/<uuid:document_id>/page/<int:page>/", views.preview_page),
    path("past-papers/<uuid:document_id>/external-authorization/", views.external_authorization),
    path("past-paper-questions/<uuid:question_id>/correct/", views.correct_question),
    path("past-paper-questions/<uuid:question_id>/review/", views.decide_question),
    path("past-paper-questions/<uuid:question_id>/variations/", views.variations),
    path("past-paper-variations/<uuid:candidate_id>/edit/", views.edit_candidate),
    path("past-paper-variations/<uuid:candidate_id>/review/", views.decide_candidate),
]
