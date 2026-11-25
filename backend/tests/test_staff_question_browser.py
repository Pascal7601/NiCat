"""Sprint 13.5: tutor question browsing is staff-only and never leaks keys."""
from decimal import Decimal

import pytest
from django.test import override_settings

from apps.academics.models import CurriculumUnit, CurriculumVersion, Programme, Topic, Unit, University
from apps.questions.models import ChoiceOption, Question, QuestionRevision
from apps.resources.models import SourceDocument
from apps.study_tutor.models import SourceExcerpt
from apps.study_tutor.services import approve_excerpt
from .test_staff_workspace import as_user, grant, users  # noqa: F401 - shared fixture

ENDPOINT = "/api/v1/staff/questions/search/"


def publish_question(topic, academic, *, prompt, number=1, published=True):
    question = Question.objects.create(topic=topic)
    revision = QuestionRevision.objects.create(
        question=question, number=number,
        kind=QuestionRevision.Kind.SINGLE_CHOICE,
        provenance=QuestionRevision.Provenance.ORIGINAL,
        prompt=prompt, max_marks=Decimal("2.00"),
    )
    ChoiceOption.objects.create(revision=revision, text="Correct private option", position=1, is_correct=True)
    ChoiceOption.objects.create(revision=revision, text="Wrong private option", position=2, is_correct=False)
    if published:
        revision.status = QuestionRevision.Status.PUBLISHED
        revision.reviewed_by = academic
        revision.save()
    return revision


@pytest.mark.django_db
def test_question_browser_permissions_and_no_answers(users):
    student, outsider, editor, rights, academic, unit, topic, document, reference = users
    revision = publish_question(topic, academic, prompt="What is the purpose of least privilege?")
    with override_settings(NICAT_STAFF_WORKSPACE_ENABLED=False):
        assert as_user(academic).post(ENDPOINT, {}, format="json").status_code == 404
    with override_settings(NICAT_STAFF_WORKSPACE_ENABLED=True):
        assert as_user(student).post(ENDPOINT, {}, format="json").status_code == 403
        assert as_user(editor).post(ENDPOINT, {}, format="json").status_code == 403
        # Tutor reviewers must explicitly have question-browser read permission.
        assert as_user(academic).post(ENDPOINT, {}, format="json").status_code == 403
        grant(academic, "questions", "view_questionrevision")
        response = as_user(academic).post(ENDPOINT, {}, format="json")
        assert response.status_code == 200, response.data
        assert response.data["total"] == 1
        item = response.data["items"][0]
        assert item["id"] == str(revision.pk)
        assert item["prompt"] == revision.prompt
        assert item["approved_excerpt_count"] == 0
        assert not ({"is_correct", "options", "rubric", "answer", "source_reference"} & item.keys())
        assert "Correct private option" not in str(response.data)
        assert "Wrong private option" not in str(response.data)


@pytest.mark.django_db
def test_programme_unit_topic_filter_and_exclude_unpublished(users):
    student, outsider, editor, rights, academic, unit, topic, document, reference = users
    grant(academic, "questions", "view_questionrevision")
    a = University.objects.create(name="Example University A", abbreviation="A")
    prog_a = Programme.objects.create(university=a, name="BBIT")
    prog_b = Programme.objects.create(university=a, name="BSc CS")
    version_a = CurriculumVersion.objects.create(programme=prog_a, label="2026 example A")
    version_b = CurriculumVersion.objects.create(programme=prog_b, label="2026 example B")
    second_unit = Unit.objects.create(title="Computer Graphics", slug="browser-computer-graphics")
    second_topic = Topic.objects.create(unit=second_unit, title="2D Transformations")
    CurriculumUnit.objects.create(curriculum_version=version_a, unit=unit, year_number=2, semester_number=1)
    CurriculumUnit.objects.create(curriculum_version=version_b, unit=second_unit, year_number=3, semester_number=2)
    first = publish_question(topic, academic, prompt="Describe least privilege.")
    second = publish_question(second_topic, academic, prompt="Apply a 2D translation.")
    publish_question(second_topic, academic, prompt="Draft private question.", published=False)

    with override_settings(NICAT_STAFF_WORKSPACE_ENABLED=True):
        selected = as_user(academic).post(ENDPOINT, {"programme_id": str(prog_a.pk)}, format="json")
        assert selected.status_code == 200, selected.data
        assert selected.data["total"] == 1
        assert selected.data["items"][0]["id"] == str(first.pk)
        assert len(selected.data["units"]) == 1

        selected = as_user(academic).post(ENDPOINT, {
            "programme_id": str(prog_b.pk),
            "unit_id": str(second_unit.pk),
            "topic_id": str(second_topic.pk),
            "search": "translation",
        }, format="json")
        assert selected.status_code == 200, selected.data
        assert [x["id"] for x in selected.data["items"]] == [str(second.pk)]
        assert selected.data["total"] == 1

        mismatched = as_user(academic).post(ENDPOINT, {"programme_id": str(prog_a.pk), "unit_id": str(second_unit.pk)}, format="json")
        assert mismatched.data["items"] == []
        assert mismatched.data["total"] == 0
        assert as_user(academic).post(ENDPOINT, {"limit": 501}, format="json").status_code == 400
        assert as_user(academic).post(ENDPOINT, {"programme_id": "invalid"}, format="json").status_code == 400


@pytest.mark.django_db
def test_source_indicator_only_counts_current_approved_matching_evidence(users):
    student, outsider, editor, rights, academic, unit, topic, document, reference = users
    grant(academic, "questions", "view_questionrevision")
    question = publish_question(topic, academic, prompt="Explain role based access control.")
    document.rights_status = SourceDocument.Rights.ALLOWED
    document.save()
    excerpt = SourceExcerpt.objects.create(
        topic=topic, reference=reference,
        text="Role-based access control assigns permissions to roles and avoids redundant per-user grants.",
    )
    approve_excerpt(excerpt_id=excerpt.pk, actor=academic)
    with override_settings(NICAT_STAFF_WORKSPACE_ENABLED=True):
        response = as_user(academic).post(ENDPOINT, {"search": "access control"}, format="json")
        assert response.status_code == 200
        assert response.data["items"][0]["id"] == str(question.pk)
        assert response.data["items"][0]["approved_excerpt_count"] == 1
        document.rights_status = SourceDocument.Rights.RESTRICTED
        document.save()
        response = as_user(academic).post(ENDPOINT, {}, format="json")
        assert response.data["items"][0]["approved_excerpt_count"] == 0


@pytest.mark.django_db
def test_question_search_is_bounded_and_paginated(users):
    student, outsider, editor, rights, academic, unit, topic, document, reference = users
    grant(academic, "questions", "view_questionrevision")
    for number in range(3):
        publish_question(topic, academic, prompt=f"Explain access control rule {number}.")
    with override_settings(NICAT_STAFF_WORKSPACE_ENABLED=True):
        first = as_user(academic).post(ENDPOINT, {"limit": 1, "offset": 0}, format="json")
        assert first.status_code == 200, first.data
        assert first.data["total"] == 3
        assert len(first.data["items"]) == 1
        assert first.data["has_more"] is True
        second = as_user(academic).post(ENDPOINT, {"limit": 1, "offset": 1}, format="json")
        assert second.status_code == 200
        assert second.data["items"][0]["id"] != first.data["items"][0]["id"]
