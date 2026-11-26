from rest_framework import serializers
from apps.academics.models import Programme, Unit
from .models import DocumentSubmission


class DocumentSubmitSerializer(serializers.Serializer):
    programme_id = serializers.PrimaryKeyRelatedField(queryset=Programme.objects.all(), source="programme")
    unit_id = serializers.PrimaryKeyRelatedField(queryset=Unit.objects.all(), source="unit", required=False, allow_null=True)
    suggested_unit_title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    suggested_unit_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    year_number = serializers.IntegerField(min_value=1, max_value=8, required=False)
    semester_number = serializers.IntegerField(min_value=1, max_value=4, required=False)
    title = serializers.CharField(min_length=5, max_length=180)
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    suggested_topics = serializers.CharField(max_length=350, required=False, allow_blank=True)
    document_type = serializers.ChoiceField(choices=DocumentSubmission.DocumentType.choices)
    rights_basis = serializers.ChoiceField(choices=DocumentSubmission.RightsBasis.choices)
    rights_evidence = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    author_or_owner = serializers.CharField(min_length=2, max_length=180)
    permit_question_generation = serializers.BooleanField(required=True)
    permit_resource_display = serializers.BooleanField(default=False)
    permit_tutor_use = serializers.BooleanField(default=False)

    def validate(self, data):
        if not data.get("permit_question_generation"):
            raise serializers.ValidationError("You must grant explicit permission for question drafting from this file")
        if not data.get("unit") and len(data.get("suggested_unit_title", "").strip()) < 4:
            raise serializers.ValidationError("Select a unit or provide a missing unit name")
        if data.get("rights_basis") != DocumentSubmission.RightsBasis.AUTHOR and len(data.get("rights_evidence", "").strip()) < 25:
            raise serializers.ValidationError("Describe the external owner's license/permission (25+ characters)")
        return data


class StudentDocumentSerializer(serializers.ModelSerializer):
    unit_title = serializers.CharField(source="unit.title", read_only=True, default="")
    programme_title = serializers.CharField(source="programme.name", read_only=True)

    class Meta:
        model = DocumentSubmission
        fields = ("id", "title", "programme_title", "unit_title", "suggested_unit_title", "state",
                  "scan_state", "extraction_state", "possible_duplicate", "created_at")
        read_only_fields = fields
