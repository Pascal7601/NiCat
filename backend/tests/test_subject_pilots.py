
"""Contract tests for the IAP and E-Commerce pilots."""

from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.exams.models import ExamVersion
from apps.questions.models import QuestionRevision


PILOTS = [
    ("iap", "mmu-bbit-iap"),
    ("ecommerce", "mmu-bbit-ecommerce"),
]


@pytest.mark.django_db
@pytest.mark.parametrize("unit,slug", PILOTS)
def test_import_creates_stable_unpublished_exam(unit, slug):
    call_command("seed_subject_pilots", "--unit", unit)

    exam = ExamVersion.objects.get(
        template__unit__slug=slug
    )

    assert exam.is_published is False
    assert exam.items.count() == 12

    total = sum(
        (i.revision.max_marks for i in exam.items.all()),
        Decimal("0"),
    )
    assert total == Decimal("20.00")

    assert QuestionRevision.objects.filter(
        question__topic__unit__slug=slug,
        status="published",
    ).count() == 0

    # Importing twice must not duplicate questions.
    call_command("seed_subject_pilots", "--unit", unit)
    assert exam.items.count() == 12

    student = User.objects.create_user(
        f"{unit}-student@example.test",
        "SafePass!2026",
    )
    api = APIClient()
    api.force_authenticate(user=student)

    listing = api.get("/api/v1/exams/")
    assert listing.status_code == 200

    published_ids = [
        str(entry["id"])
        for entry in listing.data["results"]
    ]

    assert str(exam.id) not in published_ids


@pytest.mark.django_db
@pytest.mark.parametrize("unit,slug", PILOTS)
def test_published_exam_supports_student_attempt(unit, slug):
    reviewer = User.objects.create_superuser(
        f"{unit}-reviewer@example.test",
        "SafePass!2026",
    )
    student = User.objects.create_user(
        f"{unit}-student@example.test",
        "SafePass!2026",
    )

    call_command("seed_subject_pilots", "--unit", unit)

    call_command(
        "seed_subject_pilots",
        "--unit", unit,
        "--publish",
        "--reviewer-email", reviewer.email,
    )

    exam = ExamVersion.objects.get(
        template__unit__slug=slug
    )
    assert exam.is_published

    # Publishing again must not duplicate or modify the exam.
    call_command(
        "seed_subject_pilots",
        "--unit", unit,
        "--publish",
        "--reviewer-email", reviewer.email,
    )

    api = APIClient()
    api.force_authenticate(user=student)

    started = api.post(
        f"/api/v1/exams/{exam.id}/attempts/",
        format="json",
    )

    assert started.status_code == 201, started.data
    assert len(started.data["questions"]) == 12

    # Correct answers and private rubrics must not leak.
    assert "correct_option_id" not in str(started.data)
    assert "rubric" not in str(started.data)

    attempt_id = started.data["id"]

    for question in started.data["questions"]:
        if question["kind"] == "single_choice":
            answer = {
                "selected_option_id": (
                    question["options"][0]["id"]
                )
            }
        else:
            answer = {
                "text_answer": (
                    "This answer requires reviewer marking."
                )
            }

        saved = api.put(
            f"/api/v1/attempts/{attempt_id}"
            f"/responses/{question['id']}/",
            answer,
            format="json",
        )
        assert saved.status_code == 200, saved.data

    submitted = api.post(
        f"/api/v1/attempts/{attempt_id}/submit/"
    )
    assert submitted.status_code == 200

    result = api.get(
        f"/api/v1/attempts/{attempt_id}/result/"
    )
    assert result.status_code == 200
    assert result.data["status"] == "grading_pending"
    assert result.data["ungraded_possible_marks"] == "10.00"
    assert result.data["final_percentage"] is None


@pytest.mark.django_db
@pytest.mark.parametrize("unit,slug", PILOTS)
def test_publishing_requires_authorized_staff(unit, slug):
    student = User.objects.create_user(
        f"{unit}-student@example.test",
        "SafePass!2026",
    )

    call_command("seed_subject_pilots", "--unit", unit)

    with pytest.raises(
        CommandError,
        match="active staff reviewer",
    ):
        call_command(
            "seed_subject_pilots",
            "--unit", unit,
            "--publish",
            "--reviewer-email", student.email,
        )

    exam = ExamVersion.objects.get(
        template__unit__slug=slug
    )
    assert exam.is_published is False
