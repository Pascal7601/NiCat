"""Server-side boundaries for past-paper OCR review and draft-only variations.

All content remains private. Never trust a front-end eligibility label.
"""
import hashlib
from difflib import SequenceMatcher
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.academics.models import Topic
from apps.document_intake.models import DocumentSubmission
from apps.question_generation.models import ExternalSourceAuthorization
from apps.question_generation.services import text_hash
from apps.question_generation.validation import normalize, validate_candidate
from apps.question_generation.provider import GenerationProviderError, generate_questions
from .extraction import suggest_question_chunks
from .models import PaperQuestionDraft, PaperReviewEvent, PaperVariationJob, PaperVariationCandidate


class PaperConflict(Exception):
    pass


def require_staff(actor, perm):
    if not (actor.is_authenticated and actor.is_active and actor.is_staff and actor.has_perm(perm)):
        raise PermissionDenied("Authorized past-paper staff only")


def is_eligible_paper(doc):
    return (
        doc.document_type == DocumentSubmission.DocumentType.AUTHORIZED_PAPER
        and doc.state == DocumentSubmission.State.APPROVED
        and doc.scan_state == DocumentSubmission.ScanState.CLEAN
        and doc.extraction_state == DocumentSubmission.ExtractionState.DONE
        and doc.unit_id is not None
        and doc.rights_reviewed_by_id is not None
        and doc.academic_reviewed_by_id is not None
        and doc.rights_reviewed_by_id != doc.academic_reviewed_by_id
        and not doc.possible_duplicate
        and bool((doc.extracted_text or "").strip())
        and doc.file_type == "pdf"
        and bool(doc.page_count) and 0 < doc.page_count <= 80
    )


def _paper_current(q):
    doc = q.document
    if not is_eligible_paper(doc):
        raise PaperConflict("Past paper has been withdrawn, changed, or is not fully approved")
    if doc.sha256 != q.source_sha256 or text_hash(doc.extracted_text) != q.extracted_sha256:
        raise PaperConflict("Original paper or OCR extraction changed; re-extract and reverify")
    return doc


def _event(actor, document, action, rationale, question=None, candidate=None):
    PaperReviewEvent.objects.create(actor=actor, document=document, action=action,
                                    rationale=rationale, question=question, candidate=candidate)


def _note(note, minimum=25):
    value = (note or "").strip()
    if len(value) < minimum or len(value) > 2500:
        raise PaperConflict(f"Provide a rationale of {minimum}–2500 characters")
    return value


@transaction.atomic
def extract_question_drafts(*, document_id, actor):
    require_staff(actor, "past_papers.extract_paper_questions")
    doc = DocumentSubmission.objects.select_for_update().get(pk=document_id)
    if not is_eligible_paper(doc):
        raise PaperConflict("Only clean, extracted, rights-cleared, academically approved past papers qualify")
    if doc.student_id == actor.pk:
        raise PaperConflict("The source uploader cannot extract and validate their own paper")
    existing = PaperQuestionDraft.objects.filter(document=doc)
    if existing.exists():
        # Avoid overwriting corrections, verification, or downstream jobs.
        raise PaperConflict("Questions already extracted; edit existing drafts or add one manually")
    chunks = suggest_question_chunks(doc.extracted_text)
    for i, (chunk, flags) in enumerate(chunks, 1):
        PaperQuestionDraft.objects.create(
            document=doc, position=i, source_sha256=doc.sha256,
            extracted_sha256=text_hash(doc.extracted_text), original_ocr_text=chunk,
            corrected_text=chunk, flags=flags, extracted_by=actor,
        )
    _event(actor, doc, "ocr_question_suggestions", f"Created {len(chunks)} unverified OCR candidates; page matching required")
    return len(chunks)


@transaction.atomic
def add_manual_question(*, document_id, actor, text, page_number):
    require_staff(actor, "past_papers.extract_paper_questions")
    doc = DocumentSubmission.objects.select_for_update().get(pk=document_id)
    if not is_eligible_paper(doc) or doc.student_id == actor.pk:
        raise PaperConflict("Document not eligible for staff reconstruction")
    text = (text or "").strip()
    if not 15 <= len(text) <= 2000:
        raise PaperConflict("Manual question text must have 15–2000 characters")
    if not page_number or not 1 <= page_number <= doc.page_count:
        raise PaperConflict("Select the original PDF page")
    last = PaperQuestionDraft.objects.filter(document=doc).order_by("-position").first()
    position = (last.position if last else 0) + 1
    if position > 100:
        raise PaperConflict("Maximum 100 reconstructed questions per paper")
    q = PaperQuestionDraft.objects.create(
        document=doc, position=position, source_sha256=doc.sha256,
        extracted_sha256=text_hash(doc.extracted_text), original_ocr_text="",
        corrected_text=text, page_number=page_number, extracted_by=actor,
        flags=["manual_transcription_unverified"],
    )
    _event(actor, doc, "manual_transcription", "New question transcribed from private original; not yet verified", question=q)
    return q


@transaction.atomic
def update_question(*, question_id, actor, corrected_text, page_number, marks,
                    topic_id, verified_answer_context, rationale):
    require_staff(actor, "past_papers.extract_paper_questions")
    q = PaperQuestionDraft.objects.select_for_update().select_related("document").get(pk=question_id)
    _paper_current(q)
    if q.state != q.State.DRAFT:
        raise PaperConflict("Verified/rejected questions are immutable; create a corrected replacement")
    if q.document.student_id == actor.pk:
        raise PaperConflict("The source uploader cannot correct their own submitted paper")
    rationale = _note(rationale)
    text = (corrected_text or "").strip()
    if not 15 <= len(text) <= 2000:
        raise PaperConflict("Corrected question must contain 15–2000 characters")
    if not 1 <= page_number <= q.document.page_count:
        raise PaperConflict("Select a page in the original PDF")
    topic = Topic.objects.get(pk=topic_id, unit_id=q.document.unit_id)
    answer = (verified_answer_context or "").strip()
    if len(answer) > 3500:
        raise PaperConflict("Reference material cannot exceed 3500 characters")
    if marks is not None and (marks <= Decimal("0") or marks > Decimal("100")):
        raise PaperConflict("Marks must be between 0 and 100")
    q.corrected_text, q.page_number, q.topic, q.verified_answer_context, q.marks = text, page_number, topic, answer, marks
    q.flags = ["pending_visual_verification"]
    q.save(update_fields=["corrected_text", "page_number", "topic", "verified_answer_context", "marks", "flags", "updated_at"])
    _event(actor, q.document, "ocr_corrected", rationale, question=q)
    return q


@transaction.atomic
def review_question(*, question_id, actor, action, rationale):
    require_staff(actor, "past_papers.verify_paper_questions")
    q = PaperQuestionDraft.objects.select_for_update().select_related("document", "topic").get(pk=question_id)
    _paper_current(q)
    if q.state != q.State.DRAFT:
        raise PaperConflict("Question was already reviewed")
    if actor.pk in (q.document.student_id, q.extracted_by_id):
        raise PaperConflict("A separate staff reviewer must compare the question with the original PDF")
    rationale = _note(rationale)
    if action == "verify":
        if not q.page_number or not q.topic_id or q.topic.unit_id != q.document.unit_id:
            raise PaperConflict("Verified question requires a PDF page and syllabus topic")
        if not 15 <= len(q.corrected_text.strip()) <= 2000:
            raise PaperConflict("Verified question text is missing or too long")
        # The reviewer must explicitly confirm the screenshot/page comparison in UI.
        q.state = q.State.VERIFIED
        q.flags = []
    elif action == "reject":
        q.state = q.State.REJECTED
    else:
        raise PaperConflict("Unknown verification action")
    q.verified_by, q.verified_at = actor, timezone.now()
    q.save(update_fields=["state", "flags", "verified_by", "verified_at", "updated_at"])
    _event(actor, q.document, "question_" + action, rationale, question=q)
    return q


def _verified_source(q):
    _paper_current(q)
    if q.state != q.State.VERIFIED or q.verified_by_id is None or not q.page_number or q.topic_id is None:
        raise PaperConflict("Question must be visually verified against the original PDF")
    if q.topic.unit_id != q.document.unit_id:
        raise PaperConflict("Question topic no longer belongs to paper's unit")
    if not q.document.permit_question_generation:
        raise PaperConflict("Question variations not authorized for this document")
    if len(q.verified_answer_context.strip()) < 60:
        raise PaperConflict("Verified reference/answer context (60+ characters) is required for variations")
    return q.document


def _question_digest(q):
    payload = "\n".join([q.corrected_text, q.verified_answer_context, str(q.page_number), str(q.topic_id)])
    return text_hash(payload)


def _vendor_authorized(job):
    if job.provider == "mock":
        return True
    if job.provider != "openai" or not getattr(settings, "NICAT_QUESTION_AI_REMOTE_ENABLED", False):
        return False
    doc = job.question.document
    auth = ExternalSourceAuthorization.objects.filter(
        document=doc, provider=job.provider, revoked_at__isnull=True,
        approved_source_hash=doc.sha256, approved_extracted_sha256=text_hash(doc.extracted_text),
    ).first()
    return bool(auth and auth.approved_by_id not in (
        doc.student_id, job.requested_by_id, job.question.verified_by_id
    ))


@transaction.atomic
def authorize_paper_external(*, document_id, actor, rationale, revoke=False):
    require_staff(actor, "question_generation.approve_external_question_ai")
    doc = DocumentSubmission.objects.select_for_update().get(pk=document_id)
    if not is_eligible_paper(doc) or not doc.permit_question_generation or doc.student_id == actor.pk:
        raise PaperConflict("Not eligible for independent external-vendor processing authorization")
    rationale = _note(rationale, minimum=40)
    if revoke:
        ExternalSourceAuthorization.objects.filter(document=doc, revoked_at__isnull=True).update(revoked_at=timezone.now())
        _event(actor, doc, "external_ai_revoked", rationale)
        return None
    provider = getattr(settings, "NICAT_QUESTION_AI_PROVIDER", "mock").lower()
    if provider != "openai":
        raise PaperConflict("Select the real provider before recording authorization")
    # Only after independent evidence establishes vendor/data-transfer and derivative-use rights.
    auth, _ = ExternalSourceAuthorization.objects.update_or_create(document=doc, defaults=dict(
        provider=provider, approved_source_hash=doc.sha256,
        approved_extracted_sha256=text_hash(doc.extracted_text),
        rationale=rationale, approved_by=actor, revoked_at=None,
    ))
    _event(actor, doc, "external_ai_authorized", rationale)
    return auth


@transaction.atomic
def queue_variations(*, question_id, actor, count, kind, difficulty):
    require_staff(actor, "past_papers.request_paper_variations")
    q = PaperQuestionDraft.objects.select_for_update().select_related("document", "topic").get(pk=question_id)
    doc = _verified_source(q)
    if actor.pk == doc.student_id:
        raise PaperConflict("Source uploader cannot request variations")
    if kind not in ("mcq", "short", "essay") or difficulty not in ("easy", "medium", "hard") or not 1 <= count <= 3:
        raise PaperConflict("Choose 1–3 variations of a supported kind/difficulty")
    provider = getattr(settings, "NICAT_QUESTION_AI_PROVIDER", "mock").lower()
    if provider not in ("mock", "openai"):
        raise PaperConflict("Unsupported provider")
    job = PaperVariationJob(
        question=q, requested_by=actor, provider=provider,
        model_name=(getattr(settings, "NICAT_QUESTION_AI_MODEL", "") if provider != "mock" else "mock"),
        count=count, kind=kind, difficulty=difficulty, source_sha256=doc.sha256,
        extracted_sha256=text_hash(doc.extracted_text), verified_question_sha256=_question_digest(q),
    )
    if not _vendor_authorized(job):
        raise PaperConflict("Independent document-specific external AI processing authorization required")
    job.save()
    _event(actor, doc, "variations_queued", f"Requested {count} {kind} variations from verified question", question=q)
    return job


def check_variation_job(job):
    q = job.question
    doc = _verified_source(q)
    if doc.sha256 != job.source_sha256 or text_hash(doc.extracted_text) != job.extracted_sha256 or _question_digest(q) != job.verified_question_sha256:
        raise PaperConflict("Verified paper/answer reference changed")
    if not _vendor_authorized(job):
        raise PaperConflict("External processing authorization expired/revoked")
    return doc


def variation_source_text(q):
    """Verified material only, not unreviewed OCR fragments or other paper pages."""
    return (
        "VERIFIED ORIGINAL QUESTION (for concept only; do not copy verbatim):\n"
        + q.corrected_text + "\nVERIFIED ANSWER/REFERENCE CONTEXT:\n"
        + q.verified_answer_context + "\n"
        + "Write a NEW practice variation with the same learning objective. "
        + "Do not reproduce the original question verbatim."
    )


def process_variation_job(job_id):
    changed = PaperVariationJob.objects.filter(pk=job_id, state=PaperVariationJob.State.QUEUED).update(state=PaperVariationJob.State.RUNNING)
    if not changed:
        return "skipped"
    job = PaperVariationJob.objects.select_related("question__document", "question__topic").get(pk=job_id)
    try:
        check_variation_job(job)
        source = variation_source_text(job.question)
    except PaperConflict:
        PaperVariationJob.objects.filter(pk=job_id, state=job.State.RUNNING).update(state=job.State.BLOCKED, failure_code="source_invalid", finished_at=timezone.now())
        return "blocked"
    try:
        result = generate_questions(source_text=source, count=job.count, kind=job.kind,
                                    difficulty=job.difficulty, topic=job.question.topic.title)
        if not isinstance(result, list) or not result or len(result) > job.count:
            raise GenerationProviderError("Invalid provider output")
    except Exception:
        # Fail closed and avoid logging protected source text or credentials.
        PaperVariationJob.objects.filter(pk=job_id, state=job.State.RUNNING).update(state=job.State.FAILED, failure_code="provider_error", finished_at=timezone.now())
        return "failed"
    with transaction.atomic():
        job = PaperVariationJob.objects.select_for_update().select_related("question__document", "question__topic").get(pk=job_id)
        try:
            check_variation_job(job)
        except PaperConflict:
            job.state, job.failure_code = job.State.BLOCKED, "source_revoked_during_generation"
            job.finished_at = timezone.now()
            job.save(update_fields=["state", "failure_code", "finished_at"])
            return "blocked"
        for idx, data in enumerate(result, 1):
            if not isinstance(data, dict):
                continue
            values = {key: data.get(key) for key in ("kind", "prompt", "options", "correct_index", "explanation", "rubric", "evidence_quote")}
            problems = validate_candidate(values, source)
            # Evidence must support an answer, not merely quote the original
            # question or the instruction appended to the prompt.
            if normalize(str(values.get("evidence_quote") or "")) not in normalize(job.question.verified_answer_context):
                problems.append("answer_reference_quote_missing")
            prompt = str(values.get("prompt") or "")[:1600]
            if normalize(prompt) == normalize(job.question.corrected_text) or SequenceMatcher(None, normalize(prompt), normalize(job.question.corrected_text)).ratio() > 0.90:
                problems.append("too_similar_to_original")
            if job.provider == "mock":
                problems.append("mock_test_data")
            raw_options = values.get("options")
            safe_options = ([option[:350] for option in raw_options[:4]]
                            if isinstance(raw_options, list) and all(isinstance(option, str) for option in raw_options[:4])
                            else [])
            raw_rubric = values.get("rubric")
            safe_rubric = raw_rubric[:8] if isinstance(raw_rubric, list) and all(isinstance(row, dict) for row in raw_rubric[:8]) else []
            PaperVariationCandidate.objects.create(
                job=job, position=idx,
                kind=values.get("kind") if values.get("kind") in ("mcq", "short", "essay") else job.kind,
                prompt=prompt,
                options=safe_options,
                correct_index=values.get("correct_index") if type(values.get("correct_index")) is int and values.get("correct_index") in range(4) else None,
                explanation=str(values.get("explanation") or "")[:4000],
                rubric=safe_rubric,
                evidence_quote=str(values.get("evidence_quote") or "")[:650],
                validation_errors=sorted(set(problems)),
            )
        job.state = job.State.COMPLETE
        job.finished_at = timezone.now()
        job.save(update_fields=["state", "finished_at"])
    return "complete"


@transaction.atomic
def edit_variation(*, candidate_id, actor, values, note):
    require_staff(actor, "past_papers.review_paper_variations")
    c = PaperVariationCandidate.objects.select_for_update().select_related("job__question__document", "job__question__topic").get(pk=candidate_id)
    if c.state != c.State.DRAFT or c.job.provider == "mock":
        raise PaperConflict("Only real-provider draft variations may be corrected")
    if actor.pk in (c.job.requested_by_id, c.job.question.document.student_id):
        raise PaperConflict("Independent academic reviewer required")
    check_variation_job(c.job)
    note = _note(note)
    for field in ("kind", "prompt", "options", "correct_index", "explanation", "rubric", "evidence_quote"):
        if field in values:
            setattr(c, field, values[field])
    c.validation_errors = validate_candidate({key: getattr(c, key) for key in (
        "kind", "prompt", "options", "correct_index", "explanation", "rubric", "evidence_quote"
    )}, variation_source_text(c.job.question))
    if normalize(c.evidence_quote) not in normalize(c.job.question.verified_answer_context):
        c.validation_errors.append("answer_reference_quote_missing")
    if SequenceMatcher(None, normalize(c.prompt), normalize(c.job.question.corrected_text)).ratio() > 0.90:
        c.validation_errors.append("too_similar_to_original")
    c.validation_errors = sorted(set(c.validation_errors))
    c.save()
    _event(actor, c.job.question.document, "variation_edited", note, question=c.job.question, candidate=c)
    return c


@transaction.atomic
def review_variation(*, candidate_id, actor, action, note):
    require_staff(actor, "past_papers.review_paper_variations")
    c = PaperVariationCandidate.objects.select_for_update().select_related("job__question__document", "job__question__topic").get(pk=candidate_id)
    if c.state != c.State.DRAFT:
        raise PaperConflict("Candidate already decided")
    if actor.pk in (c.job.requested_by_id, c.job.question.document.student_id):
        raise PaperConflict("Independent academic reviewer required")
    note = _note(note)
    if action == "approve":
        check_variation_job(c.job)
        if c.job.provider == "mock" or "mock_test_data" in c.validation_errors:
            raise PaperConflict("Mock variations can never be approved")
        if c.validation_errors:
            raise PaperConflict("Candidate has outstanding validation flags")
        source = variation_source_text(c.job.question)
        if validate_candidate({key: getattr(c, key) for key in (
            "kind", "prompt", "options", "correct_index", "explanation", "rubric", "evidence_quote"
        )}, source):
            raise PaperConflict("Candidate failed revalidation")
        if normalize(c.evidence_quote) not in normalize(c.job.question.verified_answer_context):
            raise PaperConflict("Variation evidence quote does not match verified answer reference")
        if SequenceMatcher(None, normalize(c.prompt), normalize(c.job.question.corrected_text)).ratio() > 0.90:
            raise PaperConflict("Variation is too similar to the original paper question")
        c.state = c.State.APPROVED
    elif action == "reject":
        c.state = c.State.REJECTED
    else:
        raise PaperConflict("Unknown candidate review action")
    c.reviewed_by, c.reviewed_at, c.review_note = actor, timezone.now(), note
    c.save(update_fields=["state", "reviewed_by", "reviewed_at", "review_note"])
    _event(actor, c.job.question.document, "variation_" + action, note, question=c.job.question, candidate=c)
    return c
