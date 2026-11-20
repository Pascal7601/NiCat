"""Integration contract checks. Exercise against PostgreSQL in CI."""
from datetime import timedelta
from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.academics.models import University, Programme, CurriculumVersion, Unit, CurriculumUnit, Topic
from apps.questions.models import Question, QuestionRevision, ChoiceOption
from apps.exams.models import ExamTemplate, ExamVersion, ExamQuestion
from apps.attempts.models import Grade

@pytest.fixture
def users(db):
    return User.objects.create_user("student1@example.test", "StrongExamplePassword!1"), User.objects.create_user("student2@example.test", "StrongExamplePassword!2"), User.objects.create_superuser("reviewer@example.test", "StrongExamplePassword!3")

@pytest.fixture
def sample_exam(users, db):
    uni = University.objects.create(name="Pilot University (test fixture)")
    prog = Programme.objects.create(university=uni, name="BBIT")
    curriculum = CurriculumVersion.objects.create(programme=prog, label="archival-test")
    unit = Unit.objects.create(title="Data Structures and Algorithms", slug="dsa-test")
    CurriculumUnit.objects.create(curriculum_version=curriculum, unit=unit, year_number=2, semester_number=1)
    topic = Topic.objects.create(unit=unit, title="Stacks")
    q = Question.objects.create(topic=topic)
    rev = QuestionRevision.objects.create(question=q, number=1, kind="single_choice", provenance="original_practice", prompt="Which stack operation removes an item?", max_marks=Decimal("2"))
    wrong = ChoiceOption.objects.create(revision=rev, position=1, text="Push", is_correct=False)
    correct = ChoiceOption.objects.create(revision=rev, position=2, text="Pop", is_correct=True)
    rev.reviewed_by = users[2]
    rev.status = "published"
    rev.save()
    t = ExamTemplate.objects.create(unit=unit, title="Stacks pilot")
    v = ExamVersion.objects.create(template=t, number=1, duration_seconds=900)
    ExamQuestion.objects.create(version=v, revision=rev, position=1)
    v.is_published = True
    v.save()
    return v, correct, wrong, curriculum

@pytest.mark.django_db
def test_student_attempt_owner_isolation_and_safe_keys(users, sample_exam):
    exam, correct, _, _ = sample_exam
    client = APIClient()
    client.force_authenticate(user=users[0])
    response = client.post(f"/api/v1/exams/{exam.pk}/attempts/", format="json")
    assert response.status_code == 201, response.data
    attempt_id = response.data["id"]
    question = response.data["questions"][0]
    assert "correct_option_id" not in str(response.data)
    assert "is_correct" not in str(response.data)
    other = APIClient()
    other.force_authenticate(user=users[1])
    assert other.get(f"/api/v1/attempts/{attempt_id}/").status_code == 404
    assert other.get(f"/api/v1/attempts/{attempt_id}/result/").status_code == 404
    assert other.post(f"/api/v1/attempts/{attempt_id}/submit/").status_code == 404
    save = client.put(f"/api/v1/attempts/{attempt_id}/responses/{question['id']}/",
        {"selected_option_id": str(correct.id)}, format="json")
    assert save.status_code == 200, save.data
    first = client.post(f"/api/v1/attempts/{attempt_id}/submit/")
    second = client.post(f"/api/v1/attempts/{attempt_id}/submit/")
    assert first.status_code == 200 and second.status_code == 200
    result = client.get(f"/api/v1/attempts/{attempt_id}/result/")
    assert result.data["final_percentage"] == "100.00"
    assert Grade.objects.count() == 1
    assert client.put(f"/api/v1/attempts/{attempt_id}/responses/{question['id']}/",
        {"selected_option_id": str(correct.id)}, format="json").status_code == 409

@pytest.mark.django_db
def test_unauthenticated_api_is_rejected_and_archive_does_not_imply_verification(sample_exam):
    exam,_,_,curriculum=sample_exam
    client=APIClient()
    assert client.get("/api/v1/me/").status_code in (401,403)
    assert client.post(f"/api/v1/exams/{exam.pk}/attempts/").status_code in (401,403)
    assert curriculum.is_officially_verified is False

@pytest.mark.django_db
def test_published_question_immutable_and_one_correct_option(users, sample_exam):
    exam,correct,_,_=sample_exam
    rev=exam.items.first().revision
    rev.prompt="changed after publication"
    with pytest.raises(ValidationError):
        rev.save()
    correct.text="tampering"
    with pytest.raises(ValidationError):
        correct.save()


@pytest.mark.django_db
def test_deadline_blocks_writes_but_allows_saved_work_finalization(users, sample_exam):
    from apps.attempts.models import Attempt
    exam, correct, wrong, _ = sample_exam
    client=APIClient()
    client.force_authenticate(user=users[0])
    first=client.post(f"/api/v1/exams/{exam.pk}/attempts/", format="json")
    assert first.status_code == 201
    attempt_id=first.data["id"]
    qid=first.data["questions"][0]["id"]
    assert client.put(f"/api/v1/attempts/{attempt_id}/responses/{qid}/",
        {"selected_option_id": str(correct.id)}, format="json").status_code == 200
    Attempt.objects.filter(pk=attempt_id).update(deadline_at=timezone.now() - timedelta(seconds=1))
    late=client.put(f"/api/v1/attempts/{attempt_id}/responses/{qid}/",
        {"selected_option_id": str(wrong.id)}, format="json")
    assert late.status_code == 409
    assert client.post(f"/api/v1/attempts/{attempt_id}/submit/").status_code == 200
    assert client.get(f"/api/v1/attempts/{attempt_id}/result/").data["final_percentage"] == "100.00"

@pytest.mark.django_db
def test_pending_written_never_claims_final_percentage(users, sample_exam):
    from apps.questions.models import RubricCriterion
    exam, _, _, _ = sample_exam
    topic=exam.items.first().revision.question.topic
    q=Question.objects.create(topic=topic)
    rev=QuestionRevision.objects.create(question=q,number=1,kind="written",provenance="original_practice",
        prompt="Explain a stack",max_marks=Decimal("5"))
    RubricCriterion.objects.create(revision=rev,description="LIFO explanation",max_marks=Decimal("5"),position=1)
    rev.reviewed_by=users[2]
    rev.status="published"
    rev.save()
    version=ExamVersion.objects.create(template=exam.template,number=2,duration_seconds=900)
    ExamQuestion.objects.create(version=version,revision=rev,position=1)
    version.is_published=True
    version.save()
    client=APIClient()
    client.force_authenticate(user=users[0])
    started=client.post(f"/api/v1/exams/{version.pk}/attempts/",format="json")
    assert started.status_code==201
    aid=started.data["id"]
    qid=started.data["questions"][0]["id"]
    assert client.put(f"/api/v1/attempts/{aid}/responses/{qid}/",
        {"text_answer":"A LIFO collection"},format="json").status_code==200
    assert client.post(f"/api/v1/attempts/{aid}/submit/").status_code==200
    result=client.get(f"/api/v1/attempts/{aid}/result/")
    assert result.data["status"]=="grading_pending"
    assert result.data["final_percentage"] is None
    assert result.data["ungraded_possible_marks"]=="5.00"


@pytest.mark.django_db
def test_student_attempt_metadata_and_history(
    users,
    sample_exam,
):
    exam, _, _, _ = sample_exam

    student_client = APIClient()
    student_client.force_authenticate(
        user=users[0]
    )

    started = student_client.post(
        f"/api/v1/exams/{exam.id}/attempts/",
        format="json",
    )

    assert started.status_code == 201, started.data
    assert started.data["exam_title"] == "Stacks pilot"

    attempt_id = started.data["id"]

    detail = student_client.get(
        f"/api/v1/attempts/{attempt_id}/"
    )

    assert detail.status_code == 200
    assert detail.data["exam_title"] == "Stacks pilot"

    history = student_client.get(
        "/api/v1/me/attempts/"
    )

    assert history.status_code == 200

    item = history.data[0]

    assert item["id"] == attempt_id
    assert item["exam_title"] == "Stacks pilot"
    assert item["status"] == "in_progress"
    assert item["deadline_at"]
    assert item["submitted_at"] is None

    # A different student must not see this attempt.
    other_client = APIClient()
    other_client.force_authenticate(
        user=users[1]
    )

    other_history = other_client.get(
        "/api/v1/me/attempts/"
    )

    assert other_history.status_code == 200
    assert other_history.data == []

    assert other_client.get(
        f"/api/v1/attempts/{attempt_id}/"
    ).status_code == 404
