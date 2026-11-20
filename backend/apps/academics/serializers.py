from rest_framework import serializers
from .models import CurriculumUnit, CurriculumVersion, Programme, Topic

class ProgrammeSerializer(serializers.ModelSerializer):
    university_name = serializers.CharField(source="university.name", read_only=True)
    class Meta:
        model = Programme
        fields = ("id", "name", "code", "university_name")

class CurriculumUnitSerializer(serializers.ModelSerializer):
    unit_id = serializers.UUIDField(source="unit.id", read_only=True)
    unit_name = serializers.CharField(source="unit.title", read_only=True)
    class Meta:
        model = CurriculumUnit
        fields = ("id", "unit_id", "unit_name", "year_number", "semester_number", "displayed_code", "code_verification_status")

class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ("id", "parent_id", "title", "position")


class CurriculumVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurriculumVersion
        fields = ("id", "label", "is_officially_verified", "reference_url")
