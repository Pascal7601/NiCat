"""Sprint 14: private candidate generation, authorization, review and revocation."""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from apps.academics.models import Topic
from apps.document_intake.models import DocumentSubmission
from apps.document_intake.services import review_document, process_one
from apps.question_generation.models import QuestionGenerationJob, GeneratedQuestionCandidate
from apps.question_generation.services import (
    authorize_external, queue_job, process_job, review_candidate, GenerationConflict,
)
from .test_document_intake import intake  # shared fixture, registered in this module

BASE='/api/v1/question-generation/'


def client_for(user):
    client=APIClient();client.force_authenticate(user=user);return client


def grant(user, codename):
    user.user_permissions.add(Permission.objects.get(content_type__app_label='question_generation',codename=codename))


@pytest.fixture
def verified(intake,monkeypatch):
    owner, outsider, rights, academic, programme, unit, data, root=intake
    User=get_user_model()
    requester=User.objects.create_user(email='qgen-requester@example.test', password='GoodPass123!',is_staff=True)
    reviewer=User.objects.create_user(email='qgen-reviewer@example.test', password='GoodPass123!',is_staff=True)
    grant(requester,'request_question_generation')
    grant(reviewer,'review_question_candidate')
    grant(rights,'approve_external_question_ai')
    topic=Topic.objects.create(unit=unit,title='Translation in Computer Graphics')
    with override_settings(NICAT_DOCUMENT_PRIVATE_ROOT=root, NICAT_DOCUMENT_INTAKE_ENABLED=True):
        payload=('Coordinate translation adds horizontal and vertical offsets to a point in a Cartesian plane. '*10).encode()
        response=client_for(owner).post('/api/v1/document-intake/',{
            **data,'file':SimpleUploadedFile('graphics.txt',payload,content_type='text/plain')},format='multipart')
        assert response.status_code==201,response.data
        docid=response.data['id']
        monkeypatch.setattr('apps.document_intake.services.scan_with_clamav',lambda path:'clean')
        assert process_one(docid)=='ready'
        reason='Verified student authorship, educational permission and academic topic alignment.'
        review_document(document_id=docid,actor=rights,action='rights_clear',rationale=reason)
        review_document(document_id=docid,actor=academic,action='academic_approve',rationale=reason)
    doc=DocumentSubmission.objects.get(pk=docid)
    return owner,outsider,rights,academic,requester,reviewer,doc,topic,root


@pytest.mark.django_db
def test_mock_drafts_cannot_be_approved_and_no_question_bank_entry(verified):
    owner,outsider,rights,academic,requester,reviewer,doc,topic,root=verified
    with override_settings(NICAT_QUESTION_GENERATION_ENABLED=True,NICAT_QUESTION_AI_PROVIDER='mock',NICAT_DOCUMENT_PRIVATE_ROOT=root):
        assert client_for(outsider).get(BASE+'sources/').status_code==403
        response=client_for(requester).post(BASE+'jobs/',{'document_id':str(doc.pk),'topic_id':str(topic.pk),
             'count':2,'kind':'mixed','difficulty':'easy'},format='json')
        assert response.status_code==201,response.data
        jobid=response.data['id']
        assert process_job(jobid)=='complete'
        job=QuestionGenerationJob.objects.get(pk=jobid)
        assert job.candidates.count()==2
        candidate=job.candidates.first()
        assert 'mock_test_data' in candidate.validation_errors
        with pytest.raises(GenerationConflict,match='Mock'):
            review_candidate(candidate_id=candidate.pk,actor=reviewer,action='approve',note='Academic content verified against the material.')
        rejected=review_candidate(candidate_id=candidate.pk,actor=reviewer,action='reject',note='Mock answer is not real academic content.')
        assert rejected.state==GeneratedQuestionCandidate.State.REJECTED
        from apps.questions.models import Question
        assert not Question.objects.filter(topic=topic).exists()


@pytest.mark.django_db
def test_remote_provider_requires_explicit_independent_document_authorization(verified,monkeypatch):
    owner,outsider,rights,academic,requester,reviewer,doc,topic,root=verified
    cfg=dict(NICAT_QUESTION_GENERATION_ENABLED=True,NICAT_QUESTION_AI_PROVIDER='openai',
             NICAT_QUESTION_AI_REMOTE_ENABLED=True,NICAT_QUESTION_AI_MODEL='test-only',
             NICAT_DOCUMENT_PRIVATE_ROOT=root)
    with override_settings(**cfg):
        forbidden=client_for(requester).post(BASE+'jobs/',{'document_id':str(doc.pk),'topic_id':str(topic.pk),
             'count':1,'kind':'mcq','difficulty':'medium'},format='json')
        assert forbidden.status_code==409
        authorize_external(document_id=doc.pk,actor=rights,
            rationale='Verified documented rights, vendor-processing scope, privacy terms and data minimization.')
        response=client_for(requester).post(BASE+'jobs/',{'document_id':str(doc.pk),'topic_id':str(topic.pk),
             'count':1,'kind':'mcq','difficulty':'medium'},format='json')
        assert response.status_code==201,response.data
        jobid=response.data['id']
        quote=doc.extracted_text[:115]
        def fake_provider(**kwargs):
            return [dict(kind='mcq',prompt='After translating point (2,3) by vector (4,1), what point results?',
                         options=['(6,4)','(6,3)','(2,4)','(4,1)'],correct_index=0,
                         explanation='The translated coordinates are the original coordinates plus their offsets.',
                         evidence_quote=quote,rubric=[])]
        monkeypatch.setattr('apps.question_generation.services.generate_questions',fake_provider)
        assert process_job(jobid)=='complete'
        c=QuestionGenerationJob.objects.get(pk=jobid).candidates.first()
        assert c.validation_errors==[]
        approved=review_candidate(candidate_id=c.pk,actor=reviewer,action='approve',
            note='Translation computation, answers, and evidence checked manually.')
        assert approved.state==GeneratedQuestionCandidate.State.APPROVED
        assert approved.bank_revision is None


@pytest.mark.django_db
def test_withdrawal_blocks_queued_generation(verified):
    owner,outsider,rights,academic,requester,reviewer,doc,topic,root=verified
    with override_settings(NICAT_QUESTION_GENERATION_ENABLED=True,NICAT_QUESTION_AI_PROVIDER='mock',NICAT_DOCUMENT_PRIVATE_ROOT=root):
        job=queue_job(document_id=doc.pk,topic_id=topic.pk,actor=requester,count=1,kind='mcq',difficulty='easy')
        doc.state=DocumentSubmission.State.WITHDRAWN
        doc.save(update_fields=['state'])
        assert process_job(job.pk)=='blocked'
        assert GeneratedQuestionCandidate.objects.filter(job=job).count()==0
