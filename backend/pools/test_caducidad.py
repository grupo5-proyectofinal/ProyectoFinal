"""Caducidad con participantes, extensión del plazo y reconfirmación."""
# ruff: noqa: F811 — los fixtures importados de tests.py se reciben como parámetros

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from .models import EventoPool, Membership, Pool, expirar_vencidos
from .tests import (  # noqa: F401 — fixtures compartidos
    TELEFONO,
    api_client,
    autenticar,
    categoria,
    crear_pool,
    otro,
    pool,
    user,
)


def pool_caducado(user, categoria, otro, **overrides):
    """Pool de `user` con un miembro (`otro`), vencido ayer y ya caducado."""
    overrides.setdefault("fecha_caducidad", timezone.localdate() - timedelta(days=1))
    pool = crear_pool(user, categoria, **overrides)
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3, telefono=TELEFONO)
    expirar_vencidos()
    pool.refresh_from_db()
    return pool


def fecha_valida(dias=10):
    return (timezone.localdate() + timedelta(days=dias)).isoformat()


def extender(api_client, pool, dias=10):
    return api_client.post(
        reverse("pool-extender", args=[pool.id]),
        {"fecha_caducidad": fecha_valida(dias)},
        format="json",
    )


def test_vencido_con_participantes_pasa_a_caducado(user, otro, categoria):
    pool = pool_caducado(user, categoria, otro)
    assert pool.estado == Pool.Estado.CADUCADO
    assert pool.eventos.filter(tipo=EventoPool.Tipo.EXPIRADO).exists()


def test_vencido_sin_participantes_se_cancela(user, categoria):
    pool = crear_pool(
        user, categoria, fecha_caducidad=timezone.localdate() - timedelta(days=1)
    )
    expirar_vencidos()
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.CANCELADO


def test_caducado_no_permite_comprobante_ni_chat(api_client, user, otro, categoria):
    pool = pool_caducado(user, categoria, otro)
    autenticar(api_client, otro)
    comprobante = api_client.post(
        reverse("pool-comprobante", args=[pool.id]), {}, format="multipart"
    )
    chat = api_client.post(
        reverse("pool-mensajes", args=[pool.id]), {"texto": "Hola"}, format="json"
    )
    assert comprobante.status_code == 400
    assert chat.status_code == 400


def test_extender_pasa_a_reconfirmacion_y_avisa(api_client, user, otro, categoria):
    pool = pool_caducado(user, categoria, otro)
    autenticar(api_client, user)
    response = extender(api_client, pool)
    assert response.status_code == 200
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.RECONFIRMACION
    assert pool.fecha_caducidad == timezone.localdate() + timedelta(days=10)
    assert pool.reconfirmacion_hasta is not None
    assert pool.eventos.filter(tipo=EventoPool.Tipo.EXTENDIDO).exists()
    assert otro.notificaciones.filter(pool=pool, titulo__contains="¿seguís").exists()


def test_extender_solo_el_creador(api_client, user, otro, categoria):
    pool = pool_caducado(user, categoria, otro)
    autenticar(api_client, otro)
    assert extender(api_client, pool).status_code == 403


def test_extender_solo_caducado(api_client, user, categoria):
    pool = crear_pool(user, categoria)
    autenticar(api_client, user)
    assert extender(api_client, pool).status_code == 400


def test_extender_rechaza_fechas_que_no_dejan_tiempo_o_superan_30_dias(
    api_client, user, otro, categoria
):
    pool = pool_caducado(user, categoria, otro)
    autenticar(api_client, user)
    pronto = extender(api_client, pool, dias=2)
    lejos = extender(api_client, pool, dias=31)
    assert "fecha_caducidad" in pronto.data
    assert "fecha_caducidad" in lejos.data
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.CADUCADO


def test_reconfirmar_seguir_cierra_y_reabre(api_client, user, otro, categoria):
    pool = pool_caducado(user, categoria, otro)
    autenticar(api_client, user)
    extender(api_client, pool)
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-reconfirmar", args=[pool.id]), {"seguir": True}, format="json"
    )
    assert response.status_code == 200
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.ABIERTO
    assert pool.reconfirmacion_hasta is None
    assert pool.memberships.filter(usuario=otro).exists()


def test_reconfirmar_salir_libera_el_cupo(api_client, user, otro, categoria):
    pool = pool_caducado(user, categoria, otro)
    autenticar(api_client, user)
    extender(api_client, pool)
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-reconfirmar", args=[pool.id]), {"seguir": False}, format="json"
    )
    assert response.status_code == 200
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.ABIERTO
    assert not pool.memberships.exists()
    assert pool.eventos.filter(tipo=EventoPool.Tipo.SALIDA, actor=otro).exists()


def test_reconfirmar_espera_a_todos_y_no_acepta_doble_respuesta(
    api_client, user, otro, categoria
):
    pool = pool_caducado(user, categoria, otro)
    tercero = otro.__class__.objects.create_user(
        email="c@example.com", username="c", dni="10000003", password="Zq7!mN2pLxD"
    )
    Membership.objects.create(pool=pool, usuario=tercero, cantidad=1, telefono=TELEFONO)
    autenticar(api_client, user)
    extender(api_client, pool)
    autenticar(api_client, otro)
    url = reverse("pool-reconfirmar", args=[pool.id])
    api_client.post(url, {"seguir": True}, format="json")
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.RECONFIRMACION
    assert api_client.post(url, {"seguir": True}, format="json").status_code == 400


def test_reconfirmar_solo_participantes_y_en_reconfirmacion(
    api_client, user, otro, categoria
):
    pool = pool_caducado(user, categoria, otro)
    url = reverse("pool-reconfirmar", args=[pool.id])
    autenticar(api_client, otro)
    # Todavía caducado: nadie tiene que responder.
    assert api_client.post(url, {"seguir": True}, format="json").status_code == 400
    autenticar(api_client, user)
    extender(api_client, pool)
    # El creador no es un participante que reconfirma.
    assert api_client.post(url, {"seguir": True}, format="json").status_code == 403


def test_plazo_cumplido_saca_a_quien_no_respondio(user, otro, categoria):
    pool = pool_caducado(user, categoria, otro)
    Pool.objects.filter(pk=pool.pk).update(
        estado=Pool.Estado.RECONFIRMACION,
        reconfirmacion_hasta=timezone.now() - timedelta(minutes=1),
        fecha_caducidad=timezone.localdate() + timedelta(days=10),
    )
    expirar_vencidos()
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.ABIERTO
    assert not pool.memberships.exists()
    assert pool.eventos.filter(
        tipo=EventoPool.Tipo.SALIDA, datos__motivo="sin_respuesta"
    ).exists()


def test_reconfirmacion_completa_el_cupo_deja_listo(api_client, user, otro, categoria):
    pool = pool_caducado(user, categoria, otro, cantidad_total=5, cantidad_creador=2)
    # 2 del creador + 3 del miembro = cupo completo.
    autenticar(api_client, user)
    extender(api_client, pool)
    autenticar(api_client, otro)
    api_client.post(
        reverse("pool-reconfirmar", args=[pool.id]), {"seguir": True}, format="json"
    )
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.LISTO


def test_cancelar_desde_caducado(api_client, user, otro, categoria):
    pool = pool_caducado(user, categoria, otro)
    autenticar(api_client, user)
    assert api_client.post(reverse("pool-cancelar", args=[pool.id])).status_code == 200
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.CANCELADO


def test_miembro_ve_su_reconfirmacion_en_el_detalle(api_client, user, otro, categoria):
    pool = pool_caducado(user, categoria, otro)
    autenticar(api_client, user)
    extender(api_client, pool)
    autenticar(api_client, otro)
    data = api_client.get(reverse("pool-detail", args=[pool.id])).data
    assert data["estado"] == "reconfirmacion"
    assert data["reconfirmacion_hasta"] is not None
    assert [m["reconfirmado"] for m in data["miembros"]] == [None]
