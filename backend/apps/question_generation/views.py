"""Staff-only generation controls; no student access or public answer leakage."""
import hashlib
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.academics.models import Topic
from apps.document_intake.models import DocumentSubmission
from .models import QuestionGenerationJob, GeneratedQuestionCandidate
from .services import (require_staff, valid_source, queue_job, review_candidate,
                       edit_candidate, import_candidate, authorize_external,
                       GenerationConflict)


def gate():
    if not getattr(settings, 'NICAT_QUESTION_GENERATION_ENABLED', False):
        return Response({'code':'disabled'}, status=404)
    return None


def staff_reader(user):
    if not user.is_authenticated or not user.is_active or not user.is_staff:
        raise PermissionDenied('Staff only')
    if not (user.has_perm('question_generation.request_question_generation') or
            user.has_perm('question_generation.review_question_candidate') or
            user.has_perm('question_generation.import_question_candidate')):
        raise PermissionDenied('Question-generation reviewer permission required')


def serialize_candidate(c):
    return dict(id=str(c.pk), position=c.position, kind=c.kind, prompt=c.prompt,
                options=c.options, correct_index=c.correct_index, explanation=c.explanation,
                rubric=c.rubric, evidence_quote=c.evidence_quote,
                validation_errors=c.validation_errors, state=c.state,
                review_note=c.review_note,
                bank_revision_id=str(c.bank_revision_id) if c.bank_revision_id else None)


def serialize_job(job, include_candidates=False):
    result = dict(id=str(job.pk), document=str(job.document_id),
                  document_title=job.document.title, topic=job.topic.title,
                  count=job.count, kind=job.kind, difficulty=job.difficulty,
                  provider=job.provider, model_name=job.model_name,
                  state=job.state, failure_code=job.failure_code,
                  created_at=job.created_at.isoformat())
    if include_candidates:
        result['candidates'] = [serialize_candidate(c) for c in job.candidates.all()]
    return result


class JobSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    topic_id = serializers.UUIDField()
    count = serializers.IntegerField(min_value=1, max_value=5)
    kind = serializers.ChoiceField(choices=QuestionGenerationJob.Kind.choices)
    difficulty = serializers.ChoiceField(choices=['easy','medium','hard','mixed'])


class ActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve','reject','import'])
    note = serializers.CharField(required=False, max_length=2500, allow_blank=True)


class EditSerializer(serializers.Serializer):
    prompt = serializers.CharField(min_length=15, max_length=1600)
    kind = serializers.ChoiceField(choices=['mcq','short','essay'])
    options = serializers.ListField(child=serializers.CharField(max_length=350), required=True)
    correct_index = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=3)
    explanation = serializers.CharField(min_length=20, max_length=4000)
    rubric = serializers.ListField(child=serializers.DictField(), required=True)
    evidence_quote = serializers.CharField(min_length=15, max_length=650)
    note = serializers.CharField(min_length=25, max_length=2500)


class RemoteReviewSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    rationale = serializers.CharField(min_length=40, max_length=2500)
    revoke = serializers.BooleanField(default=False)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sources(request):
    off = gate()
    if off is not None:
        return off
    require_staff(request.user, 'question_generation.request_question_generation')
    docs = DocumentSubmission.objects.filter(
        state=DocumentSubmission.State.APPROVED,
        scan_state=DocumentSubmission.ScanState.CLEAN,
        extraction_state=DocumentSubmission.ExtractionState.DONE,
        permit_question_generation=True,
    ).select_related('programme','unit').order_by('-created_at')[:150]
    items = [dict(id=str(d.pk), title=d.title, unit=d.unit.title,
                  unit_id=str(d.unit_id), programme=d.programme.name,
                  external_authorized=hasattr(d,'external_question_ai_authorization') and
                      d.external_question_ai_authorization.revoked_at is None and
                      d.external_question_ai_authorization.approved_source_hash == d.sha256 and
                      d.external_question_ai_authorization.approved_extracted_sha256 == hashlib.sha256(d.extracted_text.encode('utf-8')).hexdigest() and
                      d.external_question_ai_authorization.provider == getattr(settings,'NICAT_QUESTION_AI_PROVIDER','mock'))
             for d in docs if valid_source(d)]
    topic_ids = {d['unit_id'] for d in items}
    topics = [dict(id=str(t.pk), unit_id=str(t.unit_id), title=t.title)
              for t in Topic.objects.filter(unit_id__in=topic_ids).order_by('title')[:400]]
    return Response(dict(items=items, topics=topics,
                         provider=getattr(settings,'NICAT_QUESTION_AI_PROVIDER','mock')))


@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def jobs(request):
    off = gate()
    if off is not None:
        return off
    if request.method == 'GET':
        staff_reader(request.user)
        result = QuestionGenerationJob.objects.select_related('document','topic').order_by('-created_at')[:50]
        return Response({'items':[serialize_job(j) for j in result]})
    require_staff(request.user,'question_generation.request_question_generation')
    ser=JobSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    try:
        job=queue_job(actor=request.user,**ser.validated_data)
    except (DocumentSubmission.DoesNotExist,Topic.DoesNotExist):
        return Response({'code':'not_found'},status=404)
    except GenerationConflict as e:
        return Response({'code':'conflict','message':str(e)},status=409)
    return Response(serialize_job(job),status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def job_detail(request, job_id):
    off=gate()
    if off is not None:
        return off
    staff_reader(request.user)
    job=get_object_or_404(QuestionGenerationJob.objects.select_related('document','topic').prefetch_related('candidates'),pk=job_id)
    return Response(serialize_job(job,include_candidates=True))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def candidate_edit(request, candidate_id):
    off=gate()
    if off is not None:
        return off
    require_staff(request.user,'question_generation.review_question_candidate')
    ser=EditSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    values=ser.validated_data.copy()
    note=values.pop('note')
    try:
        result=edit_candidate(candidate_id=candidate_id,actor=request.user,values=values,note=note)
    except GeneratedQuestionCandidate.DoesNotExist:
        return Response({'code':'not_found'},status=404)
    except GenerationConflict as e:
        return Response({'code':'conflict','message':str(e)},status=409)
    return Response(serialize_candidate(result))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def candidate_action(request, candidate_id):
    off=gate()
    if off is not None:
        return off
    ser=ActionSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    action=ser.validated_data['action']
    try:
        if action=='import':
            result=import_candidate(candidate_id=candidate_id,actor=request.user)
            return Response({'bank_revision_id':str(result.pk),'status':'published'})
        result=review_candidate(candidate_id=candidate_id,actor=request.user,
                                action=action,note=ser.validated_data.get('note',''))
    except GeneratedQuestionCandidate.DoesNotExist:
        return Response({'code':'not_found'},status=404)
    except GenerationConflict as e:
        return Response({'code':'conflict','message':str(e)},status=409)
    return Response(serialize_candidate(result))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def external_authorization(request):
    off=gate()
    if off is not None:
        return off
    require_staff(request.user,'question_generation.approve_external_question_ai')
    ser=RemoteReviewSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    try:
        auth=authorize_external(actor=request.user,**ser.validated_data)
    except DocumentSubmission.DoesNotExist:
        return Response({'code':'not_found'},status=404)
    except GenerationConflict as e:
        return Response({'code':'conflict','message':str(e)},status=409)
    return Response({'authorized':bool(auth)})
