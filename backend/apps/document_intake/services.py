"""Private original intake; two distinct humans approve future question-draft eligibility."""
import os
import re
import uuid
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.text import slugify
from django.utils import timezone

from apps.academics.models import CurriculumUnit, CurriculumVersion, Unit
from .models import DocumentSubmission, DocumentReviewEvent
from .storage import private_path, save_original


class IntakeConflict(Exception):
    pass


class IntakeQuotaExceeded(Exception):
    pass


def _require_reviewer(actor, perm):
    if not actor.is_active or not actor.is_staff or not actor.has_perm(perm):
        raise PermissionDenied("Academic document review permission required")


def _mapping_exists(programme, unit):
    return CurriculumUnit.objects.filter(curriculum_version__programme=programme, unit=unit).exists()


def _audit(entry, actor, action, rationale):
    DocumentReviewEvent.objects.create(document=entry, actor=actor, action=action, rationale=rationale)


@transaction.atomic
def submit_document(*, student, file, validated):
    """Quarantine a document; do NOT scan or publish in the HTTP request."""
    type(student).objects.select_for_update().get(pk=student.pk)
    daily = max(0, int(getattr(settings, "NICAT_DOCUMENT_DAILY_LIMIT", 3)))
    if DocumentSubmission.objects.filter(student=student, created_at__date=timezone.localdate()).count() >= daily:
        raise IntakeQuotaExceeded("Daily document submission limit reached")
    programme = validated["programme"]
    unit = validated.get("unit")
    if unit and not _mapping_exists(programme, unit):
        raise IntakeConflict("Selected unit is not associated with this programme. Request a missing unit instead.")
    if not unit and not validated.get("suggested_unit_title", "").strip():
        raise IntakeConflict("Select a unit or request a missing unit")
    if not validated.get("permit_question_generation"):
        raise IntakeConflict("Explicit permission for question drafting is required for this submission route")
    original_name = os.path.basename((file.name or "document").replace("\\", "/"))[:180]
    suffix = Path(original_name).suffix.lower()
    if suffix not in (".pdf", ".txt"):
        raise IntakeConflict("Only PDF and TXT documents are accepted")
    file_type = suffix[1:]
    key = f"{uuid.uuid4().hex}{suffix}"
    try:
        size, sha = save_original(file, key, file_type)
        duplicate = DocumentSubmission.objects.filter(sha256=sha).exists()
        entry = DocumentSubmission(
            student=student, programme=programme, unit=unit,
            suggested_unit_title=validated.get("suggested_unit_title", ""),
            suggested_unit_code=validated.get("suggested_unit_code", ""),
            year_number=validated.get("year_number"), semester_number=validated.get("semester_number"),
            title=validated["title"], description=validated.get("description", ""),
            suggested_topics=validated.get("suggested_topics", ""),
            document_type=validated["document_type"], rights_basis=validated["rights_basis"],
            rights_evidence=validated.get("rights_evidence", ""),
            author_or_owner=validated["author_or_owner"],
            permit_question_generation=True,
            permit_resource_display=validated.get("permit_resource_display", False),
            permit_tutor_use=validated.get("permit_tutor_use", False),
            original_filename=original_name, stored_key=key, file_type=file_type,
            size_bytes=size, sha256=sha, possible_duplicate=duplicate,
        )
        entry.full_clean()
        entry.save()
        return entry
    except Exception:
        # Database/save failure must not leave an untracked file behind.
        private_path(key).unlink(missing_ok=True)
        raise


@transaction.atomic
def withdraw_document(*, document_id, student):
    try:
        entry = DocumentSubmission.objects.select_for_update().get(pk=document_id, student=student)
    except DocumentSubmission.DoesNotExist:
        raise PermissionDenied("Document not found")
    if entry.state != DocumentSubmission.State.WITHDRAWN:
        entry.state = DocumentSubmission.State.WITHDRAWN
        entry.save(update_fields=["state", "updated_at"])
        _audit(entry, student, "withdrawn", "Contributor withdrew this document")
    # The private original remains isolated for retention review; never expose it.
    return entry


def scan_with_clamav(path):
    """Return clean/blocked/error. Fail closed; no allow-without-scanner mode."""
    try:
        result = subprocess.run(["clamscan", "--no-summary", str(path)],
                                capture_output=True, text=True, timeout=35, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return "error"
    return {0: "clean", 1: "blocked"}.get(result.returncode, "error")


def extract_text(path, file_type):
    """Bounded extraction. In production, execute in an isolated, resource-limited worker."""
    if file_type == "txt":
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        pages = 1
    else:
        from pypdf import PdfReader
        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted:
            raise IntakeConflict("Encrypted PDFs require separate review")
        if len(reader.pages) > 80:
            raise IntakeConflict("PDF exceeds the 80-page review limit")
        pages = len(reader.pages)
        fragments = []
        remaining = 100_000
        for page in reader.pages:
            if remaining <= 0:
                break
            extracted = (page.extract_text() or "")[:remaining]
            fragments.append(extracted)
            remaining -= len(extracted)
        text = "\n".join(fragments)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    if len(text.strip()) < 100:
        raise IntakeConflict("Document has too little extractable text; manual review/OCR may be needed")
    return text[:100_000], pages


def process_one(document_id):
    """Run from a private admin command, not public requests. Fail closed on every error."""
    with transaction.atomic():
        entry = DocumentSubmission.objects.select_for_update().get(pk=document_id)
        if entry.state in (DocumentSubmission.State.WITHDRAWN, DocumentSubmission.State.REJECTED, DocumentSubmission.State.APPROVED):
            return "skipped"
        if entry.scan_state not in (DocumentSubmission.ScanState.PENDING, DocumentSubmission.ScanState.ERROR):
            return "skipped"
        entry.scan_state = DocumentSubmission.ScanState.PROCESSING
        entry.save(update_fields=["scan_state", "updated_at"])
    path = private_path(entry.stored_key)
    result = scan_with_clamav(path)
    if result == "blocked":
        with transaction.atomic():
            current = DocumentSubmission.objects.select_for_update().get(pk=document_id)
            current.scan_state = DocumentSubmission.ScanState.BLOCKED
            current.state = DocumentSubmission.State.REJECTED
            current.save(update_fields=["scan_state", "state", "updated_at"])
        return "blocked"
    if result != "clean":
        with transaction.atomic():
            current = DocumentSubmission.objects.select_for_update().get(pk=document_id)
            current.scan_state = DocumentSubmission.ScanState.ERROR
            current.state = DocumentSubmission.State.PROCESSING_ERROR
            current.save(update_fields=["scan_state", "state", "updated_at"])
        return "scanner_error"
    try:
        text, pages = extract_text(path, entry.file_type)
    except Exception:
        with transaction.atomic():
            current = DocumentSubmission.objects.select_for_update().get(pk=document_id)
            current.scan_state = DocumentSubmission.ScanState.CLEAN
            current.extraction_state = DocumentSubmission.ExtractionState.ERROR
            current.state = DocumentSubmission.State.PROCESSING_ERROR
            current.save(update_fields=["scan_state", "extraction_state", "state", "updated_at"])
        return "extraction_error"
    with transaction.atomic():
        current = DocumentSubmission.objects.select_for_update().get(pk=document_id)
        current.scan_state = DocumentSubmission.ScanState.CLEAN
        current.extraction_state = DocumentSubmission.ExtractionState.DONE
        current.extracted_text = text
        current.page_count = pages
        if current.state != DocumentSubmission.State.WITHDRAWN:
            current.state = (DocumentSubmission.State.PENDING_REVIEW if current.unit_id else DocumentSubmission.State.NEEDS_MAPPING)
        current.save(update_fields=["scan_state", "extraction_state", "extracted_text", "page_count", "state", "updated_at"])
    return "ready"


@transaction.atomic
def review_document(*, document_id, actor, action, rationale, unit=None):
    """One narrow service for staff actions, with independent rights/academic approval."""
    entry = DocumentSubmission.objects.select_for_update().get(pk=document_id)
    if entry.state in (DocumentSubmission.State.REJECTED, DocumentSubmission.State.WITHDRAWN, DocumentSubmission.State.APPROVED):
        raise IntakeConflict("This submission is already closed")
    rationale = (rationale or "").strip()
    if len(rationale) < 25:
        raise IntakeConflict("A review rationale of at least 25 characters is required")
    if action == "map_unit":
        _require_reviewer(actor, "document_intake.map_document_units")
        if not unit or not _mapping_exists(entry.programme, unit):
            raise IntakeConflict("Staff must choose a unit already mapped to the selected programme")
        entry.unit = unit
        if entry.scan_state == entry.ScanState.CLEAN and entry.extraction_state == entry.ExtractionState.DONE:
            entry.state = entry.State.PENDING_REVIEW
        entry.save(update_fields=["unit", "state", "updated_at"])
    elif action in ("rights_clear", "rights_hold"):
        _require_reviewer(actor, "document_intake.review_document_rights")
        if entry.scan_state != entry.ScanState.CLEAN or entry.extraction_state != entry.ExtractionState.DONE:
            raise IntakeConflict("Document must pass security scanning and extraction first")
        if action == "rights_hold":
            entry.state = entry.State.RIGHTS_HOLD
            entry.save(update_fields=["state", "updated_at"])
        else:
            if entry.state != entry.State.PENDING_REVIEW or entry.rights_reviewed_by_id:
                raise IntakeConflict("Rights review unavailable for this submission")
            if entry.student_id == actor.pk:
                raise IntakeConflict("Uploader cannot review their own submission")
            entry.rights_reviewed_by = actor
            entry.rights_reviewed_at = timezone.now()
            entry.save(update_fields=["rights_reviewed_by", "rights_reviewed_at", "updated_at"])
    elif action in ("academic_approve", "reject"):
        _require_reviewer(actor, "document_intake.review_document_academic")
        if action == "reject":
            entry.state = entry.State.REJECTED
            entry.save(update_fields=["state", "updated_at"])
        else:
            if entry.state != entry.State.PENDING_REVIEW or not entry.unit_id:
                raise IntakeConflict("Document must have an approved unit mapping")
            if entry.scan_state != entry.ScanState.CLEAN or entry.extraction_state != entry.ExtractionState.DONE:
                raise IntakeConflict("Document has not passed file checks")
            if entry.possible_duplicate:
                raise IntakeConflict("Duplicate flag requires investigation and resolution outside this simple approval flow")
            if not entry.rights_reviewed_by_id or entry.rights_reviewed_by_id in (actor.pk, entry.student_id):
                raise IntakeConflict("An independent rights reviewer must approve first")
            if actor.pk == entry.student_id:
                raise IntakeConflict("Uploader cannot approve their own document")
            entry.academic_reviewed_by = actor
            entry.academic_reviewed_at = timezone.now()
            entry.state = entry.State.APPROVED
            entry.save(update_fields=["academic_reviewed_by", "academic_reviewed_at", "state", "updated_at"])
    else:
        raise IntakeConflict("Unknown review action")
    _audit(entry, actor, action, rationale)
    # Deliberately no QuestionRevision, SourceDocument or SourceExcerpt created.
    return entry


@transaction.atomic
def create_and_map_verified_unit(
    *, document_id, actor, curriculum_version, title, year_number,
    semester_number, rationale, catalogue_verified=False,
):
    """Explicit staff catalogue approval of a student-suggested unit.

    The catalogue is authoritative; suggestions do not auto-create units.
    Shared global Unit records are reused by exact title only after explicit
    staff confirmation. Writes and the mapping audit event are atomic.
    """
    _require_reviewer(actor, "document_intake.map_document_units")
    _require_reviewer(actor, "academics.add_curriculumunit")
    if not catalogue_verified:
        raise IntakeConflict("Confirm that the unit and curriculum placement have been verified")
    rationale = (rationale or "").strip()
    if len(rationale) < 25:
        raise IntakeConflict("A review rationale of at least 25 characters is required")
    normalized_title = re.sub(r"\s+", " ", title or "").strip()
    if len(normalized_title) < 4 or len(normalized_title) > 200:
        raise IntakeConflict("Enter a verified unit title of 4–200 characters")
    entry = DocumentSubmission.objects.select_for_update().get(pk=document_id)
    if entry.state in (entry.State.WITHDRAWN, entry.State.REJECTED, entry.State.APPROVED):
        raise IntakeConflict("This document is closed and cannot be mapped")
    if entry.unit_id:
        raise IntakeConflict("Document already has a verified unit; use the current mapping")

    # Lock the curriculum row so concurrent requests through this workflow
    # cannot add duplicate mappings for the same curriculum version.
    version = CurriculumVersion.objects.select_for_update().get(pk=curriculum_version.pk)
    if version.programme_id != entry.programme_id:
        raise IntakeConflict("Curriculum version does not belong to the submitted programme")

    candidates = list(Unit.objects.filter(title__iexact=normalized_title)[:2])
    if len(candidates) > 1:
        raise IntakeConflict("Multiple catalogue units share this title; resolve duplicates before mapping")
    created = False
    if candidates:
        unit = candidates[0]
    else:
        _require_reviewer(actor, "academics.add_unit")
        # Use a distinct slug so a similarly named unit does not cause a
        # collision; do not treat a suggested unit code as verified metadata.
        max_len = Unit._meta.get_field("slug").max_length or 200
        slug = f"{slugify(normalized_title)[:max(1, max_len - 9)]}-{uuid.uuid4().hex[:8]}"
        unit = Unit(title=normalized_title, slug=slug)
        unit.full_clean()
        unit.save()
        created = True

    mapping = CurriculumUnit.objects.filter(curriculum_version=version, unit=unit).first()
    if mapping is None:
        mapping = CurriculumUnit(
            curriculum_version=version, unit=unit,
            year_number=year_number, semester_number=semester_number,
        )
        mapping.full_clean()
        mapping.save()
    elif mapping.year_number != year_number or mapping.semester_number != semester_number:
        raise IntakeConflict("Existing curriculum placement differs; verify it before mapping")

    entry.unit = unit
    if entry.scan_state == entry.ScanState.CLEAN and entry.extraction_state == entry.ExtractionState.DONE:
        entry.state = entry.State.PENDING_REVIEW
    entry.save(update_fields=["unit", "state", "updated_at"])
    action = "unit_created_and_mapped" if created else "existing_unit_linked_and_mapped"
    audit_rationale = (
        f"{rationale} | curriculum={version.pk}; year={year_number}; "
        f"semester={semester_number}; suggested_code={entry.suggested_unit_code or '-'}"
    )
    _audit(entry, actor, action, audit_rationale)
    return entry, created
