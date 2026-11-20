from django.urls import path
from .views import ProgrammeList, ProgrammeCurricula, CurriculumUnits, UnitTopics
urlpatterns = [
    path("programmes/", ProgrammeList.as_view(), name="programmes"),
    path("programmes/<uuid:programme_id>/curricula/", ProgrammeCurricula.as_view(), name="programme-curricula"),
    path("curricula/<uuid:curriculum_id>/units/", CurriculumUnits.as_view(), name="curriculum-units"),
    path("units/<uuid:unit_id>/topics/", UnitTopics.as_view(), name="unit-topics"),
]
