"""Source approval, grounded draft generation, publication and student-safe delivery."""
import hashlib
import json
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.questions.models import QuestionRevision
from apps.resources.models import SourceDocument

from .models import SourceExcerpt, TutorExplanation
from .provider import TutorProviderError, generate_explanation
from .retrieval import retrieve_excerpts


class TutorConflict(Exception):
    pass


def require_academic_reviewer(user):
    # Separate content-publication permission from existing human-marking permission.
    if not user.is_authenticated or not user.is_active or not user.is_staff or not user.has_perm(
        "study_tutor.approve_tutor_content"
    ):
        raise PermissionDenied("Academic content approval permission required")


def _eligible(excerpts: list[SourceExcerpt], *, revision) -> bool:
    topic = revision.question.topic
    return bool(excerpts) and all(
        e.state == SourceExcerpt.State.APPROVED
        and e.topic_id == topic.pk
        and e.reference.document.unit_id == topic.unit_id
        and e.reference.document.rights_status == SourceDocument.Rights.ALLOWED
        for e in excerpts
    )


def fingerprint(excerpts: list[SourceExcerpt]) -> str:
    manifest = [{"id": str(e.pk), "text": e.text,
                 "page": e.reference.page_label, "section": e.reference.section_label,
                 "document_id": str(e.reference.document_id)}
                for e in sorted(excerpts, key=lambda e: str(e.pk))]
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def approve_excerpt(*, excerpt_id, actor) -> SourceExcerpt:
    require_academic_reviewer(actor)
    with transaction.atomic():
        excerpt = SourceExcerpt.objects.select_for_update().select_related(
            "reference__document", "topic"
        ).get(pk=excerpt_id)
        if excerpt.state != SourceExcerpt.State.DRAFT:
            raise TutorConflict("Only unreviewed source excerpts can be approved")
        if excerpt.reference.document.rights_status != SourceDocument.Rights.ALLOWED:
            raise TutorConflict("Source rights must be cleared before academic approval")
        excerpt.state = SourceExcerpt.State.APPROVED
        excerpt.approved_by = actor
        excerpt.approved_at = timezone.now()
        excerpt.save(update_fields=["state", "approved_by", "approved_at"])
        return excerpt


def withdraw_excerpt(*, excerpt_id, actor) -> SourceExcerpt:
    require_academic_reviewer(actor)
    with transaction.atomic():
        excerpt = SourceExcerpt.objects.select_for_update().get(pk=excerpt_id)
        if excerpt.state != SourceExcerpt.State.APPROVED:
            raise TutorConflict("Only approved excerpts can be withdrawn")
        excerpt.state = SourceExcerpt.State.WITHDRAWN
        excerpt.save(update_fields=["state"])
        return excerpt


def validate_generated(raw: dict, excerpts: list[SourceExcerpt]) -> tuple[str, str, str, list]:
    """The only citations the client can receive are existing approved excerpt IDs."""
    if not isinstance(raw, dict):
        raise TutorProviderError("AI returned an invalid explanation")
    ranges = {"explanation": (30, 5000), "common_mistake": (10, 1500), "practice_tip": (10, 1500)}
    fields = {}
    for key, (min_length, max_length) in ranges.items():
        val = raw.get(key)
        if not isinstance(val, str) or not min_length <= len(val.strip()) <= max_length:
            raise TutorProviderError(f"AI returned an invalid {key}")
        fields[key] = val.strip()
    cited_ids = raw.get("citation_ids")
    available = {str(e.pk): e for e in excerpts}
    if (not isinstance(cited_ids, list) or not 1 <= len(cited_ids) <= len(excerpts)
            or any(not isinstance(x, str) or x not in available for x in cited_ids)
            or len(cited_ids) != len(set(cited_ids))):
        raise TutorProviderError("AI references missing, duplicate or unapproved evidence")
    return fields["explanation"], fields["common_mistake"], fields["practice_tip"], [available[x] for x in cited_ids]


def make_draft(*, revision_id, actor) -> tuple[TutorExplanation, bool]:
    require_academic_reviewer(actor)
    revision = QuestionRevision.objects.select_related("question__topic").filter(
        pk=revision_id, status=QuestionRevision.Status.PUBLISHED
    ).first()
    if revision is None:
        raise QuestionRevision.DoesNotExist()
    existing = TutorExplanation.objects.filter(revision=revision, state=TutorExplanation.State.DRAFT).first()
    if existing:
        return existing, False
    excerpts = retrieve_excerpts(revision=revision)
    if not _eligible(excerpts, revision=revision):
        raise TutorConflict("No approved, relevant excerpts are available for this question")
    raw = generate_explanation(revision=revision, excerpts=excerpts)
    explanation, mistake, tip, cited = validate_generated(raw, excerpts)
    # Re-check approval/rights after the remote model call, before storing a draft.
    current = {e.pk: e for e in SourceExcerpt.objects.filter(pk__in=[e.pk for e in cited]).select_related(
        "reference__document", "topic"
    )}
    if len(current) != len(cited) or not _eligible(list(current.values()), revision=revision):
        raise TutorConflict("Academic source permissions changed during generation")
    cited = [current[e.pk] for e in cited]
    with transaction.atomic():
        QuestionRevision.objects.select_for_update().get(pk=revision.pk)
        existing = TutorExplanation.objects.filter(revision=revision, state=TutorExplanation.State.DRAFT).first()
        if existing:
            return existing, False
        next_version = (TutorExplanation.objects.filter(revision=revision).aggregate(
            highest=Max("version")
        )["highest"] or 0) + 1
        draft = TutorExplanation.objects.create(
            revision=revision, version=next_version, explanation=explanation,
            common_mistake=mistake, practice_tip=tip, model_name=(
                getattr(settings, "NICAT_AI_TUTOR_MODEL", "") or getattr(settings, "NICAT_AI_MODEL", "")
            ), source_fingerprint=fingerprint(cited), generated_by=actor,
        )
        draft.citations.set(cited)
    return draft, True


def _current_citations(explanation: TutorExplanation) -> list[SourceExcerpt]:
    return list(explanation.citations.select_related("reference__document", "topic"))


def publish_explanation(*, explanation_id, actor) -> TutorExplanation:
    require_academic_reviewer(actor)
    with transaction.atomic():
        explanation = TutorExplanation.objects.select_for_update().select_related(
            "revision__question__topic"
        ).get(pk=explanation_id)
        if explanation.state != TutorExplanation.State.DRAFT:
            raise TutorConflict("Only drafts can be published")
        if TutorExplanation.objects.filter(revision=explanation.revision, state=TutorExplanation.State.PUBLISHED).exists():
            raise TutorConflict("Withdraw the current version before publishing a replacement")
        sources = _current_citations(explanation)
        if not _eligible(sources, revision=explanation.revision) or fingerprint(sources) != explanation.source_fingerprint:
            raise TutorConflict("Cited academic evidence is missing, edited or no longer allowed")
        explanation.state = TutorExplanation.State.PUBLISHED
        explanation.approved_by = actor
        explanation.approved_at = timezone.now()
        explanation.save(update_fields=["state", "approved_by", "approved_at"])
        return explanation


def withdraw_explanation(*, explanation_id, actor) -> TutorExplanation:
    require_academic_reviewer(actor)
    with transaction.atomic():
        explanation = TutorExplanation.objects.select_for_update().get(pk=explanation_id)
        if explanation.state != TutorExplanation.State.PUBLISHED:
            raise TutorConflict("Only published explanations can be withdrawn")
        explanation.state = TutorExplanation.State.WITHDRAWN
        explanation.save(update_fields=["state"])
        return explanation


def student_payload(*, revision) -> dict | None:
    """Never exposes AI drafts, private rubrics, provider prompts or grader metadata."""
    explanation = TutorExplanation.objects.filter(
        revision=revision, state=TutorExplanation.State.PUBLISHED
    ).select_related("approved_by").first()
    if explanation is None or not explanation.approved_by_id or not explanation.approved_at:
        return None
    sources = _current_citations(explanation)
    if not _eligible(sources, revision=revision) or fingerprint(sources) != explanation.source_fingerprint:
        return None
    return {
        "revision_version": explanation.version,
        "question_topic": revision.question.topic.title,
        "explanation": explanation.explanation,
        "common_mistake": explanation.common_mistake,
        "practice_tip": explanation.practice_tip,
        "ai_assisted": True,
        "reviewer_approved": True,
        "official_university_material": False,
        "sources": [
            {"excerpt_id": str(e.pk), "title": e.reference.document.title,
             "page": e.reference.page_label, "section": e.reference.section_label,
             "evidence": e.text[:300]}
            for e in sources
        ],
    }
