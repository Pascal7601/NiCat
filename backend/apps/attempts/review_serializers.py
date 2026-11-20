"""Reviewer-only request schemas. Decimal scores prevent float rounding errors."""
from decimal import Decimal

from rest_framework import serializers



class FirstReviewSerializer(serializers.Serializer):
    marks_awarded = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )
    rationale = serializers.CharField(
        min_length=10,
        max_length=5000,
        trim_whitespace=True,
    )
    student_feedback = serializers.CharField(
        min_length=10,
        max_length=2000,
        trim_whitespace=True,
    )


class CorrectionSerializer(serializers.Serializer):
    marks_awarded = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )
    reason = serializers.CharField(
        min_length=15,
        max_length=5000,
        trim_whitespace=True,
    )
    student_feedback = serializers.CharField(
        min_length=10,
        max_length=2000,
        trim_whitespace=True,
        required=False,
    )



class GradeStatusSerializer(serializers.Serializer):
    grade_item_id = serializers.UUIDField()
    item_status = serializers.CharField()
    awarded = serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True)
    attempt_status = serializers.CharField()
    scored_marks = serializers.DecimalField(max_digits=8, decimal_places=2)
    scored_possible_marks = serializers.DecimalField(max_digits=8, decimal_places=2)
    ungraded_possible_marks = serializers.DecimalField(max_digits=8, decimal_places=2)
    final_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)


class ReviewerRubricSerializer(serializers.Serializer):
    criterion = serializers.CharField()
    max_marks = serializers.CharField()


class PendingAnswerSerializer(serializers.Serializer):
    grade_item_id = serializers.UUIDField()
    attempt_id = serializers.UUIDField()
    question_id = serializers.UUIDField()
    prompt = serializers.CharField()
    kind = serializers.CharField()
    possible_marks = serializers.DecimalField(max_digits=6, decimal_places=2)
    response = serializers.CharField(allow_blank=True)
    reviewer_rubric = ReviewerRubricSerializer(many=True)


class PendingQueueSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    items = PendingAnswerSerializer(many=True)
