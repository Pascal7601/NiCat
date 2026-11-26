"""Small, explicit staff-only JSON endpoints. Raw PDF is never served publicly."""
import base64
import hashlib
import io

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.academics.models import Topic
from apps.document_intake.models import DocumentSubmission
from apps.document_intake.storage import private_path
from .models import PaperQuestionDraft, PaperReviewEvent, PaperVariationJob, PaperVariationCandidate
from .services import (
    PaperConflict, require_staff, is_eligible_paper, extract_question_drafts,
    add_manual_question, update_question, review_question, queue_variations,
    edit_variation, review_variation, authorize_paper_external,
)


def _enabled():
    if not getattr(settings, "NICAT_PAST_PAPERS_ENABLED", False):
        raise Http404("Not enabled")


def _reader(user):
    perms = (
        "past_papers.extract_paper_questions", "past_papers.verify_paper_questions",
        "past_papers.request_paper_variations", "past_papers.review_paper_variations",
        "question_generation.approve_external_question_ai",
    )
    if not user.is_authenticated or not user.is_active or not user.is_staff or not any(user.has_perm(p) for p in perms):
        raise PermissionDenied("Past-paper review staff only")


def _response_error(exc):
    if isinstance(exc, PermissionDenied):
        return Response({"code": "forbidden"}, status=403)
    if isinstance(exc, PaperConflict):
        return Response({"code": "conflict", "message": str(exc)}, status=409)
    return Response({"code": "not_found"}, status=404)


def _question(q):
    return dict(
        id=str(q.pk), document_id=str(q.document_id), position=q.position,
        original_ocr_text=q.original_ocr_text, corrected_text=q.corrected_text,
        page_number=q.page_number, marks=(str(q.marks) if q.marks is not None else None),
        topic_id=str(q.topic_id) if q.topic_id else None,
        verified_answer_context=q.verified_answer_context, flags=q.flags,
        state=q.state, extracted_by_id=str(q.extracted_by_id),
        verified_by_id=str(q.verified_by_id) if q.verified_by_id else None,
    )


def _candidate(c):
    return dict(id=str(c.pk), state=c.state, kind=c.kind, position=c.position,
                prompt=c.prompt, options=c.options, correct_index=c.correct_index,
                explanation=c.explanation, rubric=c.rubric, evidence_quote=c.evidence_quote,
                validation_errors=c.validation_errors, review_note=c.review_note)


class TextCorrection(serializers.Serializer):
    corrected_text = serializers.CharField(min_length=15, max_length=2000)
    page_number = serializers.IntegerField(min_value=1, max_value=80)
    topic_id = serializers.UUIDField()
    marks = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    verified_answer_context = serializers.CharField(max_length=3500, required=False, allow_blank=True)
    rationale = serializers.CharField(min_length=25, max_length=2500)


class ManualQuestion(serializers.Serializer):
    text = serializers.CharField(min_length=15, max_length=2000)
    page_number = serializers.IntegerField(min_value=1, max_value=80)


class QuestionDecision(serializers.Serializer):
    action = serializers.ChoiceField(choices=("verify", "reject"))
    rationale = serializers.CharField(min_length=25, max_length=2500)
    compared_with_original = serializers.BooleanField(default=False)


class VariationRequest(serializers.Serializer):
    count = serializers.IntegerField(min_value=1, max_value=3)
    kind = serializers.ChoiceField(choices=("mcq", "short", "essay"))
    difficulty = serializers.ChoiceField(choices=("easy", "medium", "hard"))


class VariationDecision(serializers.Serializer):
    action = serializers.ChoiceField(choices=("approve", "reject"))
    rationale = serializers.CharField(min_length=25, max_length=2500)


class VariationEdit(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("mcq", "short", "essay"))
    prompt = serializers.CharField(min_length=15, max_length=1600)
    options = serializers.ListField(child=serializers.CharField(max_length=350), allow_empty=True)
    correct_index = serializers.IntegerField(min_value=0, max_value=3, required=False, allow_null=True)
    explanation = serializers.CharField(min_length=20, max_length=4000)
    rubric = serializers.ListField(child=serializers.DictField(), allow_empty=True)
    evidence_quote = serializers.CharField(min_length=15, max_length=650)
    rationale = serializers.CharField(min_length=25, max_length=2500)


class VendorReview(serializers.Serializer):
    rationale = serializers.CharField(min_length=40, max_length=2500)
    revoke = serializers.BooleanField(default=False)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def papers(request):
    _enabled()
    _reader(request.user)
    docs = DocumentSubmission.objects.filter(
        document_type=DocumentSubmission.DocumentType.AUTHORIZED_PAPER,
        state=DocumentSubmission.State.APPROVED,
        scan_state=DocumentSubmission.ScanState.CLEAN,
        extraction_state=DocumentSubmission.ExtractionState.DONE,
    ).select_related("programme", "unit").order_by("-created_at")[:100]
    docs = [doc for doc in docs if is_eligible_paper(doc)]
    ids = [d.unit_id for d in docs]
    topics = Topic.objects.filter(unit_id__in=ids).order_by("title")[:500]
    return Response(dict(items=[dict(id=str(d.pk), title=d.title, unit=d.unit.title,
                                     programme=d.programme.name, page_count=d.page_count,
                                     extracted_length=len(d.extracted_text), state=d.state,
                                     can_generate=bool(d.permit_question_generation)) for d in docs],
                         topics=[dict(id=str(t.pk), unit_id=str(t.unit_id), title=t.title) for t in topics],
                         unit_ids={str(d.pk):str(d.unit_id) for d in docs},
                         provider=getattr(settings, "NICAT_QUESTION_AI_PROVIDER", "mock")))


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def questions(request, document_id):
    _enabled()
    _reader(request.user)
    doc = get_object_or_404(DocumentSubmission, pk=document_id)
    if not is_eligible_paper(doc):
        return Response({"code": "not_eligible"}, status=409)
    if request.method == "POST":
        try:
            count = extract_question_drafts(document_id=document_id, actor=request.user)
        except (PaperConflict, PermissionDenied) as exc:
            return _response_error(exc)
        return Response({"created": count}, status=201)
    values = PaperQuestionDraft.objects.filter(document=doc).order_by("position")[:100]
    events = PaperReviewEvent.objects.filter(document=doc).select_related("actor")[:60]
    return Response(dict(items=[_question(v) for v in values], events=[
        dict(action=e.action, rationale=e.rationale, created_at=e.created_at.isoformat()) for e in events
    ]))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def manual_question(request, document_id):
    _enabled()
    ser = ManualQuestion(data=request.data)
    ser.is_valid(raise_exception=True)
    try:
        q = add_manual_question(document_id=document_id, actor=request.user, **ser.validated_data)
    except DocumentSubmission.DoesNotExist:
        return Response({"code": "not_found"}, status=404)
    except (PaperConflict, PermissionDenied) as exc:
        return _response_error(exc)
    return Response(_question(q), status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def preview_page(request, document_id, page):
    _enabled()
    _reader(request.user)
    doc = get_object_or_404(DocumentSubmission, pk=document_id)
    if not is_eligible_paper(doc):
        return Response({"code": "not_eligible"}, status=409)
    if not 1 <= page <= doc.page_count:
        return Response({"code": "invalid_page"}, status=400)
    path = private_path(doc.stored_key)
    try:
        if path.stat().st_size != doc.size_bytes:
            return Response({"code": "source_changed"}, status=409)
        # Check original bytes, not just a database checksum. Size bounded at upload.
        digest = hashlib.sha256()
        with path.open("rb") as f:
            while chunk := f.read(64 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != doc.sha256:
            return Response({"code": "source_changed"}, status=409)
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(str(path))
        try:
            if len(pdf) != doc.page_count:
                return Response({"code": "page_count_changed"}, status=409)
            p = pdf[page - 1]
            try:
                width, height = p.get_size()
                if min(width, height) <= 0 or max(width, height) > 100000:
                    return Response({"code": "unsafe_page_dimensions"}, status=409)
                # Cap rendered pixels to limit memory use on oversized PDF pages.
                scale = min(1.2, 1300 / width, 1700 / height, (3_000_000 / (width * height)) ** 0.5)
                bitmap = p.render(scale=scale)
                image = bitmap.to_pil()
                try:
                    image.thumbnail((1300, 1700))
                    out = io.BytesIO()
                    image.convert("RGB").save(out, "JPEG", quality=75, optimize=True)
                    encoded = base64.b64encode(out.getvalue()).decode("ascii")
                finally:
                    image.close()
                bitmap.close()
            finally:
                p.close()
        finally:
            pdf.close()
    except Exception:
        # PDF renderer failures are opaque to clients; never return raw PDF data.
        return Response({"code": "preview_unavailable"}, status=503)
    response = Response({"page": page, "image_base64": encoded, "mime": "image/jpeg"})
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def correct_question(request, question_id):
    _enabled()
    ser = TextCorrection(data=request.data)
    ser.is_valid(raise_exception=True)
    try:
        q = update_question(question_id=question_id, actor=request.user, **ser.validated_data)
    except (PaperQuestionDraft.DoesNotExist, Topic.DoesNotExist):
        return Response({"code": "not_found"}, status=404)
    except (PaperConflict, PermissionDenied) as exc:
        return _response_error(exc)
    return Response(_question(q))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def decide_question(request, question_id):
    _enabled()
    ser = QuestionDecision(data=request.data)
    ser.is_valid(raise_exception=True)
    if ser.validated_data["action"] == "verify" and not ser.validated_data["compared_with_original"]:
        return Response({"code": "comparison_required", "message": "Compare the corrected question with the original PDF"}, status=409)
    try:
        q = review_question(question_id=question_id, actor=request.user, action=ser.validated_data["action"], rationale=ser.validated_data["rationale"])
    except PaperQuestionDraft.DoesNotExist:
        return Response({"code": "not_found"}, status=404)
    except (PaperConflict, PermissionDenied) as exc:
        return _response_error(exc)
    return Response(_question(q))


@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated])
def variations(request, question_id):
    _enabled()
    _reader(request.user)
    q = get_object_or_404(PaperQuestionDraft, pk=question_id)
    if request.method == "POST":
        ser = VariationRequest(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            job = queue_variations(question_id=question_id, actor=request.user, **ser.validated_data)
        except (PaperConflict, PermissionDenied) as exc:
            return _response_error(exc)
        return Response({"id": str(job.pk), "state": job.state}, status=201)
    jobs = PaperVariationJob.objects.filter(question=q).prefetch_related("candidates").order_by("-created_at")[:30]
    return Response({"jobs": [dict(id=str(j.pk), state=j.state, failure_code=j.failure_code,
                                   provider=j.provider, kind=j.kind, created_at=j.created_at.isoformat(),
                                   candidates=[_candidate(c) for c in j.candidates.all()]) for j in jobs]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def edit_candidate(request, candidate_id):
    _enabled()
    ser = VariationEdit(data=request.data)
    ser.is_valid(raise_exception=True)
    values = dict(ser.validated_data)
    note = values.pop("rationale")
    try:
        c = edit_variation(candidate_id=candidate_id, actor=request.user, values=values, note=note)
    except PaperVariationCandidate.DoesNotExist:
        return Response({"code": "not_found"}, status=404)
    except (PaperConflict, PermissionDenied) as exc:
        return _response_error(exc)
    return Response(_candidate(c))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def decide_candidate(request, candidate_id):
    _enabled()
    ser = VariationDecision(data=request.data)
    ser.is_valid(raise_exception=True)
    try:
        c = review_variation(candidate_id=candidate_id, actor=request.user, action=ser.validated_data["action"], note=ser.validated_data["rationale"])
    except PaperVariationCandidate.DoesNotExist:
        return Response({"code": "not_found"}, status=404)
    except (PaperConflict, PermissionDenied) as exc:
        return _response_error(exc)
    return Response(_candidate(c))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def external_authorization(request, document_id):
    _enabled()
    ser = VendorReview(data=request.data)
    ser.is_valid(raise_exception=True)
    try:
        auth = authorize_paper_external(document_id=document_id, actor=request.user, **ser.validated_data)
    except DocumentSubmission.DoesNotExist:
        return Response({"code": "not_found"}, status=404)
    except (PaperConflict, PermissionDenied) as exc:
        return _response_error(exc)
    return Response({"authorized": bool(auth)})
