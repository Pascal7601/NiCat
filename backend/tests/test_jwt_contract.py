"""JWT contract and revocation tests; intended for PostgreSQL-backed pytest-django."""
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User


@pytest.mark.django_db
def test_login_me_refresh_rotate_logout_and_blacklist():
    user = User.objects.create_user("jwt-student@example.test", "ExamplePass!9912")
    anonymous = APIClient()
    assert anonymous.get("/api/v1/me/").status_code == 401
    login = anonymous.post("/api/v1/auth/login/",
        {"email": "jwt-student@example.test", "password": "ExamplePass!9912"}, format="json")
    assert login.status_code == 200, login.data
    access = login.data["access"]
    refresh = login.data["refresh"]
    assert login.data["user"]["email"] == user.email

    student = APIClient()
    student.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert student.get("/api/v1/me/").status_code == 200
    assert APIClient().get("/api/v1/me/").status_code == 401

    renewed = anonymous.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json")
    assert renewed.status_code == 200, renewed.data
    assert renewed.data["refresh"] != refresh
    assert "access" in renewed.data
    assert anonymous.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json").status_code == 401

    rotated = renewed.data["refresh"]
    logout = student.post("/api/v1/auth/logout/", {"refresh": rotated}, format="json")
    assert logout.status_code == 204, logout.data
    assert anonymous.post("/api/v1/auth/refresh/", {"refresh": rotated}, format="json").status_code == 401
    # Existing bearer tokens remain valid until the short access-token expiry.
    assert student.get("/api/v1/me/").status_code == 200


@pytest.mark.django_db
def test_cannot_logout_another_users_refresh():
    first = User.objects.create_user("jwt-a@example.test", "ExamplePass!9912")
    second = User.objects.create_user("jwt-b@example.test", "ExamplePass!9912")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(first).access_token}")
    other_refresh = str(RefreshToken.for_user(second))
    reply = client.post("/api/v1/auth/logout/", {"refresh": other_refresh}, format="json")
    assert reply.status_code == 400
    assert APIClient().post("/api/v1/auth/refresh/", {"refresh": other_refresh}, format="json").status_code == 200


@pytest.mark.django_db
def test_invalid_password_and_invalid_jwt_not_authenticated():
    User.objects.create_user("jwt-invalid@example.test", "ExamplePass!9912")
    client = APIClient()
    wrong = client.post("/api/v1/auth/login/", {"email": "jwt-invalid@example.test",
        "password": "wrong"}, format="json")
    assert wrong.status_code == 401
    client.credentials(HTTP_AUTHORIZATION="Bearer invalid.not.a.jwt")
    assert client.get("/api/v1/me/").status_code == 401


@pytest.mark.django_db
def test_login_throttle_still_blocks_excessive_attempts():
    client = APIClient()

    credentials = {
        "email": "missing@example.test",
        "password": "incorrect",
    }

    status_codes = [
        client.post(
            "/api/v1/auth/login/",
            credentials,
            format="json",
        ).status_code
        for _ in range(6)
    ]

    assert status_codes[:5] == [401] * 5
    assert status_codes[5] == 429
