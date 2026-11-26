"""Authenticated student intake; no published source or staff review payloads."""
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, parser_classes, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from apps.academics.models import Unit
from .models import Contribution
from .serializers import SubmitContributionSerializer, StudentContributionSerializer
from .services import ContributionConflict, ContributionQuotaExceeded, submit, withdraw


class ContributionThrottle(ScopedRateThrottle):
    scope = "contribution_submissions"

    def allow_request(self, request, view):
        if request.method != "POST":
            return True
        return super().allow_request(request, view)


def _enabled():
    return bool(getattr(settings, "NICAT_CONTRIBUTIONS_ENABLED", False))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def units(request):
    if not _enabled():
        return Response({"code": "disabled"}, status=404)
    return Response({"items": [{"id": str(u.pk), "title": u.title} for u in Unit.objects.order_by("title")[:200]]})


@api_view(["GET", "POST"])
@parser_classes([JSONParser])
@permission_classes([IsAuthenticated])
@throttle_classes([ContributionThrottle])
def contributions(request):
    if not _enabled():
        return Response({"code": "disabled"}, status=404)
    if request.method == "GET":
        entries = Contribution.objects.filter(student=request.user).select_related("unit")[:50]
        return Response({"items": StudentContributionSerializer(entries, many=True).data})
    serializer = SubmitContributionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        entry = submit(student=request.user, **serializer.validated_data)
    except ContributionQuotaExceeded as exc:
        return Response({"code": "quota_exceeded", "message": str(exc)}, status=429)
    except (ContributionConflict, ValidationError) as exc:
        return Response({"code": "invalid_contribution", "message": str(exc)}, status=400)
    return Response(StudentContributionSerializer(entry).data, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def contribution_detail(request, contribution_id):
    if not _enabled():
        return Response({"code": "disabled"}, status=404)
    entry = get_object_or_404(Contribution.objects.select_related("unit"), pk=contribution_id, student=request.user)
    return Response(StudentContributionSerializer(entry).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def contribution_withdraw(request, contribution_id):
    if not _enabled():
        return Response({"code": "disabled"}, status=404)
    # Ownership is enforced here and independently in the service.
    entry = get_object_or_404(Contribution, pk=contribution_id, student=request.user)
    try:
        entry = withdraw(contribution_id=entry.pk, actor=request.user)
    except (ContributionConflict, PermissionDenied):
        return Response({"code": "not_found"}, status=404)
    return Response({"id": str(entry.pk), "state": entry.state})
