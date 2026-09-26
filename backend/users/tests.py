import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

PASSWORD = "Zq7!mN2pLxD"


def test_auth_user_model():
    assert settings.AUTH_USER_MODEL == "users.User"


def register_payload(**overrides):
    data = {
        "email": "ana@example.com",
        "username": "ana",
        "dni": "30111222",
        "first_name": "Ana",
        "last_name": "Perez",
        "password": PASSWORD,
        "password2": PASSWORD,
    }
    data.update(overrides)
    return data


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="base@example.com",
        username="base",
        dni="30000000",
        password=PASSWORD,
    )


def login(api_client, email, password):
    return api_client.post(
        reverse("login"), {"email": email, "password": password}, format="json"
    )


def authenticate(api_client, user):
    token = login(api_client, user.email, PASSWORD).data["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


def test_register_ok(api_client, db):
    response = api_client.post(reverse("register"), register_payload(), format="json")

    assert response.status_code == 201
    assert response.data["access"]
    assert response.data["refresh"]
    assert response.data["user"]["email"] == "ana@example.com"
    assert "password" not in response.data["user"]
    assert User.objects.filter(email="ana@example.com").exists()


def test_register_invalid_email(api_client, db):
    response = api_client.post(
        reverse("register"), register_payload(email="not-an-email"), format="json"
    )

    assert response.status_code == 400
    assert "email" in response.data


def test_register_duplicate_email(api_client, user):
    response = api_client.post(
        reverse("register"), register_payload(email=user.email), format="json"
    )

    assert response.status_code == 400
    assert "email" in response.data


def test_register_duplicate_username(api_client, user):
    response = api_client.post(
        reverse("register"), register_payload(username=user.username), format="json"
    )

    assert response.status_code == 400
    assert "username" in response.data


def test_register_duplicate_dni(api_client, user):
    response = api_client.post(
        reverse("register"), register_payload(dni=user.dni), format="json"
    )

    assert response.status_code == 400
    assert "dni" in response.data


def test_register_weak_password(api_client, db):
    response = api_client.post(
        reverse("register"),
        register_payload(password="12345678", password2="12345678"),
        format="json",
    )

    assert response.status_code == 400
    assert "password" in response.data


def test_register_password_mismatch(api_client, db):
    response = api_client.post(
        reverse("register"), register_payload(password2="Zq7!mN2pLxE"), format="json"
    )

    assert response.status_code == 400
    assert "password2" in response.data


def test_register_missing_fields(api_client, db):
    response = api_client.post(reverse("register"), {}, format="json")

    assert response.status_code == 400
    for field in ["email", "username", "dni", "password", "password2"]:
        assert field in response.data


def test_login_ok(api_client, user):
    response = login(api_client, user.email, PASSWORD)

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


def test_login_bad_password(api_client, user):
    response = login(api_client, user.email, "wrong-pass")

    assert response.status_code == 401


def test_me_requires_token(api_client):
    response = api_client.get(reverse("me"))

    assert response.status_code == 401


def test_me_ok(api_client, user):
    authenticate(api_client, user)

    response = api_client.get(reverse("me"))

    assert response.status_code == 200
    assert response.data["email"] == user.email
    assert response.data["dni"] == user.dni


def test_patch_me_updates_allowed_fields(api_client, user):
    authenticate(api_client, user)

    response = api_client.patch(
        reverse("me"), {"first_name": "Nueva", "ciudad": "Rosario"}, format="json"
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == "Nueva"
    assert user.ciudad == "Rosario"


def test_patch_me_ignores_immutable_fields(api_client, user):
    authenticate(api_client, user)

    response = api_client.patch(
        reverse("me"), {"email": "otro@example.com", "dni": "99999999"}, format="json"
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email == "base@example.com"
    assert user.dni == "30000000"
