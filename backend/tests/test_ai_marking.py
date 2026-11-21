"""AI marking is reviewer-only, non-final, validated, and never student-visible."""
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.ai_tutor.models import AIMarkingSuggestion
from apps.ai_tutor.provider import AIProviderError
from apps.ai_tutor.services import validate_proposal
from apps.attempts.models import GradeItem
from .test_reviewer_workflow import reviewed_written_exam


FAKE_AI = {
    "criterion_scores": [{
        "criterion_number": 1,
        "awarded": "4.00",
        "reason": "Identifies first-in, first-out correctly but lacks an example.",
    }],
    "feedback": "Good explanation of FIFO. Add a real-world example to strengthen it.",
}


@pytest.mark.django_db
def test_ai_endpoint_denies_students_and_disabled_feature(reviewed_written_exam):
    student_client, reviewer, _, _, _, item = reviewed_written_exam
    url = f"/api/v1/review/grade-items/{item.pk}/ai-suggestion/"
    with override_settings(NICAT_AI_MARKING_ENABLED=True):
        assert APIClient().post(url).status_code == 401
        assert student_client.post(url).status_code == 403
        assert student_client.get(url).status_code == 403
    reviewing = APIClient()
    reviewing.force_authenticate(user=reviewer)
    with override_settings(NICAT_AI_MARKING_ENABLED=False):
        assert reviewing.post(url).status_code == 404
    assert not AIMarkingSuggestion.objects.exists()


@pytest.mark.django_db
def test_ai_suggestion_is_never_a_final_grade_and_reviewer_can_override(reviewed_written_exam):
    student_client, reviewer, _, _, attempt_id, item = reviewed_written_exam
    url = f"/api/v1/review/grade-items/{item.pk}/ai-suggestion/"
    reviewing = APIClient()
    reviewing.force_authenticate(user=reviewer)
    with override_settings(NICAT_AI_MARKING_ENABLED=True, NICAT_AI_MODEL="mocked-evaluator"):
        with patch("apps.ai_tutor.services.generate_marking", return_value=FAKE_AI) as model:
            proposal = reviewing.post(url)
            assert proposal.status_code == 201, proposal.data
            assert proposal.data["human_review_required"] is True
            assert proposal.data["proposed_marks"] == "4.00"
            assert reviewing.post(url).status_code == 200  # cached, no second API charge
            assert reviewing.get(url).status_code == 200
            assert model.call_count == 1
        assert student_client.get(url).status_code == 403
        assert GradeItem.objects.get(pk=item.pk).marks_awarded is None
        assert student_client.get(f"/api/v1/attempts/{attempt_id}/result/").data["status"] == "grading_pending"
        reviewed = reviewing.post(
            f"/api/v1/review/grade-items/{item.pk}/mark/",
            {
                "marks_awarded": "3.50",
                "rationale": "The response lacks a concrete FIFO example",
                "student_feedback": (
                    "You correctly explained LIFO and FIFO. "
                    "However, your answer needs a clearer example "
                    "showing how a queue operates."
                ),
            },
            format="json",
        )
        assert reviewed.status_code == 200, reviewed.data
        suggestion = AIMarkingSuggestion.objects.get(grade_item=item)
        assert suggestion.review_status == AIMarkingSuggestion.ReviewStatus.OVERRIDDEN
        assert suggestion.reviewed_by == reviewer
        result = student_client.get(f"/api/v1/attempts/{attempt_id}/result/")
        assert result.status_code == 200
        assert result.data["final_percentage"] == "70.00"
        assert "ai_suggestion" not in str(result.data)
        assert "reviewer_rubric" not in str(result.data)


@pytest.mark.django_db
def test_invalid_ai_score_is_rejected_without_creating_a_grade(reviewed_written_exam):
    _, reviewer, _, _, _, item = reviewed_written_exam
    reviewing = APIClient()
    reviewing.force_authenticate(user=reviewer)
    url = f"/api/v1/review/grade-items/{item.pk}/ai-suggestion/"
    invalid = {
        "criterion_scores": [{
            "criterion_number": 1,
            "awarded": "500.00",
            "reason": "This would exceed the rubric maximum.",
        }],
        "feedback": "This is an invalid out-of-range proposal.",
    }
    with override_settings(NICAT_AI_MARKING_ENABLED=True, NICAT_AI_MODEL="mocked-evaluator"):
        with patch("apps.ai_tutor.services.generate_marking", return_value=invalid):
            response = reviewing.post(url)
    assert response.status_code == 503
    assert not AIMarkingSuggestion.objects.filter(grade_item=item).exists()
    assert GradeItem.objects.get(pk=item.pk).marks_awarded is None


@pytest.mark.parametrize("score", ["-1", "NaN", "Infinity", "5.01", "3.123", "abc"])
def test_rubric_validator_rejects_bad_scores(score):
    with pytest.raises(AIProviderError):
        validate_proposal(
            {"criterion_scores": [{"criterion_number": 1, "awarded": score, "reason": "Rubric evidence"}],
             "feedback": "This is a sample feedback message."},
            [{"criterion": "Explain FIFO", "max_marks": "5.00"}],
            Decimal("5.00"),
        )
