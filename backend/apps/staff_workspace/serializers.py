from rest_framework import serializers
from apps.academics.models import Topic, Unit
from apps.resources.models import SourceDocument, SourceReference
from apps.study_tutor.models import SourceExcerpt


class DocumentCreateSerializer(serializers.Serializer):
    title = serializers.CharField(min_length=5, max_length=500)
    unit_id = serializers.PrimaryKeyRelatedField(queryset=Unit.objects.all(), source="unit")
    source_kind = serializers.ChoiceField(choices=SourceDocument.Kind.choices)
    source_url = serializers.URLField(max_length=1000, required=False, allow_blank=True)
    notes = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class RightsDecisionSerializer(serializers.Serializer):
    rights_status = serializers.ChoiceField(choices=[SourceDocument.Rights.ALLOWED, SourceDocument.Rights.RESTRICTED])
    rationale = serializers.CharField(min_length=30, max_length=4000, trim_whitespace=True)


class ReferenceCreateSerializer(serializers.Serializer):
    document_id = serializers.PrimaryKeyRelatedField(queryset=SourceDocument.objects.all(), source="document")
    page_label = serializers.CharField(max_length=80, required=False, allow_blank=True)
    section_label = serializers.CharField(max_length=200, required=False, allow_blank=True)


class ExcerptCreateSerializer(serializers.Serializer):
    reference_id = serializers.PrimaryKeyRelatedField(queryset=SourceReference.objects.all(), source="reference")
    topic_id = serializers.PrimaryKeyRelatedField(queryset=Topic.objects.all(), source="topic")
    text = serializers.CharField(min_length=30, max_length=5000)


class NoteSerializer(serializers.Serializer):
    note = serializers.CharField(min_length=15, max_length=4000, trim_whitespace=True)


class TutorDraftEditSerializer(serializers.Serializer):
    explanation = serializers.CharField(min_length=30, max_length=5000)
    common_mistake = serializers.CharField(min_length=10, max_length=1500)
    practice_tip = serializers.CharField(min_length=10, max_length=1500)


class FollowupAnswerSerializer(serializers.Serializer):
    draft_answer = serializers.CharField(min_length=50, max_length=4000, trim_whitespace=True)


class ActionSerializer(serializers.Serializer):
    action = serializers.CharField(min_length=3, max_length=32)
