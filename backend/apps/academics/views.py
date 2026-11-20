from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import NotFound
from django.shortcuts import get_object_or_404
from .models import CurriculumVersion, CurriculumUnit, Programme, Topic, Unit
from .serializers import ProgrammeSerializer, CurriculumUnitSerializer, TopicSerializer, CurriculumVersionSerializer

class ProgrammeList(ListAPIView):
    queryset = Programme.objects.select_related("university").order_by("name")
    permission_classes = [AllowAny]
    serializer_class = ProgrammeSerializer

class CurriculumUnits(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CurriculumUnitSerializer
    def get_queryset(self):
        get_object_or_404(CurriculumVersion, pk=self.kwargs["curriculum_id"])
        return CurriculumUnit.objects.filter(curriculum_version_id=self.kwargs["curriculum_id"]).select_related("unit")

class UnitTopics(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TopicSerializer
    def get_queryset(self):
        get_object_or_404(Unit, pk=self.kwargs["unit_id"])
        return Topic.objects.filter(unit_id=self.kwargs["unit_id"])


class ProgrammeCurricula(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CurriculumVersionSerializer

    def get_queryset(self):
        get_object_or_404(Programme, pk=self.kwargs["programme_id"])
        return CurriculumVersion.objects.filter(programme_id=self.kwargs["programme_id"]).order_by("label")
