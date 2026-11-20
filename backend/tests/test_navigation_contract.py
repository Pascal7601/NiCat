"""Student navigation must work with real curricular relationships, not hardcoded IDs."""
import pytest
from django.core.management import call_command
from apps.accounts.models import User
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_bbit_navigation_and_unit_filtered_exam_listing():
    reviewer = User.objects.create_superuser("nav-reviewer@example.test", "ExamplePass!9912")
    student = User.objects.create_user("nav-student@example.test", "ExamplePass!9912")
    call_command("seed_dsa_pilot", publish=True, reviewer_email=reviewer.email)
    client = APIClient()
    token = client.post("/api/v1/auth/login/",
        {"email": student.email, "password": "ExamplePass!9912"}, format="json")
    assert token.status_code == 200
    client.credentials(HTTP_AUTHORIZATION="Bearer " + token.data["access"])

    programmes = client.get("/api/v1/programmes/")
    assert programmes.status_code == 200
    bbit = next(item for item in programmes.data["results"] if item["name"] == "Bachelor of Business Information Technology")
    curricula = client.get(f"/api/v1/programmes/{bbit['id']}/curricula/")
    assert curricula.status_code == 200
    archival = curricula.data["results"][0]
    assert archival["is_officially_verified"] is False
    units = client.get(f"/api/v1/curricula/{archival['id']}/units/")
    assert units.status_code == 200
    dsa = next(item for item in units.data["results"] if item["unit_name"] == "Data Structures and Algorithms")
    assert dsa["year_number"] == 2 and dsa["semester_number"] == 1
    topics = client.get(f"/api/v1/units/{dsa['unit_id']}/topics/")
    assert topics.status_code == 200
    assert {item["title"] for item in topics.data["results"]} >= {"Stacks", "Queues", "Searching", "Sorting", "Trees"}

    exams = client.get(f"/api/v1/exams/?unit_id={dsa['unit_id']}")
    assert exams.status_code == 200 and exams.data["count"] == 1
    exam_id = exams.data["results"][0]["id"]
    single = client.get(f"/api/v1/exams/{exam_id}/")
    assert single.status_code == 200
    assert "questions" not in single.data and "is_correct" not in str(single.data)
    invalid = client.get("/api/v1/exams/?unit_id=not-a-uuid")
    assert invalid.status_code == 400
