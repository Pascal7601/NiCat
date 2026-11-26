"""AI proposals can only be requested/read by authorized human reviewers."""
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from apps.attempts.models import GradeItem
from apps.attempts.review_services import GradingConflict, require_reviewer

from .models import AIMarkingSuggestion
from .provider import AIProviderError
from .services import proposal_payload, propose_written_mark


class AIMarkingThrottle(UserRateThrottle):
    scope = "ai_marking"


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([AIMarkingThrottle])
def marking_suggestion(request, item_id):
    try:
        require_reviewer(request.user)
    except PermissionDenied:
        return Response({"detail": "Reviewer permission required"}, status=403)
    if not settings.NICAT_AI_MARKING_ENABLED:
        raise Http404("AI marking is disabled")
    if request.method == "GET":
        suggestion = AIMarkingSuggestion.objects.filter(grade_item_id=item_id).first()
        if suggestion is None:
            raise Http404("No marking proposal exists")
        return Response(proposal_payload(suggestion))
    if request.data:
        return Response({"detail": "This endpoint does not accept client-supplied prompts"}, status=400)
    try:
        suggestion, created = propose_written_mark(item_id=item_id, actor=request.user)
    except GradeItem.DoesNotExist:
        raise Http404("Grade item not found")
    except GradingConflict as exc:
        return Response({"detail": str(exc)}, status=409)
    except AIProviderError:
        return Response({"detail": "AI marking is temporarily unavailable"}, status=503)
    return Response(proposal_payload(suggestion), status=201 if created else 200)
