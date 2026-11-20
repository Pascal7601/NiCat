"""Restricted grading queue and marking endpoints. Never return private answer keys."""
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import GradeItem, StudentResponse
from .review_serializers import (
    CorrectionSerializer, FirstReviewSerializer, GradeStatusSerializer, PendingQueueSerializer,
)
from .review_services import (
    GradingConflict,
    correct_final_answer,
    require_reviewer,
    review_written_answer,
)


def _authorized(request, *, correction=False):
    try:
        require_reviewer(request.user, correction=correction)
    except PermissionDenied:
        return Response({"code": "forbidden", "message": "Reviewer permission required"}, status=403)
    return None


def _grade_payload(item):
    grade = item.grade
    return {"grade_item_id": str(item.pk), "item_status": item.status,
            "awarded": str(item.marks_awarded) if item.marks_awarded is not None else None,
            "attempt_status": grade.attempt.state,
            "scored_marks": str(grade.scored_marks),
            "scored_possible_marks": str(grade.scored_possible_marks),
            "ungraded_possible_marks": str(grade.ungraded_possible_marks),
            "final_percentage": str(grade.final_percentage) if grade.final_percentage is not None else None}


@extend_schema(responses={200: PendingQueueSerializer}, description="Privileged queue of pending written answers. Requires staff reviewer permission.")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def review_queue(request):
    if (denied := _authorized(request)) is not None:
        return denied
    try:
        limit = max(1, min(100, int(request.query_params.get("limit", "20"))))
    except (TypeError, ValueError):
        return Response({"code": "invalid_limit", "message": "Limit must be an integer"}, status=400)
    items = list(GradeItem.objects.filter(status=GradeItem.Status.PENDING)
                 .select_related("grade__attempt__student", "attempt_question__revision")
                 .order_by("grade__attempt__submitted_at", "pk")[:limit])
    response_ids = [item.attempt_question_id for item in items]
    answers = {response.attempt_question_id: response.text_answer for response in
               StudentResponse.objects.filter(attempt_question_id__in=response_ids)}
    return Response({"count": len(items), "items": [{
        "grade_item_id": str(item.id), "attempt_id": str(item.grade.attempt_id),
        "question_id": str(item.attempt_question_id),
        "prompt": item.attempt_question.public_snapshot["prompt"],
        "kind": item.attempt_question.public_snapshot["kind"],
        "possible_marks": str(item.possible_marks),
        "response": answers.get(item.attempt_question_id, ""),
        "reviewer_rubric": item.attempt_question.private_key_snapshot.get("rubric", []),
    } for item in items]})


def _error(exc):
    if isinstance(exc, GradeItem.DoesNotExist):
        raise Http404("Grade item not found")
    if isinstance(exc, GradingConflict):
        return Response({"code": "grade_conflict", "message": str(exc)}, status=409)
    if isinstance(exc, DjangoValidationError):
        return Response({"code": "validation_error", "message": "; ".join(exc.messages)}, status=400)
    raise exc


@extend_schema(request=FirstReviewSerializer, responses={200: GradeStatusSerializer},
               description="First and finalizable reviewer mark. Audited and transactional.")
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def first_review(request, item_id):
    if (denied := _authorized(request)) is not None:
        return denied
    serializer = FirstReviewSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        item = review_written_answer(
            item_id=item_id,
            actor=request.user,
            marks=serializer.validated_data["marks_awarded"],
            rationale=serializer.validated_data["rationale"],
            student_feedback=serializer.validated_data["student_feedback"],
        )
    except (GradeItem.DoesNotExist, GradingConflict, DjangoValidationError) as exc:
        return _error(exc)
    item.refresh_from_db()
    return Response(_grade_payload(item), status=status.HTTP_200_OK)


@extend_schema(request=CorrectionSerializer, responses={200: GradeStatusSerializer},
               description="Audit-only final grade correction with separate permission.")
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def correction(request, item_id):
    if (denied := _authorized(request, correction=True)) is not None:
        return denied
    serializer = CorrectionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        item = correct_final_answer(
            item_id=item_id,
            actor=request.user,
            marks=serializer.validated_data["marks_awarded"],
            reason=serializer.validated_data["reason"],
            student_feedback=serializer.validated_data.get(
                "student_feedback"
            ),
        )

    except (GradeItem.DoesNotExist, GradingConflict, DjangoValidationError) as exc:
        return _error(exc)
    item.refresh_from_db()
    return Response(_grade_payload(item), status=status.HTTP_200_OK)
