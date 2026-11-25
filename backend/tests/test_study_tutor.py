"""Sprint 7: approvals, sources, ownership and exam-result release must fail closed."""
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission
from django.test import override_settings
from rest_framework.test import APIClient

from apps.attempts.models import GradeItem
from apps.resources.models import SourceDocument, SourceReference
from apps.study_tutor.models import SourceExcerpt, TutorExplanation
from apps.study_tutor.provider import TutorProviderError
from apps.study_tutor.services import (
    approve_excerpt, make_draft, publish_explanation, student_payload, validate_generated,
    withdraw_excerpt,
)
from .test_reviewer_workflow import reviewed_written_exam


FAKE_TUTOR = {
    "explanation": "FIFO means the first element added is the first one removed from a queue.",
    "common_mistake": "Confusing FIFO queues with LIFO stacks leads to incorrect ordering.",
    "practice_tip": "Draw an example queue and label the enqueue and dequeue operations.",
}


@pytest.fixture
def tutor_setup(reviewed_written_exam):
    student_client, reviewer, corrector, outsider, attempt_id, item = reviewed_written_exam
    reviewer.user_permissions.add(Permission.objects.get(codename="approve_tutor_content"))
    topic = item.attempt_question.revision.question.topic
    document = SourceDocument.objects.create(
        title="Authorized DSA Notes", unit=topic.unit, source_kind=SourceDocument.Kind.LECTURE_NOTES,
        rights_status=SourceDocument.Rights.ALLOWED,
    )
    reference = SourceReference.objects.create(document=document, page_label="12", section_label="Queues")
    excerpt = SourceExcerpt.objects.create(
        reference=reference, topic=topic,
        text="FIFO queues process the earliest enqueued element first; dequeue removes the head of the queue.",
    )
    approve_excerpt(excerpt_id=excerpt.pk, actor=reviewer)
    url = f"/api/v1/study-tutor/attempts/{attempt_id}/questions/{item.attempt_question_id}/explanation/"
    return student_client, reviewer, outsider, attempt_id, item, document, excerpt, url


def _generate(reviewer, item, excerpt):
    return make_draft(revision_id=item.attempt_question.revision_id, actor=reviewer)


def _fake(excerpt):
    return {**FAKE_TUTOR, "citation_ids": [str(excerpt.pk)]}


def _finish_marking(reviewer, item):
    reviewer_client = APIClient()
    reviewer_client.force_authenticate(user=reviewer)
    return reviewer_client.post(
        f"/api/v1/review/grade-items/{item.pk}/mark/",
        {"marks_awarded": "4.00", "rationale": "Response accurately defines FIFO with relevant details",
         "student_feedback": "Strong explanation of queue behavior; add one practical example."},
        format="json",
    )


@pytest.mark.django_db
def test_tutor_requires_final_result_and_human_publication(tutor_setup):
    student, reviewer, outsider, attempt_id, item, doc, excerpt, url = tutor_setup
    with override_settings(NICAT_AI_TUTOR_ENABLED=True, NICAT_AI_TUTOR_MODEL="mock-tutor"):
        assert student.get(url).status_code == 409  # essay still awaiting human mark
        reviewer_api = APIClient()
        reviewer_api.force_authenticate(user=reviewer)
        draft_url = f"/api/v1/study-tutor/revisions/{item.attempt_question.revision_id}/draft/"
        with override_settings(NICAT_AI_TUTOR_GENERATION_ENABLED=True):
            with patch("apps.study_tutor.services.generate_explanation", return_value=_fake(excerpt)) as llm:
                created = reviewer_api.post(draft_url)
                assert created.status_code == 201, created.data
                assert created.data["review_required"] is True
                assert reviewer_api.post(draft_url).status_code == 200  # no extra provider call
                assert llm.call_count == 1
        assert student.post(draft_url).status_code == 403
        assert _finish_marking(reviewer, item).status_code == 200
        assert student.get(url).status_code == 404  # unpublished tutor draft is never visible
        draft = TutorExplanation.objects.get(revision=item.attempt_question.revision)
        publish_explanation(explanation_id=draft.pk, actor=reviewer)
        public = student.get(url)
        assert public.status_code == 200, public.data
        assert public.data["reviewer_approved"] is True
        assert public.data["ai_assisted"] is True
        assert public.data["official_university_material"] is False
        assert public.data["sources"][0]["title"] == "Authorized DSA Notes"
        assert public.data["sources"][0]["page"] == "12"
        for hidden in ("marking_criteria", "correct_option_id", "model_name", "answer_sha256", "student_feedback"):
            assert hidden not in str(public.data)
        assert GradeItem.objects.get(pk=item.pk).marks_awarded == 4


@pytest.mark.django_db
def test_owner_and_release_settings_block_access(tutor_setup):
    student, reviewer, outsider, attempt_id, item, doc, excerpt, url = tutor_setup
    with override_settings(NICAT_AI_TUTOR_ENABLED=True):
        assert APIClient().get(url).status_code == 401
        other = APIClient(); other.force_authenticate(user=reviewer)
        assert other.get(url).status_code == 404
        assert student.get(f"/api/v1/study-tutor/attempts/{attempt_id}/questions/{unknown_question_id()}/explanation/").status_code == 404
        assert _finish_marking(reviewer, item).status_code == 200
        with override_settings(NICAT_AI_TUTOR_ENABLED=False):
            assert student.get(url).status_code == 404
        attempt = item.grade.attempt
        type(attempt.exam_version).objects.filter(pk=attempt.exam_version_id).update(show_explanations_after_submit=False)
        assert student.get(url).status_code == 409


def unknown_question_id():
    # Distinct, syntactically valid but unknown question UUID.
    return "00000000-0000-4000-8000-000000000001"


@pytest.mark.django_db
def test_revoked_source_rights_hide_published_explanation(tutor_setup):
    student, reviewer, outsider, attempt_id, item, doc, excerpt, url = tutor_setup
    with override_settings(NICAT_AI_TUTOR_ENABLED=True, NICAT_AI_TUTOR_MODEL="mock-tutor"):
        with patch("apps.study_tutor.services.generate_explanation", return_value=_fake(excerpt)):
            draft, created = _generate(reviewer, item, excerpt)
        publish_explanation(explanation_id=draft.pk, actor=reviewer)
        assert _finish_marking(reviewer, item).status_code == 200
        assert student.get(url).status_code == 200
        doc.rights_status = SourceDocument.Rights.RESTRICTED
        doc.save(update_fields=["rights_status"])
        assert student.get(url).status_code == 404
        doc.rights_status = SourceDocument.Rights.ALLOWED
        doc.save(update_fields=["rights_status"])
        withdraw_excerpt(excerpt_id=excerpt.pk, actor=reviewer)
        assert student.get(url).status_code == 404


@pytest.mark.django_db
def test_unknown_or_fake_citations_fail_validation(tutor_setup):
    student, reviewer, outsider, attempt_id, item, doc, excerpt, url = tutor_setup
    with pytest.raises(TutorProviderError):
        validate_generated({**FAKE_TUTOR, "citation_ids": ["00000000-0000-0000-0000-000000000000"]}, [excerpt])
    with override_settings(NICAT_AI_TUTOR_MODEL="mock-tutor"):
        with patch("apps.study_tutor.services.generate_explanation", return_value={
            **FAKE_TUTOR, "citation_ids": [str(excerpt.pk), str(excerpt.pk)]
        }):
            with pytest.raises(TutorProviderError):
                _generate(reviewer, item, excerpt)
    assert not TutorExplanation.objects.exists()


@pytest.mark.django_db
def test_rights_unknown_cannot_be_approved(tutor_setup):
    student, reviewer, outsider, attempt_id, item, doc, excerpt, url = tutor_setup
    doc.rights_status = SourceDocument.Rights.UNKNOWN
    doc.save(update_fields=["rights_status"])
    from apps.study_tutor.services import TutorConflict
    from apps.resources.models import SourceReference
    reference = SourceReference.objects.create(document=doc, page_label="13")
    draft = SourceExcerpt.objects.create(reference=reference, topic=excerpt.topic, text=excerpt.text)
    with pytest.raises(TutorConflict):
        approve_excerpt(excerpt_id=draft.pk, actor=reviewer)
    assert draft.state == SourceExcerpt.State.DRAFT


@pytest.mark.django_db
def test_only_explicit_content_reviewer_can_generate_drafts(tutor_setup):
    student, reviewer, outsider, attempt_id, item, doc, excerpt, url = tutor_setup
    student_api = APIClient(); student_api.force_authenticate(user=outsider)
    draft_url = f"/api/v1/study-tutor/revisions/{item.attempt_question.revision_id}/draft/"
    with override_settings(NICAT_AI_TUTOR_GENERATION_ENABLED=True):
        assert student_api.post(draft_url).status_code == 403
        unauthorized_staff = APIClient()
        from apps.accounts.models import User
        staff = User.objects.create_user("another-staff@example.test", "StrongExamplePassword!33", is_staff=True)
        unauthorized_staff.force_authenticate(user=staff)
        assert unauthorized_staff.post(draft_url).status_code == 403
    assert not TutorExplanation.objects.exists()


@pytest.mark.django_db
def test_stale_source_set_cannot_be_published(tutor_setup):
    student, reviewer, outsider, attempt_id, item, doc, excerpt, url = tutor_setup
    with override_settings(NICAT_AI_TUTOR_MODEL="mock-tutor"):
        with patch("apps.study_tutor.services.generate_explanation", return_value=_fake(excerpt)):
            draft, created = _generate(reviewer, item, excerpt)
    doc.rights_status = SourceDocument.Rights.RESTRICTED
    doc.save(update_fields=["rights_status"])
    from apps.study_tutor.services import TutorConflict
    with pytest.raises(TutorConflict):
        publish_explanation(explanation_id=draft.pk, actor=reviewer)
    assert TutorExplanation.objects.get(pk=draft.pk).state == TutorExplanation.State.DRAFT
