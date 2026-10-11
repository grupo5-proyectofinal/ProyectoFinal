import re
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.test import APIClient

from config.settings import build_mailers
from pools.models import Category, Membership, Pool

User = get_user_model()

PASSWORD = "Zq7!mN2pLxD"

NUEVA_CLAVE = "Xk9!vR3wQzT"

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


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


# --- Backoffice admin API (Plan 2, Fase 3) ---


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="admin@example.com",
        username="admin",
        dni="30111223",
        first_name="Admin",
        last_name="Sistema",
        password=PASSWORD,
        is_staff=True,
    )


def listar(api_client, **query):
    return api_client.get(reverse("admin_usuario_lista"), query, format="json")


def detalle(api_client, pk):
    return api_client.get(reverse("admin_usuario_detalle", kwargs={"pk": pk}))


def parchear(api_client, pk, data):
    return api_client.patch(
        reverse("admin_usuario_detalle", kwargs={"pk": pk}), data, format="json"
    )


def test_DW_3_1_no_staff_403_en_todos(api_client, user, db):
    authenticate(api_client, user)

    assert listar(api_client).status_code == 403
    assert api_client.post(
        reverse("admin_usuario_lista"), register_payload(), format="json"
    ).status_code == 403
    assert detalle(api_client, user.pk).status_code == 403
    assert parchear(api_client, user.pk, {"first_name": "X"}).status_code == 403


def test_DW_3_1_staff_200(api_client, staff_user, user):
    authenticate(api_client, staff_user)

    assert listar(api_client).status_code == 200
    assert detalle(api_client, user.pk).status_code == 200


def test_DW_3_1_anonimo_401(api_client, db):
    assert listar(api_client).status_code == 401
    assert api_client.post(
        reverse("admin_usuario_lista"), register_payload(), format="json"
    ).status_code == 401


def test_DW_3_2_filtra_q(api_client, staff_user, db):
    authenticate(api_client, staff_user)
    User.objects.create_user(
        email="lucas@example.com", username="lucas", dni="31111222",
        first_name="Lucas", last_name="Gomez", password=PASSWORD,
    )
    User.objects.create_user(
        email="maria@example.com", username="maria", dni="32222333",
        first_name="Maria", last_name="Rodriguez", password=PASSWORD,
    )
    User.objects.create_user(
        email="ana@example.com", username="ana", dni="33333444",
        first_name="Ana", last_name="Perez", password=PASSWORD,
    )

    # por email
    assert [u["email"] for u in listar(api_client, q="lucas").data["results"]] == ["lucas@example.com"]
    # por username
    assert [u["username"] for u in listar(api_client, q="maria").data["results"]] == ["maria"]
    # por nombre
    assert [u["email"] for u in listar(api_client, q="ana").data["results"]] == ["ana@example.com"]
    # por apellido
    assert [u["email"] for u in listar(api_client, q="gomez").data["results"]] == ["lucas@example.com"]
    # sin coincidencias
    assert listar(api_client, q="nadie").data["count"] == 0


def test_DW_3_2_filtra_is_active(api_client, staff_user, db):
    authenticate(api_client, staff_user)
    activo = User.objects.create_user(
        email="activo@example.com", username="activo", dni="34444555", password=PASSWORD
    )
    inactivo = User.objects.create_user(
        email="inactivo@example.com", username="inactivo", dni="35555666",
        password=PASSWORD, is_active=False,
    )

    activos = listar(api_client, is_active="true").data["results"]
    inactivos = listar(api_client, is_active="false").data["results"]

    assert {u["id"] for u in activos} == {staff_user.pk, activo.pk}
    assert [u["id"] for u in inactivos] == [inactivo.pk]


def test_DW_3_2_paginado_12(api_client, staff_user, db):
    authenticate(api_client, staff_user)
    for i in range(13):
        User.objects.create_user(
            email=f"u{i}@example.com", username=f"u{i}", dni=f"{40000000 + i}",
            password=PASSWORD,
        )

    primera = listar(api_client)
    assert len(primera.data["results"]) == 12
    assert primera.data["count"] == 14  # 13 + staff

    segunda = listar(api_client, page=2)
    assert len(segunda.data["results"]) == 2


def test_DW_3_3_patch_edita_permitidos(api_client, staff_user, user):
    authenticate(api_client, staff_user)

    response = parchear(api_client, user.pk, {"first_name": "Nueva", "ciudad": "Rosario"})

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == "Nueva"
    assert user.ciudad == "Rosario"


def test_DW_3_3_desactivar_bloquea_login_y_reactivar_restaura(api_client, staff_user, user):
    authenticate(api_client, staff_user)

    assert parchear(api_client, user.pk, {"is_active": False}).status_code == 200
    user.refresh_from_db()
    assert user.is_active is False
    assert login(api_client, user.email, PASSWORD).status_code == 401

    assert parchear(api_client, user.pk, {"is_active": True}).status_code == 200
    user.refresh_from_db()
    assert user.is_active is True
    assert login(api_client, user.email, PASSWORD).status_code == 200


def test_DW_3_4_no_desactivarse_a_si_mismo(api_client, staff_user):
    authenticate(api_client, staff_user)

    response = parchear(api_client, staff_user.pk, {"is_active": False})

    assert response.status_code == 400
    assert "is_active" in response.data
    staff_user.refresh_from_db()
    assert staff_user.is_active is True


def test_DW_3_4_ignora_inmutables(api_client, staff_user, user):
    authenticate(api_client, staff_user)

    response = parchear(
        api_client,
        user.pk,
        {"email": "otro@example.com", "dni": "99999999",
         "username": "otro", "is_staff": True},
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email == "base@example.com"
    assert user.dni == "30000000"
    assert user.username == "base"
    assert user.is_staff is False


def test_DW_3_5_alta_crea_usuario(api_client, staff_user, db):
    authenticate(api_client, staff_user)

    response = api_client.post(
        reverse("admin_usuario_lista"), register_payload(), format="json"
    )

    assert response.status_code == 201
    assert response.data["is_staff"] is False
    assert response.data["is_active"] is True
    assert "password" not in response.data
    assert "access" not in response.data
    assert login(api_client, "ana@example.com", PASSWORD).status_code == 200


def test_DW_3_5_alta_duplicados_400(api_client, staff_user, user):
    authenticate(api_client, staff_user)

    for override in (
        {"email": user.email},
        {"username": user.username},
        {"dni": user.dni},
    ):
        response = api_client.post(
            reverse("admin_usuario_lista"), register_payload(**override), format="json"
        )
        assert response.status_code == 400
        campo = next(iter(override))
        assert campo in response.data


def test_DW_3_6_me_incluye_is_staff(api_client, staff_user, user):
    authenticate(api_client, staff_user)
    assert api_client.get(reverse("me")).data["is_staff"] is True

    authenticate(api_client, user)
    assert api_client.get(reverse("me")).data["is_staff"] is False


def test_admin_usuario_inexistente_404(api_client, staff_user, db):
    authenticate(api_client, staff_user)

    assert detalle(api_client, 999999).status_code == 404
    assert parchear(api_client, 999999, {"first_name": "X"}).status_code == 404


def test_admin_patch_vacio_200_sin_cambios(api_client, staff_user, user):
    authenticate(api_client, staff_user)
    original = {f: getattr(user, f) for f in ("first_name", "last_name", "ciudad", "is_active")}

    response = parchear(api_client, user.pk, {})

    assert response.status_code == 200
    user.refresh_from_db()
    for field, valor in original.items():
        assert getattr(user, field) == valor


def test_admin_q_vacio_lista_completa(api_client, staff_user, user):
    authenticate(api_client, staff_user)

    response = listar(api_client, q="")

    assert response.status_code == 200
    assert response.data["count"] == 2  # staff + user


# --- Perfil público y pools en común (Plan 3, Fase 1) ---


def _usuario(email, username, dni):
    return User.objects.create_user(
        email=email, username=username, dni=dni, password=PASSWORD
    )


def _pool(creador, categoria, titulo):
    return Pool.objects.create(
        creador=creador,
        categoria=categoria,
        titulo=titulo,
        nombre_producto="Producto",
        precio_unitario="100.00",
        cantidad_total=10,
        cantidad_creador=1,
        fecha_caducidad=timezone.localdate() + timedelta(days=7),
        direccion="Calle 1",
        ciudad="Cordoba",
    )


def test_DW_1_3_pools_en_comun_correctos(api_client, db):
    ana = _usuario("ana@example.com", "ana", "30000001")
    bea = _usuario("bea@example.com", "bea", "30000002")
    categoria = Category.objects.create(nombre="Prueba")

    compartido = _pool(ana, categoria, "Compartido")  # ana crea, bea se une
    Membership.objects.create(pool=compartido, usuario=bea, cantidad=1)
    _pool(ana, categoria, "Solo Ana")
    _pool(bea, categoria, "Solo Bea")

    authenticate(api_client, bea)
    response = api_client.get(reverse("usuario_perfil", kwargs={"pk": ana.pk}))
    assert response.status_code == 200
    assert {p["titulo"] for p in response.data["pools_en_comun"]} == {"Compartido"}
    assert response.data["pools_creados"] == 2  # Compartido + Solo Ana
    assert response.data["pools_unidos"] == 0

    authenticate(api_client, ana)
    response = api_client.get(reverse("usuario_perfil", kwargs={"pk": bea.pk}))
    assert {p["titulo"] for p in response.data["pools_en_comun"]} == {"Compartido"}


def test_DW_1_3_sin_pools_en_comun_lista_vacia(api_client, db):
    ana = _usuario("ana@example.com", "ana", "30000001")
    bea = _usuario("bea@example.com", "bea", "30000002")

    authenticate(api_client, bea)
    response = api_client.get(reverse("usuario_perfil", kwargs={"pk": ana.pk}))
    assert response.status_code == 200
    assert response.data["pools_en_comun"] == []


def test_DW_1_3_anonimo_sin_pools_en_comun_y_sin_pii(api_client, db):
    ana = _usuario("ana@example.com", "ana", "30000001")

    response = api_client.get(reverse("usuario_perfil", kwargs={"pk": ana.pk}))
    assert response.status_code == 200
    assert response.data["pools_en_comun"] == []
    assert response.data["antiguedad"] == ana.date_joined.date().isoformat()
    for pii in ("telefono", "email", "dni", "first_name", "last_name"):
        assert pii not in response.data
