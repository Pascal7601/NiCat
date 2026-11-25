"""Separate private staff draft generation from released student explanation reads."""
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.attempts.models import Attempt, AttemptQuestion, GradeItem
from apps.questions.models import QuestionRevision
from .provider import TutorProviderError
from .services import TutorConflict, make_draft, require_academic_reviewer, student_payload


class DraftThrottle(ScopedRateThrottle):
    scope = "tutor_drafts"


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([DraftThrottle])
def generate_draft(request, revision_id):
    try:
        require_academic_reviewer(request.user)
    except PermissionDenied:
        return Response({"code": "forbidden", "message": "Content reviewer permission required"}, status=403)
    if not getattr(settings, "NICAT_AI_TUTOR_GENERATION_ENABLED", False):
        return Response({"code": "disabled", "message": "Tutor draft generation is disabled"}, status=404)
    try:
        explanation, created = make_draft(revision_id=revision_id, actor=request.user)
    except QuestionRevision.DoesNotExist:
        return Response({"code": "not_found"}, status=404)
    except TutorConflict as exc:
        return Response({"code": "no_approved_sources", "message": str(exc)}, status=409)
    except TutorProviderError:
        return Response({"code": "ai_unavailable", "message": "Cannot generate a grounded draft right now"}, status=503)
    return Response({"id": str(explanation.pk), "status": "draft", "version": explanation.version,
                     "review_required": True, "admin_review_path": f"/admin/study_tutor/tutorexplanation/{explanation.pk}/change/"},
                    status=201 if created else 200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def released_explanation(request, attempt_id, question_id):
    if not getattr(settings, "NICAT_AI_TUTOR_ENABLED", False):
        return Response({"code": "disabled"}, status=404)
    # Ownership check first: another student's attempt/question must not be discoverable.
    attempt = get_object_or_404(Attempt.objects.select_related("exam_version"), pk=attempt_id, student=request.user)
    item = get_object_or_404(AttemptQuestion.objects.select_related("revision__question__topic"),
                             pk=question_id, attempt=attempt)
    if (attempt.state != Attempt.State.GRADED_FINAL
            or not attempt.exam_version.show_explanations_after_submit
            or not hasattr(attempt, "grade")
            or not attempt.grade.finalized_at
            or GradeItem.objects.filter(grade=attempt.grade, status=GradeItem.Status.PENDING).exists()):
        return Response({"code": "not_released", "message": "Tutor guidance is unavailable until results are released"}, status=409)
    payload = student_payload(revision=item.revision)
    if payload is None:
        return Response({"code": "under_review", "message": "A reviewer-approved explanation is not available yet"}, status=404)
    return Response(payload)
