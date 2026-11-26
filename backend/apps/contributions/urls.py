from django.urls import path
from .views import contributions, contribution_detail, contribution_withdraw, units

urlpatterns = [
    path("contributions/units/", units, name="contribution-units"),
    path("contributions/", contributions, name="student-contributions"),
    path("contributions/<uuid:contribution_id>/", contribution_detail, name="student-contribution-detail"),
    path("contributions/<uuid:contribution_id>/withdraw/", contribution_withdraw, name="student-contribution-withdraw"),
]
