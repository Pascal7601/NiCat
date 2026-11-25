"""Owner-filtered student intake and explicit staff review. No file download route."""
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, parser_classes, permission_classes, throttle_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework import serializers

from apps.academics.models import Programme, CurriculumVersion, CurriculumUnit, Unit
from .models import DocumentSubmission
from .serializers import DocumentSubmitSerializer, StudentDocumentSerializer
from .services import (
    IntakeConflict, IntakeQuotaExceeded, create_and_map_verified_unit,
    review_document, submit_document, withdraw_document,
)


class DocumentThrottle(ScopedRateThrottle):
    scope = "document_uploads"

    def allow_request(self, request, view):
        if request.method != "POST":
            return True
        return super().allow_request(request, view)


def _enabled():
    return bool(getattr(settings, "NICAT_DOCUMENT_INTAKE_ENABLED", False))


def _staff(user):
    return (user.is_active and user.is_staff and any(user.has_perm(f"document_intake.{code}") for code in
            ("review_document_rights", "review_document_academic", "map_document_units")))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def programmes(request):
    if not _enabled():
        return Response({"code": "disabled"}, status=404)
    values = Programme.objects.select_related("university").order_by("university__name", "name")[:200]
    return Response({"items": [{"id": str(p.pk), "name": p.name, "university": p.university.name} for p in values]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def programme_units(request, programme_id):
    if not _enabled():
        return Response({"code": "disabled"}, status=404)
    get_object_or_404(Programme, pk=programme_id)
    ids = CurriculumUnit.objects.filter(curriculum_version__programme_id=programme_id).values_list("unit_id", flat=True)
    units = Unit.objects.filter(pk__in=ids).order_by("title")[:300]
    versions = CurriculumVersion.objects.filter(programme_id=programme_id).order_by("label", "pk")[:50]
    return Response({
        "items": [{"id": str(u.pk), "title": u.title} for u in units],
        "curriculum_versions": [{"id": str(v.pk), "label": v.label} for v in versions],
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
@throttle_classes([DocumentThrottle])
def student_documents(request):
    if not _enabled():
        return Response({"code": "disabled"}, status=404)
    if request.method == "GET":
        items = DocumentSubmission.objects.filter(student=request.user).select_related("unit", "programme")[:50]
        return Response({"items": StudentDocumentSerializer(items, many=True).data})
    serializer = DocumentSubmitSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    upload = request.FILES.get("file")
    if upload is None:
        return Response({"code": "missing_file", "message": "Choose a PDF or TXT file"}, status=400)
    limit = max(1, min(8 * 1024 * 1024, int(getattr(settings, "NICAT_DOCUMENT_MAX_BYTES", 8 * 1024 * 1024))))
    if upload.size == 0 or upload.size > limit:
        return Response({"code": "bad_size", "message": "File is empty or exceeds the configured upload size"}, status=413)
    try:
        entry = submit_document(student=request.user, file=upload, validated=serializer.validated_data)
    except IntakeQuotaExceeded as exc:
        return Response({"code": "quota_exceeded", "message": str(exc)}, status=429)
    except (IntakeConflict, ValidationError, OSError) as exc:
        return Response({"code": "invalid_document", "message": str(exc)}, status=400)
    return Response(StudentDocumentSerializer(entry).data, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def student_withdraw(request, document_id):
    if not _enabled():
        return Response({"code": "disabled"}, status=404)
    try:
        entry = withdraw_document(document_id=document_id, student=request.user)
    except PermissionDenied:
        return Response({"code": "not_found"}, status=404)
    return Response({"id": str(entry.pk), "state": entry.state})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def staff_documents(request):
    if not _enabled():
        return Response({"code": "disabled"}, status=404)
    if not _staff(request.user):
        return Response({"code": "forbidden"}, status=403)
    items = DocumentSubmission.objects.select_related("student", "programme", "unit")[:100]
    return Response({"items": [
        {"id": str(i.pk), "title": i.title, "programme": i.programme.name,
         "unit": i.unit.title if i.unit_id else i.suggested_unit_title,
         "state": i.state, "scan_state": i.scan_state, "possible_duplicate": i.possible_duplicate}
        for i in items
    ]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def staff_detail(request, document_id):
    if not _enabled():
        return Response({"code": "disabled"}, status=404)
    if not _staff(request.user):
        return Response({"code": "forbidden"}, status=403)
    i = get_object_or_404(DocumentSubmission.objects.select_related("student", "programme", "unit"), pk=document_id)
    return Response({"id": str(i.pk), "title": i.title, "programme": i.programme.name,
       "programme_id": str(i.programme_id), "unit": i.unit.title if i.unit_id else "", "suggested_unit_title": i.suggested_unit_title,
       "suggested_unit_code": i.suggested_unit_code,
       "year_number": i.year_number, "semester_number": i.semester_number,
       "document_type": i.document_type, "source_owner": i.author_or_owner, "rights_basis": i.rights_basis,
       "rights_evidence": i.rights_evidence, "description": i.description, "suggested_topics": i.suggested_topics,
       "size_bytes": i.size_bytes, "original_filename": i.original_filename,
       "state": i.state, "scan_state": i.scan_state, "extraction_state": i.extraction_state,
       "possible_duplicate": i.possible_duplicate, "rights_cleared": bool(i.rights_reviewed_by_id),
       "academic_approved": bool(i.academic_reviewed_by_id),
       "permit_question_generation": i.permit_question_generation,
       "permit_resource_display": i.permit_resource_display, "permit_tutor_use": i.permit_tutor_use,
       "extracted_preview": i.extracted_text[:5000] if i.scan_state == i.ScanState.CLEAN else "",
       "events": [{"action": e.action, "rationale": e.rationale, "created_at": e.created_at.isoformat()} for e in i.events.all()[:30]]})


class ReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("rights_clear", "rights_hold", "academic_approve", "reject", "map_unit"))
    rationale = serializers.CharField(min_length=25, max_length=2000)
    unit_id = serializers.PrimaryKeyRelatedField(queryset=Unit.objects.all(), source="unit", required=False)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def staff_review(request, document_id):
    if not _enabled():
        return Response({"code": "disabled"}, status=404)
    if not _staff(request.user):
        return Response({"code": "forbidden"}, status=403)
    serializer = ReviewSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        entry = review_document(document_id=document_id, actor=request.user, **serializer.validated_data)
    except DocumentSubmission.DoesNotExist:
        return Response({"code": "not_found"}, status=404)
    except PermissionDenied:
        return Response({"code": "forbidden"}, status=403)
    except IntakeConflict as exc:
        return Response({"code": "review_conflict", "message": str(exc)}, status=409)
    return Response({"id": str(entry.pk), "state": entry.state})


class VerifiedUnitSerializer(serializers.Serializer):
    curriculum_version_id = serializers.PrimaryKeyRelatedField(
        queryset=CurriculumVersion.objects.all(), source="curriculum_version"
    )
    title = serializers.CharField(min_length=4, max_length=200)
    year_number = serializers.IntegerField(min_value=1, max_value=8)
    semester_number = serializers.IntegerField(min_value=1, max_value=4)
    rationale = serializers.CharField(min_length=25, max_length=1500)
    catalogue_verified = serializers.BooleanField(required=True)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def staff_create_and_map_unit(request, document_id):
    """Explicit academic catalogue action; students may never create verified units."""
    if not _enabled():
        return Response({"code": "disabled"}, status=404)
    serializer = VerifiedUnitSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        entry, created = create_and_map_verified_unit(
            document_id=document_id, actor=request.user, **serializer.validated_data
        )
    except DocumentSubmission.DoesNotExist:
        return Response({"code": "not_found"}, status=404)
    except PermissionDenied:
        return Response({"code": "forbidden"}, status=403)
    except CurriculumVersion.DoesNotExist:
        return Response({"code": "bad_curriculum"}, status=400)
    except (IntakeConflict, ValidationError) as exc:
        return Response({"code": "catalogue_conflict", "message": str(exc)}, status=409)
    return Response({
        "id": str(entry.pk), "unit_id": str(entry.unit_id),
        "unit_created": created, "state": entry.state,
    })
