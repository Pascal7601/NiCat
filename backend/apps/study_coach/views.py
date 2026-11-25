"""Student-only follow-up endpoints; no staff-only drafts exposed via API."""
from django.conf import settings
from django.core.exceptions import PermissionDenied
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .models import TutorFollowUp
from .services import (
    CoachConflict, CoachQuotaExceeded, create_followup, daily_limit,
    remaining_for, require_released_item, revision_recommendations,
    student_followup_payload, validate_question,
)


class FollowUpThrottle(ScopedRateThrottle):
    scope = "coach_followups"


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([FollowUpThrottle])
def followups(request, attempt_id, question_id):
    if not (
        getattr(settings, "NICAT_AI_TUTOR_ENABLED", False)
        and getattr(settings, "NICAT_AI_FOLLOWUPS_ENABLED", False)
    ):
        return Response({"code": "disabled"}, status=404)
    try:
        aq = require_released_item(
            student=request.user, attempt_id=attempt_id, question_id=question_id,
        )
    except PermissionDenied:
        # Avoid confirming other students' attempt/question identifiers.
        return Response({"code": "not_found"}, status=404)
    except CoachConflict as exc:
        return Response({"code": "not_released", "message": str(exc)}, status=409)

    if request.method == "POST":
        try:
            question = validate_question(request.data.get("question"))
        except (ValueError, AttributeError):
            return Response({"code": "invalid_question", "message": "Enter a question of 12–500 characters"}, status=400)
        try:
            followup = create_followup(student=request.user, attempt_question=aq, question=question)
        except CoachQuotaExceeded as exc:
            return Response({"code": "quota_exceeded", "message": str(exc)}, status=429)
        except CoachConflict as exc:
            return Response({"code": "not_available", "message": str(exc)}, status=409)
        return Response({
            "id": str(followup.pk), "status": "draft",
            "review_required": True,
            "message": "Your question was submitted for academic review. No answer is published yet.",
            "remaining_today": remaining_for(request.user),
        }, status=201)

    history = TutorFollowUp.objects.filter(
        student=request.user, attempt_question=aq,
    ).select_related(
        "attempt_question__revision__question__topic", "explanation",
    ).prefetch_related("citations__reference__document")[:20]
    return Response({
        "remaining_today": remaining_for(request.user),
        "daily_limit": daily_limit(),
        "items": [student_followup_payload(item) for item in history],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recommendations(request):
    if not getattr(settings, "NICAT_AI_RECOMMENDATIONS_ENABLED", False):
        return Response({"code": "disabled"}, status=404)
    return Response(revision_recommendations(student=request.user))
