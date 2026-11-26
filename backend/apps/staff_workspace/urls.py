from django.urls import path
from . import views, question_browser

urlpatterns = [
    path("staff/overview/", views.overview),
    path("staff/sources/units/", views.source_units),
    path("staff/sources/documents/", views.documents),
    path("staff/sources/documents/<uuid:document_id>/rights/", views.document_rights),
    path("staff/sources/references/", views.references),
    path("staff/sources/topics/", views.topics),
    path("staff/sources/excerpts/", views.excerpts),
    path("staff/sources/excerpts/<uuid:excerpt_id>/", views.excerpt_detail),
    path("staff/sources/excerpts/<uuid:excerpt_id>/action/", views.excerpt_action),
    path("staff/questions/search/", question_browser.search_questions),
    path("staff/tutor/", views.tutor_list),
    path("staff/tutor/generate/", views.tutor_generate),
    path("staff/tutor/<uuid:explanation_id>/", views.tutor_detail),
    path("staff/tutor/<uuid:explanation_id>/action/", views.tutor_action),
    path("staff/contributions/", views.contribution_list),
    path("staff/contributions/<uuid:contribution_id>/", views.contribution_detail),
    path("staff/contributions/<uuid:contribution_id>/action/", views.contribution_action),
    path("staff/followups/", views.followup_list),
    path("staff/followups/<uuid:followup_id>/", views.followup_detail),
    path("staff/followups/<uuid:followup_id>/action/", views.followup_action),
]
