from django.urls import path
from . import views

urlpatterns = [
    path('question-generation/sources/', views.sources),
    path('question-generation/jobs/', views.jobs),
    path('question-generation/jobs/<uuid:job_id>/', views.job_detail),
    path('question-generation/candidates/<uuid:candidate_id>/edit/', views.candidate_edit),
    path('question-generation/candidates/<uuid:candidate_id>/action/', views.candidate_action),
    path('question-generation/external-authorizations/', views.external_authorization),
]
