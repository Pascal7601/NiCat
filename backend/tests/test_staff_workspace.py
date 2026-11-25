"""Sprint 12: staff permissions, source-rights auditing and two-person review."""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from rest_framework.test import APIClient

from apps.academics.models import Topic, Unit
from apps.contributions.models import Contribution, ContributionDecision
from apps.resources.models import SourceDocument, SourceReference
from apps.staff_workspace.models import SourceRightsDecision
from apps.study_tutor.models import SourceExcerpt

BASE = "/api/v1/staff"
NOTE = "This is my independently authored revision explanation. " * 5
RIGHTS_EVIDENCE = "Verified author ownership and explicit educational reuse permission in writing."


def grant(user, app, *codenames):
    for code in codenames:
        user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=code))


def as_user(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def users(db):
    User = get_user_model()
    student = User.objects.create_user(email="stf-student@example.test", password="GoodPass123!")
    outsider = User.objects.create_user(email="stf-other@example.test", password="GoodPass123!")
    editor = User.objects.create_user(email="stf-editor@example.test", password="GoodPass123!", is_staff=True)
    rights = User.objects.create_user(email="stf-rights@example.test", password="GoodPass123!", is_staff=True)
    academic = User.objects.create_user(email="stf-academic@example.test", password="GoodPass123!", is_staff=True)
    grant(editor, "resources", "view_sourcedocument", "add_sourcedocument", "view_sourcereference", "add_sourcereference")
    grant(editor, "study_tutor", "view_sourceexcerpt", "add_sourceexcerpt")
    grant(rights, "resources", "view_sourcedocument", "change_sourcedocument")
    grant(rights, "staff_workspace", "review_source_rights")
    grant(rights, "contributions", "view_contribution", "change_contribution", "review_contribution_rights")
    grant(academic, "study_tutor", "view_sourceexcerpt", "approve_tutor_content", "view_tutorexplanation")
    grant(academic, "contributions", "view_contribution", "change_contribution", "review_contribution_content")
    grant(academic, "study_coach", "view_tutorfollowup")
    unit = Unit.objects.create(title="Security Engineering Test Unit", slug="stf-security-engineering")
    topic = Topic.objects.create(title="Identity and Access", unit=unit)
    document = SourceDocument.objects.create(title="Original test notes", unit=unit, source_kind="lecture_notes")
    reference = SourceReference.objects.create(document=document, page_label="3", section_label="Principles")
    return student, outsider, editor, rights, academic, unit, topic, document, reference


@pytest.mark.django_db
def test_staff_workspace_disabled_and_ordinary_student_denied(users):
    student, _, editor, *_ = users
    with override_settings(NICAT_STAFF_WORKSPACE_ENABLED=False):
        assert as_user(editor).get(f"{BASE}/overview/").status_code == 404
    with override_settings(NICAT_STAFF_WORKSPACE_ENABLED=True):
        assert as_user(student).get(f"{BASE}/overview/").status_code == 403
        assert as_user(student).get(f"{BASE}/sources/documents/").status_code == 403
        assert as_user(student).post(f"{BASE}/tutor/generate/", {"revision_id": "not-a-uuid"}, format="json").status_code == 403


@pytest.mark.django_db
def test_source_registration_rights_audit_and_approval(users):
    student, outsider, editor, rights, academic, unit, topic, document, reference = users
    with override_settings(NICAT_STAFF_WORKSPACE_ENABLED=True):
        created = as_user(editor).post(f"{BASE}/sources/documents/", {
            "title": "Verified original course notes", "unit_id": str(unit.pk),
            "source_kind": "lecture_notes",
        }, format="json")
        assert created.status_code == 201, created.data
        assert created.data["rights_status"] == "unknown"

        data = {"rights_status": "allowed", "rationale": RIGHTS_EVIDENCE}
        assert as_user(editor).post(f"{BASE}/sources/documents/{document.pk}/rights/", data, format="json").status_code == 403
        assert as_user(rights).post(f"{BASE}/sources/documents/{document.pk}/rights/", {
            **data, "rationale": "too short"}, format="json").status_code == 400
        reply = as_user(rights).post(f"{BASE}/sources/documents/{document.pk}/rights/", data, format="json")
        assert reply.status_code == 200, reply.data
        assert SourceRightsDecision.objects.filter(document=document, actor=rights,
            previous_status="unknown", new_status="allowed").count() == 1

        text = "This original excerpt describes access control, least privilege, and role separation for practice learners."
        excerpt = as_user(editor).post(f"{BASE}/sources/excerpts/", {
            "reference_id": str(reference.pk), "topic_id": str(topic.pk), "text": text,
        }, format="json")
        assert excerpt.status_code == 201, excerpt.data
        path = f"{BASE}/sources/excerpts/{excerpt.data['id']}/action/"
        assert as_user(editor).post(path, {"action": "approve"}, format="json").status_code == 403
        approved = as_user(academic).post(path, {"action": "approve"}, format="json")
        assert approved.status_code == 200, approved.data
        assert SourceExcerpt.objects.get(pk=excerpt.data["id"]).state == SourceExcerpt.State.APPROVED


@pytest.mark.django_db
def test_topic_mismatch_and_rights_gate(users):
    student, outsider, editor, rights, academic, unit, topic, document, reference = users
    other_unit = Unit.objects.create(title="Different unit", slug="stf-different")
    wrong_topic = Topic.objects.create(unit=other_unit, title="Other unit")
    text = "A sufficiently long academic excerpt addressing a clearly defined topic with original language."
    with override_settings(NICAT_STAFF_WORKSPACE_ENABLED=True):
        mismatch = as_user(editor).post(f"{BASE}/sources/excerpts/", {
            "reference_id": str(reference.pk), "topic_id": str(wrong_topic.pk), "text": text,
        }, format="json")
        assert mismatch.status_code == 400
        created = as_user(editor).post(f"{BASE}/sources/excerpts/", {
            "reference_id": str(reference.pk), "topic_id": str(topic.pk), "text": text,
        }, format="json")
        assert created.status_code == 201
        premature = as_user(academic).post(f"{BASE}/sources/excerpts/{created.data['id']}/action/", {
            "action": "approve"}, format="json")
        assert premature.status_code == 409


@pytest.mark.django_db
def test_private_contribution_review_and_two_people(users):
    student, outsider, editor, rights, academic, unit, topic, document, reference = users
    contribution = Contribution.objects.create(
        student=student, unit=unit, title="My original notes", body=NOTE,
        author_declaration=True, allow_display=True, content_sha256="a" * 64,
    )
    detail = f"{BASE}/contributions/{contribution.pk}/"
    act = f"{BASE}/contributions/{contribution.pk}/action/"
    with override_settings(NICAT_STAFF_WORKSPACE_ENABLED=True):
        assert as_user(student).get(detail).status_code == 403
        assert as_user(editor).get(detail).status_code == 403
        assert as_user(rights).get(detail).status_code == 200
        note = "This is verified original writing with explicit display permission."
        assert as_user(rights).post(detail, {"field": "rights_review_note", "note": note}, format="json").status_code == 200
        assert as_user(rights).post(act, {"action": "clear_rights"}, format="json").status_code == 200
        # Even a rights-reviewer with content rights must not self-approve.
        grant(rights, "contributions", "review_contribution_content")
        assert as_user(rights).post(detail, {"field": "academic_review_note", "note": "The material is educationally accurate and well categorized."}, format="json").status_code == 200
        assert as_user(rights).post(act, {"action": "approve"}, format="json").status_code == 409
        assert as_user(academic).post(act, {"action": "approve"}, format="json").status_code == 200
    contribution.refresh_from_db()
    assert contribution.state == Contribution.State.APPROVED
    assert ContributionDecision.objects.filter(contribution=contribution).count() == 2
    from apps.study_tutor.models import SourceExcerpt
    assert SourceExcerpt.objects.count() == 0  # No auto-publication/indexing


@pytest.mark.django_db
def test_no_direct_non_reviewer_tutor_or_followup_action(users):
    student, outsider, editor, rights, academic, unit, topic, document, reference = users
    with override_settings(NICAT_STAFF_WORKSPACE_ENABLED=True):
        assert as_user(editor).get(f"{BASE}/tutor/").status_code == 403
        assert as_user(editor).get(f"{BASE}/followups/").status_code == 403
        assert as_user(student).post(
            f"{BASE}/contributions/00000000-0000-4000-8000-000000000001/action/",
            {"action": "approve"}, format="json",
        ).status_code == 403
        assert as_user(academic).get(f"{BASE}/tutor/").status_code == 200
        assert as_user(academic).get(f"{BASE}/followups/").status_code == 200


@pytest.mark.django_db
def test_permissions_limit_overview_counts(users):
    student, outsider, editor, rights, academic, unit, topic, document, reference = users
    with override_settings(NICAT_STAFF_WORKSPACE_ENABLED=True):
        data = as_user(editor).get(f"{BASE}/overview/")
        assert data.status_code == 200
        assert data.data["permissions"]["sources"] is True
        assert "contributions_pending" not in data.data["counts"]
