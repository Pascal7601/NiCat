from django.urls import path
from . import views

urlpatterns = [
    path("document-intake/programmes/", views.programmes),
    path("document-intake/programmes/<uuid:programme_id>/units/", views.programme_units),
    path("document-intake/", views.student_documents),
    path("document-intake/<uuid:document_id>/withdraw/", views.student_withdraw),
    path("document-intake/staff/", views.staff_documents),
    path("document-intake/staff/<uuid:document_id>/", views.staff_detail),
    path("document-intake/staff/<uuid:document_id>/review/", views.staff_review),
]
