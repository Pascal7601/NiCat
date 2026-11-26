"""Rights/content separation, audit trail, and private-by-default contribution intake."""
import hashlib
import re
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from .models import Contribution, ContributionDecision


class ContributionConflict(Exception):
    pass


class ContributionQuotaExceeded(Exception):
    pass


def digest_body(body: str) -> str:
    normalized = re.sub(r"\s+", " ", body).strip().casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@transaction.atomic
def submit(*, student, unit, title, body, author_declaration, allow_display, allow_ai_use):
    if not author_declaration or not allow_display:
        raise ContributionConflict("Original authorship and display permission must be declared")
    # Serialize intake per student for a strict calendar-day cap on PostgreSQL.
    type(student).objects.select_for_update().get(pk=student.pk)
    daily_limit = max(0, int(getattr(settings, "NICAT_CONTRIBUTION_DAILY_LIMIT", 3)))
    today = timezone.localdate()
    if Contribution.objects.filter(student=student, created_at__date=today).count() >= daily_limit:
        raise ContributionQuotaExceeded("Daily contribution submission limit reached")
    digest = digest_body(body)
    # Flag exact duplicate content without disclosing anyone else's data.
    duplicate = Contribution.objects.filter(content_sha256=digest).exists()
    entry = Contribution(
        student=student, unit=unit, title=title.strip(), body=body.strip(),
        author_declaration=True, allow_display=True, allow_ai_use=bool(allow_ai_use),
        content_sha256=digest, possible_duplicate=duplicate,
    )
    entry.full_clean()
    entry.save()
    return entry


def _require(actor, permission):
    if not actor.is_active or not actor.is_staff or not actor.has_perm(permission):
        raise PermissionDenied("Academic reviewer permission required")


def _record(entry, actor, action, rationale):
    ContributionDecision.objects.create(contribution=entry, actor=actor, action=action, rationale=rationale.strip())


@transaction.atomic
def clear_rights(*, contribution_id, actor):
    _require(actor, "contributions.review_contribution_rights")
    entry = Contribution.objects.select_for_update().get(pk=contribution_id)
    if entry.state != Contribution.State.PENDING or entry.rights_reviewed_by_id:
        raise ContributionConflict("Submission is not awaiting initial rights clearance")
    if not entry.author_declaration or not entry.allow_display:
        raise ContributionConflict("Student must declare authorship and display permission")
    if len(entry.rights_review_note.strip()) < 15:
        raise ContributionConflict("Write at least 15 characters of rights-review rationale and save it first")
    entry.rights_reviewed_by = actor
    entry.rights_reviewed_at = timezone.now()
    entry.save(update_fields=["rights_reviewed_by", "rights_reviewed_at", "updated_at"])
    _record(entry, actor, ContributionDecision.Action.RIGHTS_CLEARED, entry.rights_review_note)
    return entry


@transaction.atomic
def approve_academic(*, contribution_id, actor):
    _require(actor, "contributions.review_contribution_content")
    entry = Contribution.objects.select_for_update().get(pk=contribution_id)
    if entry.state != Contribution.State.PENDING or not entry.rights_reviewed_by_id:
        raise ContributionConflict("Rights clearance must precede academic approval")
    if entry.rights_reviewed_by_id == actor.pk:
        raise ContributionConflict("Two distinct reviewers are required")
    if entry.possible_duplicate:
        raise ContributionConflict("Possible duplicates require investigation before approval")
    if len(entry.academic_review_note.strip()) < 15:
        raise ContributionConflict("Write at least 15 characters of academic-review rationale and save it first")
    entry.state = Contribution.State.APPROVED
    entry.academic_reviewed_by = actor
    entry.academic_reviewed_at = timezone.now()
    entry.save(update_fields=["state", "academic_reviewed_by", "academic_reviewed_at", "updated_at"])
    _record(entry, actor, ContributionDecision.Action.APPROVED, entry.academic_review_note)
    # Deliberately no SourceDocument, SourceExcerpt or search-index creation.
    return entry


@transaction.atomic
def hold_rights(*, contribution_id, actor):
    _require(actor, "contributions.review_contribution_rights")
    entry = Contribution.objects.select_for_update().get(pk=contribution_id)
    if entry.state != Contribution.State.PENDING:
        raise ContributionConflict("Only pending submissions may enter a rights hold")
    if len(entry.rights_review_note.strip()) < 15:
        raise ContributionConflict("Provide a rights-hold reason before applying the action")
    entry.state = Contribution.State.RIGHTS_HOLD
    entry.save(update_fields=["state", "updated_at"])
    _record(entry, actor, ContributionDecision.Action.RIGHTS_HOLD, entry.rights_review_note)
    return entry


@transaction.atomic
def reject(*, contribution_id, actor):
    _require(actor, "contributions.review_contribution_content")
    entry = Contribution.objects.select_for_update().get(pk=contribution_id)
    if entry.state not in (Contribution.State.PENDING, Contribution.State.RIGHTS_HOLD):
        raise ContributionConflict("Only pending or rights-held submissions may be rejected")
    if len(entry.academic_review_note.strip()) < 15:
        raise ContributionConflict("Provide a rejection reason before applying the action")
    entry.state = Contribution.State.REJECTED
    entry.save(update_fields=["state", "updated_at"])
    _record(entry, actor, ContributionDecision.Action.REJECTED, entry.academic_review_note)
    return entry


@transaction.atomic
def withdraw(*, contribution_id, actor):
    entry = Contribution.objects.select_for_update().get(pk=contribution_id)
    if entry.student_id != actor.pk:
        _require(actor, "contributions.review_contribution_content")
    if entry.state == Contribution.State.WITHDRAWN:
        return entry
    entry.state = Contribution.State.WITHDRAWN
    entry.save(update_fields=["state", "updated_at"])
    _record(entry, actor, ContributionDecision.Action.WITHDRAWN, "Contributor withdrawal" if entry.student_id == actor.pk else "Staff withdrawal")
    # Publishing/indexing is not implemented in this first slice.
    return entry
