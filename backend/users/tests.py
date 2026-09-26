import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

PASSWORD = "Zq7!mN2pLxD"

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


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


def test_patch_me_response_shape(api_client, user):
    authenticate(api_client, user)

    response = api_client.patch(reverse("me"), {"first_name": "Nueva"}, format="json")

    assert response.status_code == 200
    for field in ["first_name", "last_name", "telefono", "genero", "direccion", "ciudad", "foto"]:
        assert field in response.data
    assert response.data["first_name"] == "Nueva"
    assert "email" not in response.data
    assert "password" not in response.data


def test_patch_me_uploads_foto(api_client, user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    authenticate(api_client, user)
    upload = SimpleUploadedFile("foto.png", PNG_1X1, content_type="image/png")

    response = api_client.patch(reverse("me"), {"foto": upload}, format="multipart")

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.foto
    assert user.foto.name.endswith(".png")


def test_refresh_token(api_client, user):
    login_response = login(api_client, user.email, PASSWORD)

    response = api_client.post(
        reverse("token_refresh"), {"refresh": login_response.data["refresh"]}, format="json"
    )

    assert response.status_code == 200
    assert "access" in response.data
