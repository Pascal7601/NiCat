"""PostgreSQL-backed integration tests for the auditable grading transitions."""
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from apps.academics.models import Topic, Unit
from apps.attempts.models import Attempt, Grade, GradeItem, GradingEvent
from apps.accounts.models import User
from apps.exams.models import ExamQuestion, ExamTemplate, ExamVersion
from apps.questions.models import Question, QuestionRevision, RubricCriterion


@pytest.fixture
def reviewed_written_exam(db):
    reviewer = User.objects.create_user("marker@example.test", "SafeTestPassword@119", is_staff=True)
    corrector = User.objects.create_user("corrector@example.test", "SafeTestPassword@120", is_staff=True)
    outsider = User.objects.create_user("student@example.test", "SafeTestPassword@121")
    from django.contrib.contenttypes.models import ContentType
    grade_item_ct = ContentType.objects.get_for_model(GradeItem)
    reviewer.user_permissions.add(Permission.objects.get(content_type=grade_item_ct, codename="review_written_answers"))
    corrector.user_permissions.add(Permission.objects.get(content_type=grade_item_ct, codename="correct_final_grades"))
    unit = Unit.objects.create(title="Algorithms", slug="alg-review-tests")
    topic = Topic.objects.create(unit=unit, title="Queues")
    question = Question.objects.create(topic=topic)
    revision = QuestionRevision.objects.create(question=question, number=1, kind="written",
        provenance="original_practice", prompt="Explain FIFO", max_marks=Decimal("5.00"))
    RubricCriterion.objects.create(revision=revision, position=1, description="Explain first in first out", max_marks=Decimal("5"))
    revision.reviewed_by = reviewer
    revision.status = QuestionRevision.Status.PUBLISHED
    revision.save()
    template = ExamTemplate.objects.create(unit=unit, title="Queues")
    exam = ExamVersion.objects.create(template=template, number=1, duration_seconds=900)
    ExamQuestion.objects.create(version=exam, revision=revision, position=1)
    exam.is_published = True
    exam.save()
    student_client = APIClient()
    student_client.force_authenticate(user=outsider)
    started = student_client.post(f"/api/v1/exams/{exam.pk}/attempts/", format="json")
    assert started.status_code == 201, started.data
    attempt_id = started.data["id"]
    qid = started.data["questions"][0]["id"]
    assert student_client.put(f"/api/v1/attempts/{attempt_id}/responses/{qid}/",
                              {"text_answer": "FIFO removes the oldest element first."}, format="json").status_code == 200
    assert student_client.post(f"/api/v1/attempts/{attempt_id}/submit/").status_code == 200
    item = GradeItem.objects.get(grade__attempt_id=attempt_id)
    return student_client, reviewer, corrector, outsider, attempt_id, item


@pytest.mark.django_db
def test_marking_requires_permission_and_is_auditable(reviewed_written_exam):
    student_client, reviewer, corrector, outsider, attempt_id, item = reviewed_written_exam
    forbidden = student_client.get("/api/v1/review/pending/")
    assert forbidden.status_code == 403
    forbidden_mark = student_client.post(f"/api/v1/review/grade-items/{item.pk}/mark/",
                                         {"marks_awarded": "5.00", "rationale": "Unapproved attempt",
                                          "student_feedback": (
            "You correctly explained which item exits first."
        ),}, format="json")
    assert forbidden_mark.status_code == 403
    reviewing = APIClient(); reviewing.force_authenticate(user=reviewer)
    queue = reviewing.get("/api/v1/review/pending/")
    assert queue.status_code == 200 and queue.data["count"] == 1
    assert queue.data["items"][0]["response"].startswith("FIFO")
    assert queue.data["items"][0]["reviewer_rubric"][0]["max_marks"] == "5.00"
    assert "correct_option_id" not in str(queue.data)
    too_many = reviewing.post(f"/api/v1/review/grade-items/{item.pk}/mark/",
                             {"marks_awarded": "5.01", 
                              "rationale": "Answer meets criteria",
                              "student_feedback": (
            "You correctly explained which item exits first."
        ),}, format="json")
    assert too_many.status_code == 400
    marked = reviewing.post(f"/api/v1/review/grade-items/{item.pk}/mark/",
                            {"marks_awarded": "4.00", 
                             "rationale": "Contains the main FIFO concept",
                             "student_feedback": (
            "You correctly explained which item exits first."
        ),}, format="json")
    assert marked.status_code == 200, marked.data
    assert marked.data["attempt_status"] == Attempt.State.GRADED_FINAL
    assert marked.data["final_percentage"] == "80.00"
    assert reviewing.post(f"/api/v1/review/grade-items/{item.pk}/mark/",
             {"marks_awarded": "5.00", 
              "rationale": "Cannot grade twice",
              "student_feedback": (
            "You correctly explained which item exits first."
        ),}, format="json").status_code == 409
    assert GradingEvent.objects.filter(grade__attempt_id=attempt_id, details__action="first_review").count() == 1
    assert student_client.get(f"/api/v1/attempts/{attempt_id}/result/").data["final_percentage"] == "80.00"


@pytest.mark.django_db
def test_correction_needs_separate_permission_and_reason(reviewed_written_exam):
    student_client, reviewer, corrector, outsider, attempt_id, item = reviewed_written_exam
    reviewing = APIClient(); reviewing.force_authenticate(user=reviewer)
    assert reviewing.post(f"/api/v1/review/grade-items/{item.pk}/mark/",
        {"marks_awarded": "3.50", "rationale": "Initial review complete", "student_feedback": (
            "You correctly explained which item exits first."
        ),}, 
        format="json").status_code == 200
    correction_by_reviewer = reviewing.post(f"/api/v1/review/grade-items/{item.pk}/correct/",
        {"marks_awarded": "4.50", 
         "reason": "Additional rubric point",
         "student_feedback": (
            "You correctly explained which item exits first."
        ),}, format="json")
    assert correction_by_reviewer.status_code == 403
    editor = APIClient(); editor.force_authenticate(user=corrector)
    short_reason = editor.post(f"/api/v1/review/grade-items/{item.pk}/correct/",
        {"marks_awarded": "4.50", "reason": "Fix"}, format="json")
    assert short_reason.status_code == 400
    fixed = editor.post(f"/api/v1/review/grade-items/{item.pk}/correct/",
        {"marks_awarded": "4.50", "reason": "Double-check of the relevant rubric criterion"}, format="json")
    assert fixed.status_code == 200, fixed.data
    assert fixed.data["final_percentage"] == "90.00"
    correction_event = GradingEvent.objects.get(grade__attempt_id=attempt_id, details__action="correction")
    assert correction_event.details["old_marks"] == "3.50"
    assert correction_event.details["new_marks"] == "4.50"
    assert correction_event.actor_id == corrector.pk
    assert Grade.objects.get(attempt_id=attempt_id).scored_marks == Decimal("4.50")



@pytest.mark.django_db
def test_student_feedback_is_released_only_after_finalization(
    reviewed_written_exam,
):
    (
        student_client,
        reviewer,
        _corrector,
        _student,
        attempt_id,
        item,
    ) = reviewed_written_exam

    before = student_client.get(
        f"/api/v1/attempts/{attempt_id}/result/"
    )

    assert before.status_code == 200
    assert before.data["status"] == "grading_pending"
    assert before.data["final_percentage"] is None

    assert (
        before.data["items"][0].get("student_feedback")
        is None
    )

    reviewing = APIClient()
    reviewing.force_authenticate(user=reviewer)

    marked = reviewing.post(
        f"/api/v1/review/grade-items/{item.id}/mark/",
        {
            "marks_awarded": "4.00",
            "rationale": (
                "Awarded four marks after applying "
                "the approved rubric."
            ),
            "student_feedback": (
                "Good explanation of the FIFO concept."
            ),
        },
        format="json",
    )

    assert marked.status_code == 200, marked.data

    after = student_client.get(
        f"/api/v1/attempts/{attempt_id}/result/"
    )

    assert after.status_code == 200
    assert after.data["status"] == "graded_final"
    assert after.data["final_percentage"] == "80.00"

    assert (
        after.data["items"][0]["student_feedback"]
        == "Good explanation of the FIFO concept."
    )

    # Internal audit rationale is never sent to students.
    assert "Awarded four marks" not in str(after.data)
