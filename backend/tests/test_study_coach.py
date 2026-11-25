"""Sprint 8 protections: released-only, reviewer-only publication, quotas, rights."""
from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.resources.models import SourceDocument
from apps.study_coach.models import TutorDailyBudget, TutorFollowUp
from apps.study_coach.services import CoachConflict, publish_followup
from apps.study_tutor.services import make_draft, publish_explanation
from .test_reviewer_workflow import reviewed_written_exam
from .test_study_tutor import tutor_setup, _fake, _finish_marking


@pytest.fixture
def coach_setup(tutor_setup):
    student, reviewer, outsider, attempt_id, grade_item, document, excerpt, _ = tutor_setup
    with override_settings(NICAT_AI_TUTOR_MODEL="test-mock"):
        with patch("apps.study_tutor.services.generate_explanation", return_value=_fake(excerpt)):
            draft, _ = make_draft(revision_id=grade_item.attempt_question.revision_id, actor=reviewer)
    publish_explanation(explanation_id=draft.pk, actor=reviewer)
    endpoint = (
        f"/api/v1/study-coach/attempts/{attempt_id}/"
        f"questions/{grade_item.attempt_question_id}/followups/"
    )
    return student, reviewer, outsider, grade_item, document, excerpt, endpoint


MOCK = {
    "NICAT_AI_PROVIDER": "mock",
    "NICAT_AI_TUTOR_ENABLED": True,
    "NICAT_AI_FOLLOWUPS_ENABLED": True,
    "NICAT_AI_RECOMMENDATIONS_ENABLED": True,
    "NICAT_COACH_STUDENT_DAILY_LIMIT": 2,
    "NICAT_COACH_GLOBAL_DAILY_LIMIT": 5,
}


@pytest.mark.django_db
def test_followup_hidden_until_result_is_final_and_released(coach_setup):
    student, reviewer, outsider, grade_item, doc, excerpt, url = coach_setup
    with override_settings(**MOCK):
        assert student.post(url, {"question": "What is the difference between a queue and a stack?"}).status_code == 409
        assert _finish_marking(reviewer, grade_item).status_code == 200
        response = student.post(url, {"question": "What is the difference between a queue and a stack?"})
        assert response.status_code == 201, response.data
        assert response.data["review_required"] is True
        record = TutorFollowUp.objects.get(pk=response.data["id"])
        assert record.state == TutorFollowUp.State.DRAFT
        assert "MOCK TEST DATA" in record.draft_answer
        public = student.get(url)
        assert public.status_code == 200, public.data
        assert public.data["items"][0]["answer"] is None
        assert "MOCK TEST DATA" not in str(public.data)


@pytest.mark.django_db
def test_only_human_review_can_publish_and_revocation_hides_answer(coach_setup):
    student, reviewer, outsider, grade_item, document, excerpt, url = coach_setup
    with override_settings(**MOCK):
        assert _finish_marking(reviewer, grade_item).status_code == 200
        created = student.post(url, {"question": "Why does a queue use FIFO ordering?"})
        assert created.status_code == 201, created.data
        followup = TutorFollowUp.objects.get(pk=created.data["id"])
        with pytest.raises(CoachConflict, match="Replace the mock"):
            publish_followup(followup_id=followup.pk, actor=reviewer)
        followup.draft_answer = (
            "In a FIFO queue, the oldest item is the first item removed, "
            "as the approved notes describe. New items join the rear and dequeue removes the head."
        )
        followup.save(update_fields=["draft_answer"])
        publish_followup(followup_id=followup.pk, actor=reviewer)
        published = student.get(url)
        assert published.status_code == 200, published.data
        assert published.data["items"][0]["answer"].startswith("In a FIFO queue")
        assert published.data["items"][0]["sources"][0]["title"] == "Authorized DSA Notes"
        document.rights_status = SourceDocument.Rights.RESTRICTED
        document.save(update_fields=["rights_status"])
        hidden = student.get(url)
        assert hidden.data["items"][0]["answer"] is None
        assert hidden.data["items"][0]["status"] == "unavailable"



@pytest.mark.django_db
def test_owner_checks_and_strict_student_quota(coach_setup):
    student_api, reviewer, student, grade_item, document, excerpt, url = coach_setup

    from django.contrib.auth import get_user_model
    from apps.attempts.models import Attempt

    User = get_user_model()

    outsider = User.objects.create_user(
        email="outsider@example.test",
        password="TestPassword123!",
    )

    attempt_id = url.split("/attempts/")[1].split("/")[0]
    attempt = Attempt.objects.get(pk=attempt_id)

    assert attempt.student_id == student.pk
    assert attempt.student_id != outsider.pk

    with override_settings(**MOCK):
        assert _finish_marking(reviewer, grade_item).status_code == 200

        outsider_api = APIClient()
        outsider_api.force_authenticate(user=outsider)

        assert outsider_api.get(url).status_code == 404

        assert outsider_api.post(url, {"question": "May I see somebody else's answer?"}).status_code == 404
        for idx in range(2):
            assert student.post(url, {"question": f"Can you clarify the queue operation number {idx}?"}).status_code == 201
        limited = student.post(url, {"question": "Can you clarify this once again for me?"})
        assert limited.status_code == 429, limited.data
        assert TutorFollowUp.objects.count() == 2
        assert TutorDailyBudget.objects.get().requests == 2


@pytest.mark.django_db
def test_recommendations_use_final_student_grades(coach_setup):
    student, reviewer, outsider, grade_item, document, excerpt, url = coach_setup
    with override_settings(**MOCK):
        response = student.get("/api/v1/study-coach/recommendations/")
        assert response.status_code == 200
        assert response.data["recommendations"] == []
        assert _finish_marking(reviewer, grade_item).status_code == 200
        response = student.get("/api/v1/study-coach/recommendations/")
        assert response.status_code == 200, response.data
        assert response.data["attempts_considered"] >= 1
        assert len(response.data["recommendations"]) >= 1
        assert "student_answer" not in str(response.data)
