"""Pilot seed and grading contracts. Runs against PostgreSQL with the rest of the suite."""
from decimal import Decimal
import pytest
from django.core.management import call_command
from apps.accounts.models import User
from apps.academics.models import Unit
from apps.exams.models import ExamVersion
from apps.questions.models import QuestionRevision
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_dsa_pilot_requires_review_before_publication():
    call_command("seed_dsa_pilot")
    exam = ExamVersion.objects.get(template__unit__slug="mmu-bbit-dsa")
    assert exam.is_published is False
    assert exam.items.count() == 12
    assert sum((i.revision.max_marks for i in exam.items.all()), Decimal("0")) == Decimal("20.00")
    assert QuestionRevision.objects.filter(question__topic__unit__slug="mmu-bbit-dsa", status="published").count() == 0
    # Idempotent import; must not duplicate the draft.
    call_command("seed_dsa_pilot")
    assert exam.items.count() == 12


@pytest.mark.django_db
def test_dsa_pilot_published_after_staff_signoff_and_result():
    reviewer = User.objects.create_superuser("pilot-reviewer@example.test", "ExamplePass!9912")
    student = User.objects.create_user("pilot-student@example.test", "ExamplePass!9912")
    call_command("seed_dsa_pilot")
    call_command("seed_dsa_pilot", publish=True, reviewer_email=reviewer.email)
    exam = ExamVersion.objects.get(template__unit__slug="mmu-bbit-dsa")
    assert exam.is_published
    call_command("seed_dsa_pilot", publish=True, reviewer_email=reviewer.email)
    token = APIClient().post("/api/v1/auth/login/",
        {"email": student.email, "password": "ExamplePass!9912"}, format="json")
    assert token.status_code == 200
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.data['access']}")
    listing = client.get("/api/v1/exams/")
    assert listing.status_code == 200
    assert any(str(e["id"]) == str(exam.pk) for e in listing.data["results"])
    started = client.post(f"/api/v1/exams/{exam.pk}/attempts/", format="json")
    assert started.status_code == 201, started.data
    aid = started.data["id"]
    questions = started.data["questions"]
    assert len(questions) == 12
    assert "correct_option_id" not in str(started.data)
    assert "rubric" not in str(started.data)
    for q in questions:
        if q["kind"] == "single_choice":
            assert client.put(f"/api/v1/attempts/{aid}/responses/{q['id']}/",
                {"selected_option_id": q["options"][0]["id"]}, format="json").status_code == 200
        else:
            assert client.put(f"/api/v1/attempts/{aid}/responses/{q['id']}/",
                {"text_answer": "This written answer needs rubric-based marking."}, format="json").status_code == 200
    assert client.post(f"/api/v1/attempts/{aid}/submit/").status_code == 200
    result = client.get(f"/api/v1/attempts/{aid}/result/")
    assert result.status_code == 200
    assert result.data["status"] == "grading_pending"
    assert result.data["final_percentage"] is None
    assert result.data["ungraded_possible_marks"] == "10.00"
