from rest_framework import serializers
from apps.academics.models import Unit
from .models import Contribution


class SubmitContributionSerializer(serializers.Serializer):
    unit_id = serializers.PrimaryKeyRelatedField(queryset=Unit.objects.all(), source="unit")
    title = serializers.CharField(min_length=5, max_length=160, trim_whitespace=True)
    body = serializers.CharField(min_length=100, max_length=6000, trim_whitespace=True)
    author_declaration = serializers.BooleanField(required=True)
    allow_display = serializers.BooleanField(required=True)
    allow_ai_use = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if attrs.get("author_declaration") is not True or attrs.get("allow_display") is not True:
            raise serializers.ValidationError("You must confirm you wrote these notes and permit review/display")
        return attrs


class StudentContributionSerializer(serializers.ModelSerializer):
    unit_title = serializers.CharField(source="unit.title", read_only=True)

    class Meta:
        model = Contribution
        fields = ["id", "unit_title", "title", "state", "possible_duplicate", "created_at", "updated_at"]
        read_only_fields = fields
