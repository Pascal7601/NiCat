"""The sole authoritative boundary for generation, review and safe bank import."""
import hashlib
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.academics.models import Topic
from apps.document_intake.models import DocumentSubmission
from apps.questions.models import ChoiceOption, Question, QuestionRevision
from .models import (ExternalSourceAuthorization, QuestionGenerationJob,
                     GeneratedQuestionCandidate, QuestionGenerationEvent)
from .provider import generate_questions, GenerationProviderError
from .validation import validate_candidate, fingerprint


class GenerationConflict(Exception):
    pass


def require_staff(user, perm):
    if not user.is_authenticated or not user.is_active or not user.is_staff or not user.has_perm(perm):
        raise PermissionDenied('Staff authorization required')


def text_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def valid_source(doc):
    return (
        doc.state == DocumentSubmission.State.APPROVED
        and doc.scan_state == DocumentSubmission.ScanState.CLEAN
        and doc.extraction_state == DocumentSubmission.ExtractionState.DONE
        and doc.unit_id is not None
        and bool(doc.permit_question_generation)
        and bool(doc.rights_reviewed_by_id)
        and bool(doc.academic_reviewed_by_id)
        and doc.rights_reviewed_by_id != doc.academic_reviewed_by_id
        and bool(doc.extracted_text.strip())
        and not doc.possible_duplicate
    )


def check_source(job):
    doc = job.document
    if not valid_source(doc):
        raise GenerationConflict('Document is not currently approved for question drafting')
    if doc.sha256 != job.source_sha256 or text_hash(doc.extracted_text) != job.extracted_sha256:
        raise GenerationConflict('Source changed since job creation')
    if job.topic.unit_id != doc.unit_id:
        raise GenerationConflict('Question topic no longer matches the document unit')
    if job.provider != 'mock':
        if not getattr(settings, 'NICAT_QUESTION_AI_REMOTE_ENABLED', False):
            raise GenerationConflict('Remote AI disabled')
        auth = ExternalSourceAuthorization.objects.filter(
            document=doc, provider=job.provider, revoked_at__isnull=True,
            approved_source_hash=doc.sha256, approved_extracted_sha256=text_hash(doc.extracted_text),
        ).first()
        if auth is None or auth.approved_by_id in (doc.student_id, job.requested_by_id):
            raise GenerationConflict('Independent vendor-processing authorization missing')
    return doc


@transaction.atomic
def authorize_external(*, document_id, actor, rationale, revoke=False):
    require_staff(actor, 'question_generation.approve_external_question_ai')
    doc = DocumentSubmission.objects.select_for_update().get(pk=document_id)
    if doc.student_id == actor.pk:
        raise GenerationConflict('Contributors cannot authorize external processing of their own materials')
    if not revoke and not valid_source(doc):
        raise GenerationConflict('Only fully reviewed documents can be authorized')
    if len((rationale or '').strip()) < 40:
        raise GenerationConflict('Record a detailed 40+ character vendor/data-rights review rationale')
    if revoke:
        ExternalSourceAuthorization.objects.filter(document=doc, revoked_at__isnull=True).update(revoked_at=timezone.now())
        return None
    provider = getattr(settings, 'NICAT_QUESTION_AI_PROVIDER', 'mock').lower()
    if provider != 'openai':
        raise GenerationConflict('Choose a supported real provider before recording authorization')
    auth, _ = ExternalSourceAuthorization.objects.update_or_create(
        document=doc, defaults=dict(provider=provider, approved_source_hash=doc.sha256, approved_extracted_sha256=text_hash(doc.extracted_text),
                                     rationale=rationale.strip(), approved_by=actor,
                                     revoked_at=None),
    )
    return auth


@transaction.atomic
def queue_job(*, document_id, topic_id, count, kind, difficulty, actor):
    require_staff(actor, 'question_generation.request_question_generation')
    doc = DocumentSubmission.objects.select_for_update().get(pk=document_id)
    if not valid_source(doc):
        raise GenerationConflict('Upload must pass scanning, mapping, rights and academic review')
    topic = Topic.objects.get(pk=topic_id, unit_id=doc.unit_id)
    if not 1 <= count <= 5:
        raise GenerationConflict('Choose 1–5 questions per job')
    if kind not in QuestionGenerationJob.Kind.values or difficulty not in ('easy','medium','hard','mixed'):
        raise GenerationConflict('Invalid question generation configuration')
    provider = getattr(settings, 'NICAT_QUESTION_AI_PROVIDER', 'mock').lower()
    job = QuestionGenerationJob.objects.create(
        document=doc, topic=topic, count=count, kind=kind, difficulty=difficulty,
        requested_by=actor, provider=provider,
        model_name=getattr(settings, 'NICAT_QUESTION_AI_MODEL', '') if provider != 'mock' else 'mock',
        source_sha256=doc.sha256, extracted_sha256=text_hash(doc.extracted_text),
    )
    check_source(job)  # Revalidate individual approval for remote processing.
    return job


def process_job(job_id):
    """Claim -> outbound call (no DB transaction) -> revalidate and save candidates."""
    with transaction.atomic():
        changed = QuestionGenerationJob.objects.filter(pk=job_id, state=QuestionGenerationJob.State.QUEUED).update(
            state=QuestionGenerationJob.State.RUNNING
        )
        if not changed:
            return 'skipped'
        job = QuestionGenerationJob.objects.select_related('document','topic').get(pk=job_id)
        try:
            doc = check_source(job)
            context = doc.extracted_text[:6500]
        except GenerationConflict:
            job.state = QuestionGenerationJob.State.BLOCKED
            job.failure_code = 'source_not_eligible'
            job.finished_at = timezone.now()
            job.save(update_fields=['state','failure_code','finished_at'])
            return 'blocked'
    try:
        results = generate_questions(source_text=context, count=job.count,
                                     kind=job.kind, difficulty=job.difficulty, topic=job.topic.title)
        if not isinstance(results, list) or not results or len(results) > job.count:
            raise GenerationProviderError('Invalid provider response')
    except GenerationProviderError:
        QuestionGenerationJob.objects.filter(pk=job_id, state=QuestionGenerationJob.State.RUNNING).update(
            state=QuestionGenerationJob.State.FAILED, failure_code='provider_error', finished_at=timezone.now())
        return 'failed'
    with transaction.atomic():
        job = QuestionGenerationJob.objects.select_for_update().select_related('document','topic').get(pk=job_id)
        try:
            doc = check_source(job)
        except GenerationConflict:
            job.state = QuestionGenerationJob.State.BLOCKED
            job.failure_code = 'source_revoked_during_generation'
            job.finished_at = timezone.now()
            job.save(update_fields=['state','failure_code','finished_at'])
            return 'blocked'
        for i, raw in enumerate(results[:job.count], start=1):
            if not isinstance(raw, dict):
                continue
            data = {key:raw.get(key) for key in ('kind','prompt','options','correct_index','explanation','rubric','evidence_quote')}
            problems = validate_candidate(data, doc.extracted_text[:6500])
            if job.provider == 'mock':
                problems.append('mock_test_data')
            # Only fields of expected type enter database; no model-supplied review state or IDs.
            GeneratedQuestionCandidate.objects.create(
                job=job, position=i, kind=data['kind'] if data['kind'] in ('mcq','short','essay') else 'mcq',
                prompt=str(data.get('prompt') or '')[:1600],
                options=data.get('options') if isinstance(data.get('options'),list) else [],
                correct_index=data.get('correct_index') if type(data.get('correct_index')) is int and data['correct_index']>=0 else None,
                explanation=str(data.get('explanation') or '')[:4000],
                rubric=data.get('rubric') if isinstance(data.get('rubric'),list) else [],
                evidence_quote=str(data.get('evidence_quote') or '')[:650],
                validation_errors=sorted(set(problems)),
                prompt_sha256=fingerprint(str(data.get('prompt') or '')),
            )
        job.state = QuestionGenerationJob.State.COMPLETE
        job.finished_at = timezone.now()
        job.save(update_fields=['state','finished_at'])
    return 'complete'


@transaction.atomic
def edit_candidate(*, candidate_id, actor, values, note):
    require_staff(actor, 'question_generation.review_question_candidate')
    candidate = GeneratedQuestionCandidate.objects.select_for_update().select_related('job__document','job__topic').get(pk=candidate_id)
    if candidate.state != candidate.State.DRAFT:
        raise GenerationConflict('Only review-stage candidates can be edited')
    if candidate.job.provider == 'mock':
        raise GenerationConflict('Mock test candidates are immutable and never eligible for publication')
    check_source(candidate.job)
    if candidate.job.requested_by_id == actor.pk or candidate.job.document.student_id == actor.pk:
        raise GenerationConflict('Independent reviewer required')
    if len((note or '').strip()) < 25:
        raise GenerationConflict('Provide an academic correction rationale (25+ characters)')
    for key in ('prompt','kind','options','correct_index','explanation','rubric','evidence_quote'):
        if key in values:
            setattr(candidate,key,values[key])
    candidate.validation_errors = validate_candidate(values | {
        key:getattr(candidate,key) for key in ('prompt','kind','options','correct_index','explanation','rubric','evidence_quote')
    }, candidate.job.document.extracted_text[:6500])
    candidate.prompt_sha256 = fingerprint(candidate.prompt)
    candidate.save()
    QuestionGenerationEvent.objects.create(candidate=candidate,actor=actor,action='edited',note=note.strip())
    return candidate


@transaction.atomic
def review_candidate(*, candidate_id, actor, action, note):
    require_staff(actor, 'question_generation.review_question_candidate')
    candidate = GeneratedQuestionCandidate.objects.select_for_update().select_related('job__document','job__topic').get(pk=candidate_id)
    if candidate.state != candidate.State.DRAFT:
        raise GenerationConflict('Candidate was already reviewed')
    if candidate.job.requested_by_id == actor.pk or candidate.job.document.student_id == actor.pk:
        raise GenerationConflict('An independent reviewer must decide')
    if len((note or '').strip()) < 25:
        raise GenerationConflict('Explain your academic decision (25+ characters)')
    if action == 'approve':
        check_source(candidate.job)
        if candidate.job.provider == 'mock' or 'mock_test_data' in candidate.validation_errors:
            raise GenerationConflict('Mock-generated candidates are never publishable')
        fresh = validate_candidate({key:getattr(candidate,key) for key in (
            'prompt','kind','options','correct_index','explanation','rubric','evidence_quote')}, candidate.job.document.extracted_text[:6500])
        if fresh:
            raise GenerationConflict('Candidate failed validation: ' + ', '.join(fresh))
        # Check literal duplicates in the live question bank as well as approved candidates.
        if QuestionRevision.objects.filter(prompt__iexact=candidate.prompt).exists():
            raise GenerationConflict('Question prompt already exists in the question bank')
        # Exact duplicate fingerprint in another candidate, including imported.
        if GeneratedQuestionCandidate.objects.exclude(pk=candidate.pk).filter(prompt_sha256=candidate.prompt_sha256,
                                                       state__in=[candidate.State.APPROVED,candidate.State.IMPORTED]).exists():
            raise GenerationConflict('An approved candidate already has this prompt')
        candidate.state = candidate.State.APPROVED
    elif action == 'reject':
        candidate.state = candidate.State.REJECTED
    else:
        raise GenerationConflict('Unknown review action')
    candidate.reviewed_at = timezone.now()
    candidate.reviewed_by = actor
    candidate.review_note = note.strip()
    candidate.save(update_fields=['state','reviewed_at','reviewed_by','review_note'])
    QuestionGenerationEvent.objects.create(candidate=candidate,actor=actor,action=action,note=note.strip())
    return candidate


def import_candidate(*, candidate_id, actor):
    """Only reviewed REAL MCQs are safely imported to a published revision.

    Written rubric mapping requires reconciling the current RubricCriterion model.
    Do not guess fields or create ungradeable written questions.
    """
    require_staff(actor, 'question_generation.import_question_candidate')
    require_staff(actor, 'questions.add_question')
    require_staff(actor, 'questions.add_questionrevision')
    require_staff(actor, 'questions.change_questionrevision')
    with transaction.atomic():
        candidate = GeneratedQuestionCandidate.objects.select_for_update().select_related('job__document','job__topic').get(pk=candidate_id)
        if candidate.state == candidate.State.IMPORTED and candidate.bank_revision_id:
            return candidate.bank_revision
        if candidate.state != candidate.State.APPROVED:
            raise GenerationConflict('Candidate requires independent approval first')
        if candidate.kind != 'mcq':
            raise GenerationConflict('Written-question rubric import requires the existing QuestionRevision/RubricCriterion contract')
        job = candidate.job
        check_source(job)
        if job.provider == 'mock':
            raise GenerationConflict('Mock question cannot be imported')
        if validate_candidate({key:getattr(candidate,key) for key in (
            'prompt','kind','options','correct_index','explanation','rubric','evidence_quote')}, job.document.extracted_text[:6500]):
            raise GenerationConflict('Invalid candidate data')
        if QuestionRevision.objects.filter(prompt__iexact=candidate.prompt).exists():
            raise GenerationConflict('Question prompt already exists in the question bank')
        # Never mislabel AI-generated material as staff-original content.
        ai_values = [value for value,label in QuestionRevision.Provenance.choices
                     if 'ai' in str(value).lower() or 'generat' in str(value).lower()]
        if not ai_values:
            raise GenerationConflict('Add an explicit AI-generated provenance to QuestionRevision before importing')
        question = Question.objects.create(topic=job.topic)
        revision = QuestionRevision.objects.create(
            question=question, number=1, kind=QuestionRevision.Kind.SINGLE_CHOICE,
            provenance=ai_values[0], prompt=candidate.prompt, max_marks=Decimal('1.00'),
        )
        for i, option in enumerate(candidate.options, start=1):
            ChoiceOption.objects.create(revision=revision, text=option, position=i, is_correct=(i-1)==candidate.correct_index)
        revision.status = QuestionRevision.Status.PUBLISHED
        revision.reviewed_by = actor
        revision.save()
        candidate.state = candidate.State.IMPORTED
        candidate.bank_revision = revision
        candidate.save(update_fields=['state','bank_revision'])
        QuestionGenerationEvent.objects.create(candidate=candidate,actor=actor,action='imported',
                                               note='Source-grounded real candidate imported as published revision')
        return revision
