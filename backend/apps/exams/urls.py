from django.urls import path
from apps.attempts.views import begin
from .views import ExamList, ExamDetail

urlpatterns = [
    path("exams/", ExamList.as_view(), name="exams"),
    path("exams/<uuid:exam_id>/", ExamDetail.as_view(), name="exam-detail"),
    path("exams/<uuid:exam_id>/attempts/", begin, name="exam-begin"),
]
