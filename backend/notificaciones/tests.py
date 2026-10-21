from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from pools import views as pool_views
from pools.models import Category, Membership, Pool, expirar_vencidos

from . import correo
from .models import Notificacion

User = get_user_model()

PASSWORD = "Zq7!mN2pLxD"
TELEFONO = "3515551234"


@pytest.fixture(autouse=True)
def geocodificacion_sin_red(monkeypatch):
    monkeypatch.setattr(pool_views, "geocodificar", lambda direccion, ciudad: None)


@pytest.fixture
def api_client():
    return APIClient()


def crear_usuario(n, **overrides):
    datos = {
        "email": f"u{n}@example.com",
        "username": f"u{n}",
        "dni": f"2000000{n}",
        "password": PASSWORD,
    }
    datos.update(overrides)
    return User.objects.create_user(**datos)


@pytest.fixture
def creador(db):
    return crear_usuario(1, first_name="Ana", last_name="Paz")


@pytest.fixture
def miembro(db):
    return crear_usuario(2, first_name="Beto")


@pytest.fixture
def categoria(db):
    return Category.objects.create(nombre="Prueba")


def crear_pool(creador, categoria, **overrides):
    datos = {
        "creador": creador,
        "categoria": categoria,
        "titulo": "Yerba",
        "nombre_producto": "Yerba 1kg",
        "precio_unitario": "100.00",
        "cantidad_total": 10,
        "cantidad_creador": 2,
        "fecha_caducidad": timezone.localdate() + timedelta(days=7),
        "direccion": "Calle 1",
        "ciudad": "Cordoba",
    }
    datos.update(overrides)
    return Pool.objects.create(**datos)


@pytest.fixture
def pool(creador, categoria):
    return crear_pool(creador, categoria)


def unirse(api_client, usuario, pool, cantidad=1):
    api_client.force_authenticate(usuario)
    return api_client.post(
        reverse("pool-unirse", kwargs={"pk": pool.pk}),
        {"cantidad": cantidad, "telefono": TELEFONO},
        format="json",
    )


def de(usuario, **filtros):
    return Notificacion.objects.filter(usuario=usuario, **filtros)


# --- Altas por evento ---


def test_unirse_avisa_al_creador(api_client, creador, miembro, pool):
    assert unirse(api_client, miembro, pool, 3).status_code == 201

    aviso = de(creador, tipo="union").get()
    assert aviso.titulo == "Beto se unió a tu pool"
    assert "3 unidades" in aviso.texto
    assert aviso.pool == pool
    assert not de(miembro).exists()


def test_unirse_sin_preferencia_de_miembros_no_avisa(api_client, creador, miembro, pool):
    creador.notificar_miembros = False
    creador.save()

    unirse(api_client, miembro, pool)

    assert not de(creador, tipo="union").exists()


def test_completar_cupo_avisa_listo_a_todos_menos_al_actor(
    api_client, creador, miembro, categoria
):
    pool = crear_pool(creador, categoria, cantidad_total=5, cantidad_creador=2)
    otro = crear_usuario(3)
    unirse(api_client, otro, pool, 1)

    assert unirse(api_client, miembro, pool, 2).status_code == 201

    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.LISTO
    assert de(creador, tipo="estado", datos__estado="listo").count() == 1
    assert de(otro, tipo="estado", datos__estado="listo").count() == 1
    assert not de(miembro, tipo="estado").exists()


def test_transicion_avisa_a_los_miembros(api_client, creador, miembro, pool):
    Membership.objects.create(pool=pool, usuario=miembro, cantidad=8, telefono=TELEFONO)
    pool.estado = Pool.Estado.LISTO
    pool.save()
    api_client.force_authenticate(creador)

    response = api_client.post(reverse("pool-confirmar", kwargs={"pk": pool.pk}))

    assert response.status_code == 200
    aviso = de(miembro, tipo="estado").get()
    assert aviso.titulo == "Pedido confirmado en Yerba"
    assert aviso.datos == {"estado": "en_curso"}
    assert not de(creador, tipo="estado").exists()


def test_sin_preferencia_de_estados_no_avisa(api_client, creador, miembro, pool):
    miembro.notificar_estados = False
    miembro.save()
    Membership.objects.create(pool=pool, usuario=miembro, cantidad=8, telefono=TELEFONO)
    pool.estado = Pool.Estado.LISTO
    pool.save()
    api_client.force_authenticate(creador)

    api_client.post(reverse("pool-confirmar", kwargs={"pk": pool.pk}))

    assert not de(miembro).exists()


def test_expiracion_avisa_a_todos(creador, miembro, pool):
    Membership.objects.create(pool=pool, usuario=miembro, cantidad=1, telefono=TELEFONO)
    Pool.objects.filter(pk=pool.pk).update(
        fecha_caducidad=timezone.localdate() - timedelta(days=1)
    )

    expirar_vencidos()

    for usuario in (creador, miembro):
        aviso = de(usuario, tipo="estado").get()
        assert aviso.titulo == "Yerba fue cancelado"
        assert "plazo" in aviso.texto


def test_mensaje_avisa_a_los_demas_y_agrupa(api_client, creador, miembro, pool):
    Membership.objects.create(pool=pool, usuario=miembro, cantidad=8, telefono=TELEFONO)
    pool.estado = Pool.Estado.LISTO
    pool.save()
    api_client.force_authenticate(creador)
    url = reverse("pool-mensajes", kwargs={"pk": pool.pk})

    api_client.post(url, {"texto": "Hola"}, format="json")
    api_client.post(url, {"texto": "¿Retiramos el sábado?"}, format="json")

    aviso = de(miembro, tipo="mensaje").get()
    assert aviso.cantidad == 2
    assert aviso.titulo == "2 mensajes nuevos en Yerba"
    assert aviso.texto == "Ana Paz: ¿Retiramos el sábado?"
    assert not de(creador, tipo="mensaje").exists()


def test_mensaje_despues_de_leer_crea_otro_aviso(api_client, creador, miembro, pool):
    Membership.objects.create(pool=pool, usuario=miembro, cantidad=8, telefono=TELEFONO)
    pool.estado = Pool.Estado.LISTO
    pool.save()
    api_client.force_authenticate(creador)
    url = reverse("pool-mensajes", kwargs={"pk": pool.pk})

    api_client.post(url, {"texto": "Hola"}, format="json")
    de(miembro).update(leida=True)
    api_client.post(url, {"texto": "Otra"}, format="json")

    assert de(miembro, tipo="mensaje").count() == 2


def mails_a(usuario):
    return [m for m in mail.outbox if m.to == [usuario.email]]


def test_mail_de_notificacion_con_html_y_baja(
    api_client, creador, miembro, pool, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        unirse(api_client, miembro, pool)

    (aviso,) = mails_a(creador)
    assert aviso.subject == "PoolShop: Beto se unió a tu pool"
    assert f"/pools/{pool.pk}" in aviso.body
    html, tipo = aviso.alternatives[0]
    assert tipo == "text/html"
    assert "Beto se unió a tu pool" in html
    assert "/baja-emails?token=" in html
    assert aviso.extra_headers["List-Unsubscribe"].startswith("<http")


def test_union_manda_confirmacion_al_que_se_unio(
    api_client, creador, miembro, pool, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        unirse(api_client, miembro, pool, 3)

    (confirmacion,) = mails_a(miembro)
    assert confirmacion.subject == "Te uniste a Yerba"
    assert "3 unidades" in confirmacion.body
    assert "$ 300" in confirmacion.body
    assert "/baja-emails?token=" in confirmacion.body


def test_las_notificaciones_por_mail_vienen_activadas(db):
    assert crear_usuario(7).notificar_por_email is True


def test_sin_preferencia_de_mail_no_envia(
    api_client, creador, miembro, pool, django_capture_on_commit_callbacks
):
    for usuario in (creador, miembro):
        usuario.notificar_por_email = False
        usuario.save()

    with django_capture_on_commit_callbacks(execute=True):
        unirse(api_client, miembro, pool)

    assert mail.outbox == []
    assert de(creador).exists()


def test_tipo_desactivado_tampoco_manda_mail(
    api_client, creador, miembro, pool, django_capture_on_commit_callbacks
):
    creador.notificar_miembros = False
    creador.save()

    with django_capture_on_commit_callbacks(execute=True):
        unirse(api_client, miembro, pool)

    assert mails_a(creador) == []


def test_smtp_caido_no_tumba_la_accion(
    api_client, creador, miembro, pool, django_capture_on_commit_callbacks
):
    with (
        patch("notificaciones.correo.mail.mailers") as mailers,
        django_capture_on_commit_callbacks(execute=True),
    ):
        mailers.default.send_messages.side_effect = ConnectionRefusedError("down")
        response = unirse(api_client, miembro, pool)

    assert response.status_code == 201
    mailers.default.send_messages.assert_called()


# --- Baja de correos desde el link ---


def test_baja_desde_el_link_sin_sesion(api_client, creador):
    token = parse_qs(urlsplit(correo.enlace_baja(creador)).query)["token"][0]

    response = api_client.post(reverse("baja_emails"), {"token": token}, format="json")

    assert response.status_code == 200
    creador.refresh_from_db()
    assert creador.notificar_por_email is False


def test_baja_con_token_adulterado_400(api_client, creador):
    token = parse_qs(urlsplit(correo.enlace_baja(creador)).query)["token"][0]

    response = api_client.post(reverse("baja_emails"), {"token": token + "x"}, format="json")

    assert response.status_code == 400
    creador.refresh_from_db()
    assert creador.notificar_por_email is True


# --- API de la bandeja ---


def test_lista_solo_las_propias(api_client, creador, miembro, pool):
    Notificacion.objects.create(usuario=creador, tipo="estado", pool=pool, titulo="Mía")
    Notificacion.objects.create(usuario=miembro, tipo="estado", pool=pool, titulo="Ajena")
    api_client.force_authenticate(creador)

    response = api_client.get(reverse("notificacion-list"))

    assert response.status_code == 200
    assert [n["titulo"] for n in response.data["results"]] == ["Mía"]
    assert response.data["results"][0]["pool_titulo"] == "Yerba"


def test_requiere_sesion(api_client, db):
    assert api_client.get(reverse("notificacion-list")).status_code == 401
    assert api_client.get(reverse("notificacion-resumen")).status_code == 401


def test_filtra_no_leidas_y_resume(api_client, creador, pool):
    Notificacion.objects.create(usuario=creador, tipo="estado", pool=pool, titulo="Nueva")
    Notificacion.objects.create(
        usuario=creador, tipo="estado", pool=pool, titulo="Vieja", leida=True
    )
    api_client.force_authenticate(creador)

    response = api_client.get(reverse("notificacion-list"), {"leida": "false"})
    resumen = api_client.get(reverse("notificacion-resumen"))

    assert [n["titulo"] for n in response.data["results"]] == ["Nueva"]
    assert resumen.data == {"no_leidas": 1}


def test_leer_una_y_todas(api_client, creador, miembro, pool):
    una = Notificacion.objects.create(usuario=creador, tipo="estado", pool=pool, titulo="1")
    Notificacion.objects.create(usuario=creador, tipo="estado", pool=pool, titulo="2")
    ajena = Notificacion.objects.create(usuario=miembro, tipo="estado", pool=pool, titulo="3")
    api_client.force_authenticate(creador)

    response = api_client.post(reverse("notificacion-leer", kwargs={"pk": una.pk}))
    assert response.status_code == 200
    assert response.data["leida"] is True

    response = api_client.post(reverse("notificacion-leer", kwargs={"pk": ajena.pk}))
    assert response.status_code == 404

    response = api_client.post(reverse("notificacion-leer-todas"))
    assert response.data == {"marcadas": 1}
    assert not de(creador, leida=False).exists()
    assert de(miembro, leida=False).exists()


def test_preferencias_se_editan_en_me(api_client, creador):
    api_client.force_authenticate(creador)

    response = api_client.patch(
        reverse("me"),
        {"notificar_mensajes": False, "notificar_por_email": True},
        format="json",
    )

    assert response.status_code == 200
    creador.refresh_from_db()
    assert creador.notificar_mensajes is False
    assert creador.notificar_por_email is True
    perfil = api_client.get(reverse("me")).data
    assert perfil["notificar_estados"] is True
    assert perfil["notificar_mensajes"] is False


def test_titulos_largos_se_recortan_sin_romper_la_accion(api_client, categoria, miembro):
    largo = crear_usuario(5, first_name="N" * 120, last_name="A" * 120)
    pool = crear_pool(largo, categoria, titulo="T" * 200)
    Membership.objects.create(pool=pool, usuario=miembro, cantidad=8, telefono=TELEFONO)
    pool.estado = Pool.Estado.LISTO
    pool.save()
    api_client.force_authenticate(largo)
    url = reverse("pool-mensajes", kwargs={"pk": pool.pk})

    assert api_client.post(url, {"texto": "Hola"}, format="json").status_code == 201
    assert api_client.post(url, {"texto": "Otra"}, format="json").status_code == 201

    aviso = de(miembro, tipo="mensaje").get()
    assert aviso.cantidad == 2
    assert len(aviso.titulo) <= 255


def test_union_con_nombre_largo_no_rompe(api_client, creador, categoria):
    pool = crear_pool(creador, categoria, titulo="T" * 200)
    largo = crear_usuario(6, first_name="N" * 150, last_name="A" * 150)

    assert unirse(api_client, largo, pool).status_code == 201
    assert len(de(creador, tipo="union").get().titulo) <= 255
