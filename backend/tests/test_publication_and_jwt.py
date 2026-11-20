"""Security and content release regression tests (needs Django installed)."""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.academics.models import Unit, Topic
from apps.exams.models import ExamTemplate, ExamVersion, ExamQuestion
from apps.questions.models import Question, QuestionRevision, ChoiceOption
from apps.accounts.models import User


@pytest.mark.django_db
def test_empty_exam_cannot_be_published():
    unit = Unit.objects.create(title="Test Empty", slug="empty-versions")
    template = ExamTemplate.objects.create(unit=unit, title="Test Empty")
    version = ExamVersion.objects.create(template=template, number=1, duration_seconds=600)
    version.is_published = True
    with pytest.raises(ValidationError):
        version.save()
    version.refresh_from_db()
    assert version.is_published is False


@pytest.mark.django_db
def test_duplicate_question_revisions_cannot_publish():
    unit = Unit.objects.create(title="Test Duplicates", slug="duplicate-versions")
    topic = Topic.objects.create(unit=unit, title="Unit 1")
    question = Question.objects.create(topic=topic)
    revision = QuestionRevision.objects.create(question=question, number=1, kind="single_choice",
        provenance="original_practice", prompt="1+1", max_marks=Decimal("2"))
    ChoiceOption.objects.create(revision=revision, position=1, text="2", is_correct=True)
    ChoiceOption.objects.create(revision=revision, position=2, text="3", is_correct=False)
    reviewer = User.objects.create_user("reviewer-duplicates@example.test", "Str0ng!TestPassword", is_staff=True)
    revision.reviewed_by = reviewer
    revision.status = QuestionRevision.Status.PUBLISHED
    revision.save()
    template = ExamTemplate.objects.create(unit=unit, title="Duplicates")
    version = ExamVersion.objects.create(template=template, number=1, duration_seconds=600)
    ExamQuestion.objects.create(version=version, revision=revision, position=1)
    ExamQuestion.objects.create(version=version, revision=revision, position=2)
    version.is_published = True
    with pytest.raises(ValidationError):
        version.save()


@pytest.mark.django_db
def test_jwt_register_does_not_require_legacy_session_csrf():
    client = APIClient(enforce_csrf_checks=True)
    body = {"email": "jwt-register@example.test", "password": "UncommonPassword$5527"}
    response = client.post("/api/v1/auth/register/", body, format="json")
    assert response.status_code == 201, response.data
    assert User.objects.filter(email=body["email"]).exists()
    assert "password" not in response.data


@pytest.mark.django_db
def test_login_returns_jwt_not_session_cookie():
    User.objects.create_user("jwt-login@example.test", "SafeTestPassword%200")
    client = APIClient(enforce_csrf_checks=True)
    response = client.post("/api/v1/auth/login/",
        {"email": "jwt-login@example.test", "password": "SafeTestPassword%200"}, format="json")
    assert response.status_code == 200, response.data
    assert "access" in response.data and "refresh" in response.data
    assert "sessionid" not in client.cookies


@pytest.mark.django_db
def test_unpublished_revision_allowed_in_draft_but_blocks_exam_publication():
    unit = Unit.objects.create(
        title="Pilot Draft",
        slug="pilot-draft-test",
    )

    topic = Topic.objects.create(
        unit=unit,
        title="Algorithms",
    )

    question = Question.objects.create(topic=topic)

    revision = QuestionRevision.objects.create(
        question=question,
        number=1,
        kind=QuestionRevision.Kind.SINGLE_CHOICE,
        provenance=QuestionRevision.Provenance.ORIGINAL,
        prompt="What is a stack?",
        max_marks=Decimal("1"),
    )

    template = ExamTemplate.objects.create(
        unit=unit,
        title="Draft exam",
    )

    version = ExamVersion.objects.create(
        template=template,
        number=1,
        duration_seconds=600,
    )

    ExamQuestion.objects.create(
        version=version,
        revision=revision,
        position=1,
    )

    assert version.items.count() == 1
    assert not version.is_published

    version.is_published = True

    with pytest.raises(
        ValidationError,
        match="unpublished question",
    ):
        version.save()

    version.refresh_from_db()
    assert version.is_published is False
