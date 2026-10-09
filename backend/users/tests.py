import re
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.test import APIClient

from config.settings import build_mailers

User = get_user_model()

PASSWORD = "Zq7!mN2pLxD"

NUEVA_CLAVE = "Xk9!vR3wQzT"

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


# --- Password reset (Plan 2, Fase 1) ---


@pytest.fixture(autouse=True)
def _limpiar_cache_throttle():
    # El throttle usa cache por IP (LocMemCache en tests); se limpia antes de cada
    # test para que el caso de 429 no contamine al resto.
    cache.clear()
    yield


def reset_token(user):
    return (
        urlsafe_base64_encode(force_bytes(user.pk)),
        default_token_generator.make_token(user),
    )


def confirm(api_client, uid, token, password, password2):
    return api_client.post(
        reverse("password_reset_confirm"),
        {"uid": uid, "token": token, "password": password, "password2": password2},
        format="json",
    )


def test_DW_1_1_reset_envia_mail_link_correcto(api_client, user):
    with patch("users.serializers.mail") as mock_mail:
        response = api_client.post(
            reverse("password_reset"), {"email": user.email}, format="json"
        )

    assert response.status_code == 200
    mock_mail.mailers.default.send_messages.assert_called_once()
    # mail.EmailMessage(subject, message, None, [user.email]) — args reales.
    message = mock_mail.EmailMessage.call_args.args[1]
    recipients = mock_mail.EmailMessage.call_args.args[3]
    assert recipients == [user.email]
    m = re.search(r"/restablecer\?uid=([^&\s]+)&token=([^\s]+)", message)
    assert m is not None
    uid, token = m.groups()
    assert force_str(urlsafe_base64_decode(uid)) == str(user.pk)
    assert default_token_generator.check_token(user, token)


def test_DW_1_1_reset_email_inexistente_no_envia(api_client, db):
    with patch("users.serializers.mail") as mock_mail:
        response = api_client.post(
            reverse("password_reset"), {"email": "nadie@example.com"}, format="json"
        )

    assert response.status_code == 200
    mock_mail.mailers.default.send_messages.assert_not_called()


def test_DW_1_1_neutralidad_mismo_cuerpo(api_client, user):
    with patch("users.serializers.mail"):
        existe = api_client.post(
            reverse("password_reset"), {"email": user.email}, format="json"
        )
        inexistente = api_client.post(
            reverse("password_reset"), {"email": "nadie@example.com"}, format="json"
        )

    assert existe.status_code == inexistente.status_code == 200
    assert existe.data == inexistente.data


def test_reset_email_malformado_neutral(api_client, db):
    with patch("users.serializers.mail") as mock_mail:
        response = api_client.post(
            reverse("password_reset"), {"email": "no-es-un-email"}, format="json"
        )

    assert response.status_code == 200
    mock_mail.mailers.default.send_messages.assert_not_called()


def test_reset_smtp_caido_neutral(api_client, user):
    with patch("users.serializers.mail") as mock_mail:
        mock_mail.mailers.default.send_messages.side_effect = ConnectionRefusedError("down")
        response = api_client.post(
            reverse("password_reset"), {"email": user.email}, format="json"
        )

    assert response.status_code == 200


def test_reset_throttle_excedido_429(api_client, db):
    url = reverse("password_reset")
    for _ in range(5):
        r = api_client.post(url, {"email": "x@example.com"}, format="json")
        assert r.status_code == 200

    response = api_client.post(url, {"email": "x@example.com"}, format="json")

    assert response.status_code == 429


def test_DW_1_2_confirm_cambia_clave_login(api_client, user):
    uid, token = reset_token(user)

    response = confirm(api_client, uid, token, NUEVA_CLAVE, NUEVA_CLAVE)

    assert response.status_code == 200
    assert login(api_client, user.email, PASSWORD).status_code == 401
    assert login(api_client, user.email, NUEVA_CLAVE).status_code == 200


def test_DW_1_3_token_invalido_400(api_client, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    response = confirm(api_client, uid, "token-invalido", NUEVA_CLAVE, NUEVA_CLAVE)

    assert response.status_code == 400
    assert "detail" in response.data
    assert login(api_client, user.email, PASSWORD).status_code == 200


@override_settings(PASSWORD_RESET_TIMEOUT=-1)
def test_DW_1_3_token_expirado_400(api_client, user):
    uid, token = reset_token(user)

    response = confirm(api_client, uid, token, NUEVA_CLAVE, NUEVA_CLAVE)

    assert response.status_code == 400
    assert login(api_client, user.email, PASSWORD).status_code == 200


def test_DW_1_3_token_reusado_400(api_client, user):
    uid, token = reset_token(user)
    assert confirm(api_client, uid, token, NUEVA_CLAVE, NUEVA_CLAVE).status_code == 200

    reuso = confirm(api_client, uid, token, "OtraClave9!", "OtraClave9!")

    assert reuso.status_code == 400
    assert login(api_client, user.email, NUEVA_CLAVE).status_code == 200
    assert login(api_client, user.email, "OtraClave9!").status_code == 401


def test_DW_1_3_uid_roto_400(api_client, user):
    response = confirm(api_client, "!!!no-base64!!!", "abc", NUEVA_CLAVE, NUEVA_CLAVE)

    assert response.status_code == 400
    assert login(api_client, user.email, PASSWORD).status_code == 200


def test_DW_1_4_password_debil_400(api_client, user):
    uid, token = reset_token(user)

    response = confirm(api_client, uid, token, "12345678", "12345678")

    assert response.status_code == 400
    assert "password" in response.data
    assert login(api_client, user.email, PASSWORD).status_code == 200


def test_DW_1_4_password_mismatch_400(api_client, user):
    uid, token = reset_token(user)

    response = confirm(api_client, uid, token, NUEVA_CLAVE, "ClaveDistinta9!")

    assert response.status_code == 400
    assert "password2" in response.data
    assert login(api_client, user.email, PASSWORD).status_code == 200


def test_DW_1_5_mailers_consola_por_defecto():
    mailers = build_mailers({})

    assert mailers["default"]["BACKEND"] == "django.core.mail.backends.console.EmailBackend"


def test_DW_1_5_mailers_smtp_con_email_host():
    mailers = build_mailers({"EMAIL_HOST": "smtp.example.com"})

    assert mailers["default"]["BACKEND"] == "django.core.mail.backends.smtp.EmailBackend"
    assert mailers["default"]["OPTIONS"]["host"] == "smtp.example.com"
