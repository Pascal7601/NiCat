"""Public-facing exam catalogue without answer keys or unpublished versions."""
from uuid import UUID
from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from .models import ExamVersion


class ExamListSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="template.title", read_only=True)
    unit_id = serializers.UUIDField(source="template.unit_id", read_only=True)

    class Meta:
        model = ExamVersion
        fields = ("id", "title", "unit_id", "duration_seconds", "instructions")


class ExamList(generics.ListAPIView):
    serializer_class = ExamListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ExamVersion.objects.filter(is_published=True, template__is_active=True).select_related("template")
        unit_id = self.request.query_params.get("unit_id")
        if unit_id:
            try:
                unit_id = UUID(unit_id)
            except (ValueError, AttributeError):
                raise ValidationError({"unit_id": "Expected a UUID"})
            qs = qs.filter(template__unit_id=unit_id)
        return qs.order_by("template__title", "-number")


class ExamDetail(generics.RetrieveAPIView):
    serializer_class = ExamListSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "exam_id"
    queryset = ExamVersion.objects.filter(is_published=True, template__is_active=True).select_related("template")
