"""Sprint 11: owner isolation, rights separation, opt-in and no auto publishing."""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission
from django.test import override_settings
from rest_framework.test import APIClient
from apps.academics.models import Unit
from apps.contributions.models import Contribution, ContributionDecision
from apps.contributions.services import ContributionConflict, approve_academic, clear_rights

URL = "/api/v1/contributions/"
BODY = " ".join(["Binary search halves a sorted search interval, compares the midpoint, and updates left and right boundaries."] * 3)


@pytest.fixture
def sample(db):
    User = get_user_model()
    alice = User.objects.create_user(email="contrib-alice@example.test", password="ExamplePass!100")
    bob = User.objects.create_user(email="contrib-bob@example.test", password="ExamplePass!101")
    rights = User.objects.create_user(email="rights@example.test", password="ExamplePass!102", is_staff=True)
    academic = User.objects.create_user(email="academic@example.test", password="ExamplePass!103", is_staff=True)
    rights.user_permissions.add(Permission.objects.get(codename="review_contribution_rights"))
    # Give this tester BOTH permissions to verify the distinct-person rule still blocks self-approval.
    rights.user_permissions.add(Permission.objects.get(codename="review_contribution_content"))
    academic.user_permissions.add(Permission.objects.get(codename="review_contribution_content"))
    unit = Unit.objects.create(title="DSA Contributions Test", slug="dsa-contrib-test")
    return alice, bob, rights, academic, unit


def data(unit, body=BODY):
    return {"unit_id": str(unit.pk), "title": "My original binary search notes", "body": body, "author_declaration": True, "allow_display": True, "allow_ai_use": False}


@pytest.mark.django_db
def test_flag_closed_and_unauthenticated(sample):
    alice, bob, rights, academic, unit = sample
    client = APIClient()
    with override_settings(NICAT_CONTRIBUTIONS_ENABLED=False):
        client.force_authenticate(user=alice)
        assert client.post(URL, data(unit), format="json").status_code == 404
        assert Contribution.objects.count() == 0
    client.force_authenticate(user=None)
    with override_settings(NICAT_CONTRIBUTIONS_ENABLED=True):
        assert client.post(URL, data(unit), format="json").status_code in (401,403)


@pytest.mark.django_db
def test_private_submission_owner_filter_and_withdraw(sample):
    alice, bob, rights, academic, unit = sample
    owner = APIClient(); owner.force_authenticate(user=alice)
    other = APIClient(); other.force_authenticate(user=bob)
    with override_settings(NICAT_CONTRIBUTIONS_ENABLED=True):
        response = owner.post(URL, data(unit), format="json")
        assert response.status_code == 201, response.data
        id = response.data["id"]
        assert response.data["state"] == "pending_review"
        assert "body" not in response.data and "rights_review_note" not in response.data
        assert other.get(f"{URL}{id}/").status_code == 404
        assert other.post(f"{URL}{id}/withdraw/").status_code == 404
        assert other.get(URL).data["items"] == []
        assert owner.post(f"{URL}{id}/withdraw/").status_code == 200
        assert Contribution.objects.get(pk=id).state == Contribution.State.WITHDRAWN


@pytest.mark.django_db
def test_duplicate_flag_without_other_student_info(sample):
    alice, bob, rights, academic, unit = sample
    c1 = APIClient(); c1.force_authenticate(user=alice)
    c2 = APIClient(); c2.force_authenticate(user=bob)
    with override_settings(NICAT_CONTRIBUTIONS_ENABLED=True):
        assert c1.post(URL, data(unit), format="json").data["possible_duplicate"] is False
        second = c2.post(URL, data(unit), format="json")
        assert second.status_code == 201
        assert second.data["possible_duplicate"] is True
        assert "student" not in second.data and "duplicate_of" not in second.data


@pytest.mark.django_db
def test_two_reviewers_and_audit_before_approval(sample):
    alice, bob, rights, academic, unit = sample
    client = APIClient(); client.force_authenticate(user=alice)
    with override_settings(NICAT_CONTRIBUTIONS_ENABLED=True):
        id = client.post(URL, data(unit), format="json").data["id"]
    entry = Contribution.objects.get(pk=id)
    with pytest.raises(PermissionDenied):
        clear_rights(contribution_id=id, actor=alice)
    entry.rights_review_note = "This appears to be original author-written revision material."
    entry.save(update_fields=["rights_review_note"])
    clear_rights(contribution_id=id, actor=rights)
    entry.refresh_from_db()
    entry.academic_review_note = "Concepts and explanations align with the selected DSA unit."
    entry.save(update_fields=["academic_review_note"])
    with pytest.raises(ContributionConflict, match="Two distinct reviewers"):
        approve_academic(contribution_id=id, actor=rights)
    approve_academic(contribution_id=id, actor=academic)
    entry.refresh_from_db()
    assert entry.state == Contribution.State.APPROVED
    assert list(entry.decisions.values_list("action", flat=True)) == ["approved", "rights_cleared"]
    # No approved source material has been added to Tutor retrieval.
    from apps.resources.models import SourceDocument
    assert not SourceDocument.objects.filter(title=entry.title).exists()


@pytest.mark.django_db
def test_required_rights_declarations_and_daily_limit(sample):
    alice, bob, rights, academic, unit = sample
    client = APIClient(); client.force_authenticate(user=alice)
    with override_settings(NICAT_CONTRIBUTIONS_ENABLED=True, NICAT_CONTRIBUTION_DAILY_LIMIT=1):
        invalid = data(unit)
        invalid["author_declaration"] = False
        assert client.post(URL, invalid, format="json").status_code == 400
        assert Contribution.objects.count() == 0
        assert client.post(URL, data(unit), format="json").status_code == 201
        over = client.post(URL, data(unit, body=BODY + " New paragraph"), format="json")
        assert over.status_code == 429
        assert Contribution.objects.count() == 1
