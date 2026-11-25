"""Sprint 13 negative tests. Run with local NiCat Django/pytest setup."""
import io
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.academics.models import Programme, University, Unit, CurriculumVersion, CurriculumUnit
from apps.document_intake.models import DocumentSubmission
from apps.document_intake.services import IntakeConflict, review_document, process_one

URL = "/api/v1/document-intake/"


@pytest.fixture
def intake(db, tmp_path):
    User=get_user_model()
    owner=User.objects.create_user(email='intake-owner@example.test',password='TestingPassword!123')
    outsider=User.objects.create_user(email='intake-other@example.test',password='TestingPassword!123')
    rights=User.objects.create_user(email='intake-rights@example.test',password='TestingPassword!123',is_staff=True)
    academic=User.objects.create_user(email='intake-academic@example.test',password='TestingPassword!123',is_staff=True)
    rights.user_permissions.add(Permission.objects.get(codename='review_document_rights'))
    academic.user_permissions.add(Permission.objects.get(codename='review_document_academic'))
    university=University.objects.create(name='Example NiCat Test University',abbreviation='TEST')
    programme=Programme.objects.create(university=university,name='Test BBIT')
    version=CurriculumVersion.objects.create(programme=programme,label='Test')
    unit=Unit.objects.create(title='Test Computer Graphics',slug='test-computer-graphics')
    CurriculumUnit.objects.create(curriculum_version=version,unit=unit,year_number=3,semester_number=1)
    data={'programme_id':str(programme.pk),'unit_id':str(unit.pk),'title':'Computer Graphics original notes',
          'document_type':'original_notes','rights_basis':'own_work','author_or_owner':'Test student',
          'permit_question_generation':'true','permit_resource_display':'false','permit_tutor_use':'false'}
    return owner,outsider,rights,academic,programme,unit,data,tmp_path


def as_user(user):
    client=APIClient();client.force_authenticate(user=user);return client


@pytest.mark.django_db
def test_feature_flag_and_owner_visibility(intake):
    owner,outsider,rights,academic,programme,unit,data,root=intake
    with override_settings(NICAT_DOCUMENT_INTAKE_ENABLED=False,NICAT_DOCUMENT_PRIVATE_ROOT=root):
        assert as_user(owner).get(URL).status_code==404
    with override_settings(NICAT_DOCUMENT_INTAKE_ENABLED=True,NICAT_DOCUMENT_PRIVATE_ROOT=root):
        upload=SimpleUploadedFile('graphics.txt',('Computer Graphics lesson. '*8).encode(),content_type='text/plain')
        result=as_user(owner).post(URL,{**data,'file':upload},format='multipart')
        assert result.status_code==201,result.data
        pk=result.data['id']
        assert result.data['state']=='pending_scan'
        assert 'stored_key' not in result.data
        assert 'extracted_text' not in result.data
        assert as_user(outsider).get(URL).data['items']==[]
        assert as_user(outsider).post(f'{URL}{pk}/withdraw/').status_code==404
        assert as_user(owner).post(f'{URL}{pk}/withdraw/').status_code==200


@pytest.mark.django_db
def test_reject_spoofed_pdf_and_without_generation_permission(intake):
    owner,outsider,rights,academic,programme,unit,data,root=intake
    with override_settings(NICAT_DOCUMENT_INTAKE_ENABLED=True,NICAT_DOCUMENT_PRIVATE_ROOT=root):
        fake=SimpleUploadedFile('graphics.pdf',b'not a pdf and contains no PDF signature')
        response=as_user(owner).post(URL,{**data,'file':fake},format='multipart')
        assert response.status_code==400
        denied=SimpleUploadedFile('graphics.txt',b'Original text here.'*15)
        response=as_user(owner).post(URL,{**data,'permit_question_generation':'false','file':denied},format='multipart')
        assert response.status_code==400
        assert DocumentSubmission.objects.count()==0


@pytest.mark.django_db
def test_scan_fail_closed_and_review_requires_two_people(intake,monkeypatch):
    owner,outsider,rights,academic,programme,unit,data,root=intake
    with override_settings(NICAT_DOCUMENT_INTAKE_ENABLED=True,NICAT_DOCUMENT_PRIVATE_ROOT=root):
        file=SimpleUploadedFile('graphics.txt',('A correctly structured graphics concept. '*8).encode())
        response=as_user(owner).post(URL,{**data,'file':file},format='multipart')
        assert response.status_code==201,response.data
        pk=response.data['id']
        reason='Verified that the student authored the notes and granted question-drafting rights.'
        with pytest.raises(IntakeConflict):
            review_document(document_id=pk,actor=rights,action='rights_clear',rationale=reason)
        monkeypatch.setattr('apps.document_intake.services.scan_with_clamav',lambda p:'error')
        assert process_one(pk)=='scanner_error'
        doc=DocumentSubmission.objects.get(pk=pk)
        assert doc.scan_state==doc.ScanState.ERROR
        assert doc.state==doc.State.PROCESSING_ERROR
        monkeypatch.setattr('apps.document_intake.services.scan_with_clamav',lambda p:'clean')
        assert process_one(pk)=='ready'
        review_document(document_id=pk,actor=rights,action='rights_clear',rationale=reason)
        with pytest.raises(IntakeConflict,match='independent'):
            # The rights reviewer receives academic permission to verify the separate-person guard.
            rights.user_permissions.add(Permission.objects.get(codename='review_document_academic'))
            rights = get_user_model().objects.get(pk=rights.pk)
            review_document(document_id=pk,actor=rights,action='academic_approve',rationale=reason)
        approved=review_document(document_id=pk,actor=academic,action='academic_approve',rationale=reason)
        assert approved.state==DocumentSubmission.State.APPROVED
        from apps.questions.models import QuestionRevision
        # Approval does not insert new questions or publish any document file.
        assert approved.events.filter(action='academic_approve').count()==1
        assert not hasattr(approved,'published_url')


# Missing-unit catalogue resolution and authorization tests.
def set_permissions(user, *permissions):
    for app_label, codename in permissions:
        user.user_permissions.add(Permission.objects.get(content_type__app_label=app_label, codename=codename))
    return get_user_model().objects.get(pk=user.pk)


def upload_unmapped(owner, programme, original_data):
    fields = {k: v for k, v in original_data.items() if k != 'unit_id'}
    fields.update({'suggested_unit_title': 'Computer Vision', 'suggested_unit_code': 'CG-410',
                   'year_number': '4', 'semester_number': '1'})
    file = SimpleUploadedFile('vision.txt', ('Computer Vision introduction and key concepts. ' * 8).encode('utf-8'))
    return as_user(owner).post(URL, {**fields, 'file': file}, format='multipart')



@pytest.mark.django_db
def test_missing_unit_authorization_and_creation(intake):
    owner, outsider, rights, academic, programme, unit, data, root = intake
    editor = get_user_model().objects.create_user(email='catalogue-editor@example.test',
                password='Password-12345', is_staff=True)
    version = CurriculumVersion.objects.get(programme=programme)
    with override_settings(NICAT_DOCUMENT_INTAKE_ENABLED=True, NICAT_DOCUMENT_PRIVATE_ROOT=root):
        uploaded = upload_unmapped(owner, programme, data)
        assert uploaded.status_code == 201, uploaded.data
        document_id = uploaded.data['id']
        url = f'{URL}staff/{document_id}/create-unit/'
        request = {'curriculum_version_id': str(version.pk), 'title': 'Computer Vision',
                   'year_number': 4, 'semester_number': 1, 'catalogue_verified': True,
                   'rationale': 'Checked the programme syllabus and curriculum placement.'}
        assert as_user(owner).post(url, request, format='json').status_code == 403
        assert as_user(editor).post(url, request, format='json').status_code == 403
        editor = set_permissions(editor, ('document_intake', 'map_document_units'))
        assert as_user(editor).post(url, request, format='json').status_code == 403
        editor = set_permissions(editor, ('academics', 'add_curriculumunit'), ('academics', 'add_unit'))
        rejected = as_user(editor).post(url, {**request, 'catalogue_verified': False}, format='json')
        assert rejected.status_code == 409
        answer = as_user(editor).post(url, request, format='json')
        assert answer.status_code == 200, answer.data
        assert answer.data['unit_created'] is True
        submission = DocumentSubmission.objects.get(pk=document_id)
        assert submission.unit.title == 'Computer Vision'
        assert submission.state == DocumentSubmission.State.PENDING_SCAN
        assert CurriculumUnit.objects.filter(curriculum_version=version, unit=submission.unit,
            year_number=4, semester_number=1).exists()
        assert submission.events.filter(action='unit_created_and_mapped').count() == 1
        assert as_user(editor).post(url, request, format='json').status_code == 409
        listing = as_user(owner).get(f'{URL}programmes/{programme.pk}/units/')
        assert listing.status_code == 200
        assert any(row['id'] == str(submission.unit_id) for row in listing.data['items'])
        assert any(row['id'] == str(version.pk) for row in listing.data['curriculum_versions'])


@pytest.mark.django_db
def test_missing_unit_rejects_wrong_programme_curriculum(intake):
    owner, outsider, rights, academic, programme, unit, data, root = intake
    editor = get_user_model().objects.create_user(email='catalogue-editor-2@example.test',
                password='Password-12345', is_staff=True)
    editor = set_permissions(editor, ('document_intake','map_document_units'),
                             ('academics','add_curriculumunit'), ('academics','add_unit'))
    second = Programme.objects.create(university=programme.university, name='Another Programme')
    foreign_version = CurriculumVersion.objects.create(programme=second, label='Another')
    with override_settings(NICAT_DOCUMENT_INTAKE_ENABLED=True, NICAT_DOCUMENT_PRIVATE_ROOT=root):
        uploaded = upload_unmapped(owner, programme, data)
        assert uploaded.status_code == 201, uploaded.data
        doc_id = uploaded.data['id']
        before = Unit.objects.count()
        answer = as_user(editor).post(f'{URL}staff/{doc_id}/create-unit/', {
            'curriculum_version_id': str(foreign_version.pk), 'title': 'Computer Vision',
            'year_number': 4, 'semester_number': 1, 'catalogue_verified': True,
            'rationale': 'Checked the unit in a different programme incorrectly.',
        }, format='json')
        assert answer.status_code == 409
        assert Unit.objects.count() == before
        assert DocumentSubmission.objects.get(pk=doc_id).unit_id is None
