"""Dedicated staff UI API. No anonymous access, arbitrary proxy, or private student endpoints.

Published-state transitions use the existing domain services: the workspace does
not implement a second/looser approval path.
"""
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.academics.models import Topic, Unit
from apps.contributions.models import Contribution
from apps.contributions.services import (
    ContributionConflict, approve_academic, clear_rights, hold_rights,
    reject, withdraw,
)
from apps.questions.models import QuestionRevision
from apps.resources.models import SourceDocument, SourceReference
from apps.study_coach.models import TutorFollowUp
from apps.study_coach.services import (
    CoachConflict, publish_followup, reject_followup, withdraw_followup,
)
from apps.study_tutor.models import SourceExcerpt, TutorExplanation
from apps.study_tutor.provider import TutorProviderError
from apps.study_tutor.services import (
    TutorConflict, approve_excerpt, make_draft, publish_explanation,
    withdraw_excerpt, withdraw_explanation,
)
from .serializers import (
    ActionSerializer, DocumentCreateSerializer, ExcerptCreateSerializer,
    FollowupAnswerSerializer, NoteSerializer, ReferenceCreateSerializer,
    RightsDecisionSerializer, TutorDraftEditSerializer,
)
from .services import StaffConflict, decide_rights, require_staff


def _enabled():
    return bool(getattr(settings, "NICAT_STAFF_WORKSPACE_ENABLED", False))


def _guard(request, *permissions):
    # Feature-off returns nothing about staff queues, including to superusers.
    if not _enabled():
        return Response({"code": "disabled"}, status=404)
    require_staff(request.user, *permissions)
    return None


def _action(request, allowed):
    serializer = ActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    value = serializer.validated_data["action"]
    if value not in allowed:
        return None
    return value


def _conflict(exc):
    return Response({"code": "conflict", "message": str(exc)}, status=409)


def _invalid(exc):
    return Response({"code": "invalid", "message": str(exc)}, status=400)


def _source_payload(x):
    return {
        "id": str(x.pk), "state": x.state, "topic_id": str(x.topic_id),
        "topic": x.topic.title, "reference_id": str(x.reference_id),
        "document_id": str(x.reference.document_id),
        "document": x.reference.document.title,
        "rights_status": x.reference.document.rights_status,
        "text": x.text, "approved_by": str(x.approved_by_id) if x.approved_by_id else None,
    }


def _tutor_payload(x):
    return {
        "id": str(x.pk), "state": x.state, "version": x.version,
        "revision_id": str(x.revision_id), "question": x.revision.prompt[:400],
        "topic": x.revision.question.topic.title,
        "explanation": x.explanation, "common_mistake": x.common_mistake,
        "practice_tip": x.practice_tip, "model_name": x.model_name,
        "citations": [
            {"id": str(c.pk), "document": c.reference.document.title,
             "rights_status": c.reference.document.rights_status,
             "state": c.state, "text": c.text[:500]}
            for c in x.citations.all()
        ],
    }


def _contrib_payload(x):
    return {
        "id": str(x.pk), "state": x.state, "title": x.title, "unit": x.unit.title,
        "student_id": str(x.student_id), "body": x.body,
        "author_declaration": x.author_declaration, "allow_display": x.allow_display,
        "allow_ai_use": x.allow_ai_use, "possible_duplicate": x.possible_duplicate,
        "rights_review_note": x.rights_review_note,
        "academic_review_note": x.academic_review_note,
        "rights_reviewed_by": str(x.rights_reviewed_by_id) if x.rights_reviewed_by_id else None,
        "academic_reviewed_by": str(x.academic_reviewed_by_id) if x.academic_reviewed_by_id else None,
        "decisions": [
            {"action": d.action, "rationale": d.rationale, "actor_id": str(d.actor_id),
             "created_at": d.created_at.isoformat()}
            for d in x.decisions.all()
        ],
    }


def _followup_payload(x):
    return {
        "id": str(x.pk), "state": x.state, "question": x.question,
        "student_id": str(x.student_id), "draft_answer": x.draft_answer,
        "published_answer": x.published_answer,
        "citations": [
            {"id": str(c.pk), "document": c.reference.document.title,
             "state": c.state, "rights_status": c.reference.document.rights_status,
             "text": c.text[:500]}
            for c in x.citations.all()
        ],
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def overview(request):
    refused = _guard(request)
    if refused is not None:
        return refused
    user = request.user
    permissions = {
        "sources": user.has_perm("study_tutor.view_sourceexcerpt"),
        "tutor": user.has_perm("study_tutor.view_tutorexplanation"),
        "contributions": user.has_perm("contributions.view_contribution"),
        "followups": user.has_perm("study_coach.view_tutorfollowup"),
    }
    if not any(permissions.values()):
        raise PermissionDenied("No staff workspace queue permissions assigned")
    counts = {}
    if permissions["sources"]:
        counts["sources_pending"] = SourceExcerpt.objects.filter(state=SourceExcerpt.State.DRAFT).count()
    if permissions["tutor"]:
        counts["tutor_drafts"] = TutorExplanation.objects.filter(state=TutorExplanation.State.DRAFT).count()
    if permissions["contributions"]:
        counts["contributions_pending"] = Contribution.objects.filter(state=Contribution.State.PENDING).count()
    if permissions["followups"]:
        counts["followups_pending"] = TutorFollowUp.objects.filter(state=TutorFollowUp.State.DRAFT).count()
    return Response({"permissions": permissions, "counts": counts})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def source_units(request):
    refused = _guard(request, "resources.view_sourcedocument")
    if refused is not None:
        return refused
    return Response({"items": [{"id": str(u.pk), "title": u.title}
        for u in Unit.objects.order_by("title")[:300]]})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def documents(request):
    refused = _guard(request, "resources.view_sourcedocument" if request.method == "GET" else "resources.add_sourcedocument")
    if refused is not None:
        return refused
    if request.method == "GET":
        result = SourceDocument.objects.select_related("unit").order_by("title")[:100]
        return Response({"items": [{
            "id": str(d.pk), "title": d.title,
            "unit_id": str(d.unit_id) if d.unit_id else None,
            "unit": d.unit.title if d.unit else "Unassigned",
            "source_kind": d.source_kind, "rights_status": d.rights_status,
            "source_url": d.source_url,
        } for d in result]})
    serializer = DocumentCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    document = SourceDocument(**serializer.validated_data)
    try:
        document.full_clean()
        document.save()
    except ValidationError as exc:
        return _invalid(exc)
    return Response({"id": str(document.pk), "rights_status": document.rights_status}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def document_rights(request, document_id):
    refused = _guard(request, "staff_workspace.review_source_rights", "resources.change_sourcedocument")
    if refused is not None:
        return refused
    serializer = RightsDecisionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        document = decide_rights(document_id=document_id, actor=request.user, **serializer.validated_data)
    except SourceDocument.DoesNotExist:
        return Response({"code": "not_found"}, status=404)
    except StaffConflict as exc:
        return _conflict(exc)
    except ValidationError as exc:
        return _invalid(exc)
    return Response({"id": str(document.pk), "rights_status": document.rights_status})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def references(request):
    refused = _guard(request, "resources.view_sourcereference" if request.method == "GET" else "resources.add_sourcereference")
    if refused is not None:
        return refused
    if request.method == "GET":
        data = SourceReference.objects.select_related("document").order_by("document__title", "page_label")[:200]
        return Response({"items": [{"id": str(r.pk), "document_id": str(r.document_id),
             "document": r.document.title, "page": r.page_label, "section": r.section_label} for r in data]})
    serializer = ReferenceCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    reference = SourceReference(**serializer.validated_data)
    try:
        reference.full_clean()
        reference.save()
    except ValidationError as exc:
        return _invalid(exc)
    return Response({"id": str(reference.pk)}, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def topics(request):
    refused = _guard(request, "study_tutor.view_sourceexcerpt")
    if refused is not None:
        return refused
    qs = Topic.objects.select_related("unit")
    return Response({"items": [{"id": str(t.pk), "title": t.title,
        "unit_id": str(t.unit_id)} for t in qs.order_by("unit__title", "position", "title")[:300]]})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def excerpts(request):
    refused = _guard(request, "study_tutor.view_sourceexcerpt" if request.method == "GET" else "study_tutor.add_sourceexcerpt")
    if refused is not None:
        return refused
    if request.method == "GET":
        qs = SourceExcerpt.objects.select_related("topic", "reference__document")
        state = request.query_params.get("state")
        if state in SourceExcerpt.State.values:
            qs = qs.filter(state=state)
        return Response({"items": [_source_payload(x) for x in qs.order_by("-created_at")[:100]]})
    serializer = ExcerptCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    obj = SourceExcerpt(**serializer.validated_data)
    try:
        obj.save()  # Model's full_clean checks reference document matches topic unit.
    except ValidationError as exc:
        return _invalid(exc)
    return Response({"id": str(obj.pk), "state": obj.state}, status=201)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def excerpt_detail(request, excerpt_id):
    refused = _guard(request, "study_tutor.view_sourceexcerpt" if request.method == "GET" else "study_tutor.change_sourceexcerpt")
    if refused is not None:
        return refused
    if request.method == "GET":
        obj = get_object_or_404(SourceExcerpt.objects.select_related("topic", "reference__document"), pk=excerpt_id)
        return Response(_source_payload(obj))
    # Only draft text may be edited; topic/reference changes require a new excerpt.
    serializer = ExcerptCreateSerializer(data={
        "reference_id": request.data.get("reference_id"),
        "topic_id": request.data.get("topic_id"),
        "text": request.data.get("text"),
    })
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        obj = get_object_or_404(SourceExcerpt.objects.select_for_update(), pk=excerpt_id)
        if obj.state != SourceExcerpt.State.DRAFT:
            return _conflict("Only draft excerpts can be edited")
        if (obj.reference_id != serializer.validated_data["reference"].pk
                or obj.topic_id != serializer.validated_data["topic"].pk):
            return _conflict("To change topic/reference, create a new excerpt")
        obj.text = serializer.validated_data["text"]
        try:
            obj.save(update_fields=["text"])
        except ValidationError as exc:
            return _invalid(exc)
    return Response({"id": str(obj.pk), "state": obj.state})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def excerpt_action(request, excerpt_id):
    refused = _guard(request, "study_tutor.approve_tutor_content")
    if refused is not None:
        return refused
    action = _action(request, ("approve", "withdraw"))
    if action is None:
        return _invalid("Unsupported action")
    service = approve_excerpt if action == "approve" else withdraw_excerpt
    try:
        obj = service(excerpt_id=excerpt_id, actor=request.user)
    except SourceExcerpt.DoesNotExist:
        return Response({"code": "not_found"}, status=404)
    except (TutorConflict, ValidationError) as exc:
        return _conflict(exc)
    return Response({"id": str(obj.pk), "state": obj.state})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tutor_list(request):
    refused = _guard(request, "study_tutor.view_tutorexplanation")
    if refused is not None:
        return refused
    qs = TutorExplanation.objects.select_related("revision__question__topic").prefetch_related("citations__reference__document")
    state = request.query_params.get("state")
    if state in TutorExplanation.State.values:
        qs = qs.filter(state=state)
    return Response({"items": [_tutor_payload(x) for x in qs[:80]]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tutor_generate(request):
    refused = _guard(request, "study_tutor.approve_tutor_content")
    if refused is not None:
        return refused
    if not getattr(settings, "NICAT_AI_TUTOR_GENERATION_ENABLED", False):
        return Response({"code": "disabled"}, status=404)
    from uuid import UUID
    try:
        revision_id = UUID(str(request.data.get("revision_id")))
    except (TypeError, ValueError, AttributeError):
        return _invalid("Provide a valid revision UUID")
    try:
        obj, created = make_draft(revision_id=revision_id, actor=request.user)
    except QuestionRevision.DoesNotExist:
        return Response({"code": "not_found"}, status=404)
    except TutorConflict as exc:
        return _conflict(exc)
    except TutorProviderError:
        return Response({"code": "ai_unavailable", "message": "Tutor draft provider unavailable"}, status=503)
    return Response({"id": str(obj.pk), "state": obj.state, "version": obj.version}, status=201 if created else 200)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def tutor_detail(request, explanation_id):
    refused = _guard(request, "study_tutor.view_tutorexplanation" if request.method == "GET" else "study_tutor.approve_tutor_content")
    if refused is not None:
        return refused
    if request.method == "GET":
        obj = get_object_or_404(TutorExplanation.objects.select_related("revision__question__topic").prefetch_related("citations__reference__document"), pk=explanation_id)
        return Response(_tutor_payload(obj))
    serializer = TutorDraftEditSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        obj = get_object_or_404(TutorExplanation.objects.select_for_update(), pk=explanation_id)
        if obj.state != TutorExplanation.State.DRAFT:
            return _conflict("Only Tutor drafts can be edited")
        for key, val in serializer.validated_data.items():
            setattr(obj, key, val)
        try:
            obj.save(update_fields=["explanation", "common_mistake", "practice_tip"])
        except ValidationError as exc:
            return _invalid(exc)
    return Response({"id": str(obj.pk), "state": obj.state})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tutor_action(request, explanation_id):
    refused = _guard(request, "study_tutor.approve_tutor_content")
    if refused is not None:
        return refused
    action = _action(request, ("publish", "withdraw"))
    if action is None:
        return _invalid("Unsupported action")
    service = publish_explanation if action == "publish" else withdraw_explanation
    if action == "publish":
        # Mock drafts must not accidentally be exposed to a real student account.
        draft = get_object_or_404(TutorExplanation, pk=explanation_id)
        if any("MOCK TEST DATA" in getattr(draft, key).upper() for key in ("explanation", "common_mistake", "practice_tip")):
            if not (settings.DEBUG and getattr(settings, "NICAT_STAFF_ALLOW_MOCK_PUBLICATION_FOR_TESTS", False)):
                return _conflict("Replace mock text with reviewed academic content before publication")
    try:
        obj = service(explanation_id=explanation_id, actor=request.user)
    except TutorExplanation.DoesNotExist:
        return Response({"code": "not_found"}, status=404)
    except (TutorConflict, ValidationError) as exc:
        return _conflict(exc)
    return Response({"id": str(obj.pk), "state": obj.state})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def contribution_list(request):
    refused = _guard(request, "contributions.view_contribution")
    if refused is not None:
        return refused
    qs = Contribution.objects.select_related("unit").order_by("-created_at")
    state = request.query_params.get("state")
    if state in Contribution.State.values:
        qs = qs.filter(state=state)
    return Response({"items": [{"id": str(c.pk), "title": c.title, "unit": c.unit.title,
        "state": c.state, "possible_duplicate": c.possible_duplicate,
        "rights_cleared": bool(c.rights_reviewed_by_id),
        "created_at": c.created_at.isoformat()} for c in qs[:100]]})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def contribution_detail(request, contribution_id):
    if request.method == "GET":
        refused = _guard(request, "contributions.view_contribution")
        if refused is not None:
            return refused
        obj = get_object_or_404(Contribution.objects.select_related("unit").prefetch_related("decisions"), pk=contribution_id)
        return Response(_contrib_payload(obj))
    field = request.data.get("field")
    if field not in ("rights_review_note", "academic_review_note"):
        return _invalid("Only a review rationale may be saved")
    perm = "contributions.review_contribution_rights" if field == "rights_review_note" else "contributions.review_contribution_content"
    refused = _guard(request, perm, "contributions.change_contribution")
    if refused is not None:
        return refused
    serializer = NoteSerializer(data={"note": request.data.get("note")})
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        obj = get_object_or_404(Contribution.objects.select_for_update(), pk=contribution_id)
        if field == "rights_review_note" and (obj.state != Contribution.State.PENDING or obj.rights_reviewed_by_id):
            return _conflict("Rights review is already completed or submission is closed")
        if field == "academic_review_note" and obj.state not in (Contribution.State.PENDING, Contribution.State.RIGHTS_HOLD):
            return _conflict("Academic review is already closed")
        setattr(obj, field, serializer.validated_data["note"])
        obj.save(update_fields=[field, "updated_at"])
    return Response({"id": str(obj.pk), "saved": field})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def contribution_action(request, contribution_id):
    allowed = {
        "clear_rights": (clear_rights, "contributions.review_contribution_rights"),
        "hold_rights": (hold_rights, "contributions.review_contribution_rights"),
        "approve": (approve_academic, "contributions.review_contribution_content"),
        "reject": (reject, "contributions.review_contribution_content"),
        "withdraw": (withdraw, "contributions.review_contribution_content"),
    }
    action = _action(request, allowed)
    if action is None:
        return _invalid("Unsupported action")
    service, perm = allowed[action]
    refused = _guard(request, perm)
    if refused is not None:
        return refused
    try:
        obj = service(contribution_id=contribution_id, actor=request.user)
    except Contribution.DoesNotExist:
        return Response({"code": "not_found"}, status=404)
    except (ContributionConflict, ValidationError) as exc:
        return _conflict(exc)
    return Response({"id": str(obj.pk), "state": obj.state})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def followup_list(request):
    refused = _guard(request, "study_coach.view_tutorfollowup")
    if refused is not None:
        return refused
    qs = TutorFollowUp.objects.order_by("-created_at")
    state = request.query_params.get("state")
    if state in TutorFollowUp.State.values:
        qs = qs.filter(state=state)
    return Response({"items": [{"id": str(f.pk), "question": f.question,
        "state": f.state, "created_at": f.created_at.isoformat()} for f in qs[:100]]})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def followup_detail(request, followup_id):
    refused = _guard(request, "study_coach.view_tutorfollowup" if request.method == "GET" else "study_tutor.approve_tutor_content")
    if refused is not None:
        return refused
    if request.method == "GET":
        obj = get_object_or_404(TutorFollowUp.objects.prefetch_related("citations__reference__document"), pk=followup_id)
        return Response(_followup_payload(obj))
    serializer = FollowupAnswerSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        obj = get_object_or_404(TutorFollowUp.objects.select_for_update(), pk=followup_id)
        if obj.state != TutorFollowUp.State.DRAFT:
            return _conflict("Only pending follow-up drafts can be edited")
        obj.draft_answer = serializer.validated_data["draft_answer"]
        obj.save(update_fields=["draft_answer"])
    return Response({"id": str(obj.pk), "state": obj.state})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def followup_action(request, followup_id):
    refused = _guard(request, "study_tutor.approve_tutor_content")
    if refused is not None:
        return refused
    allowed = {"publish": publish_followup, "reject": reject_followup, "withdraw": withdraw_followup}
    action = _action(request, allowed)
    if action is None:
        return _invalid("Unsupported action")
    try:
        obj = allowed[action](followup_id=followup_id, actor=request.user)
    except TutorFollowUp.DoesNotExist:
        return Response({"code": "not_found"}, status=404)
    except (CoachConflict, ValidationError) as exc:
        return _conflict(exc)
    return Response({"id": str(obj.pk), "state": obj.state})
