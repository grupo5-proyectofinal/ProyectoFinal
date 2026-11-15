"""Baja de un integrante que ya pagó, con devolución coordinada fuera de la app."""
# ruff: noqa: F811 — los fixtures importados de tests.py se reciben como parámetros

import pytest
from django.urls import reverse

from .models import EventoPool, Membership, Pool, SolicitudBaja
from .tests import (  # noqa: F401 — fixtures compartidos
    TELEFONO,
    api_client,
    autenticar,
    categoria,
    crear_pool,
    otro,
    poner_estado,
    pool,
    user,
)


@pytest.fixture
def con_pago(pool, otro):
    """Pool listo con `otro` (3 u. a $100) con el pago enviado."""
    Membership.objects.create(
        pool=pool,
        usuario=otro,
        cantidad=3,
        telefono=TELEFONO,
        pago_estado=Membership.PagoEstado.ENVIADO,
    )
    return poner_estado(pool, Pool.Estado.LISTO)


def pedir(api_client, pool, motivo="Ya no me sirve"):
    return api_client.post(reverse("pool-bajas", args=[pool.id]), {"motivo": motivo}, format="json")


def resolver(api_client, pool, solicitud, **datos):
    return api_client.post(
        reverse("pool-resolver-baja", args=[pool.id, solicitud.id]), datos, format="json"
    )


def devolucion(api_client, pool, solicitud):
    return api_client.post(reverse("pool-devolucion-baja", args=[pool.id, solicitud.id]))


def baja_pendiente(api_client, pool, otro):
    autenticar(api_client, otro)
    assert pedir(api_client, pool).status_code == 201
    return SolicitudBaja.objects.get(pool=pool, usuario=otro)


def test_pedir_baja_guarda_monto_y_avisa_al_creador(api_client, con_pago, user, otro):
    autenticar(api_client, otro)
    response = pedir(api_client, con_pago)
    assert response.status_code == 201
    assert response.data["estado"] == "pendiente"
    assert response.data["monto"] == "300.00"
    assert con_pago.eventos.filter(tipo=EventoPool.Tipo.BAJA_SOLICITADA).exists()
    assert user.notificaciones.filter(pool=con_pago, titulo__contains="pidió la baja").exists()
    # Sigue en el pool hasta que el administrador responda.
    assert con_pago.memberships.filter(usuario=otro).exists()


def test_pedir_baja_sin_pago_se_deriva_a_salir(api_client, pool, otro):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3, telefono=TELEFONO)
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, otro)
    response = pedir(api_client, pool)
    assert response.status_code == 400
    assert "salir del pool" in str(response.data)


def test_pedir_baja_requiere_motivo(api_client, con_pago, otro):
    autenticar(api_client, otro)
    assert "motivo" in pedir(api_client, con_pago, motivo="   ").data


def test_pedir_baja_solo_con_pool_listo_o_en_curso(api_client, con_pago, otro):
    poner_estado(con_pago, Pool.Estado.FINALIZADO)
    autenticar(api_client, otro)
    assert pedir(api_client, con_pago).status_code == 400


def test_pedir_baja_no_duplica_pendiente(api_client, con_pago, otro):
    autenticar(api_client, otro)
    pedir(api_client, con_pago)
    assert pedir(api_client, con_pago).status_code == 400


def test_pedir_baja_solo_integrantes(api_client, con_pago, user):
    autenticar(api_client, user)
    assert pedir(api_client, con_pago).status_code == 403


def test_aprobar_saca_al_integrante_y_libera_el_cupo(api_client, con_pago, user, otro):
    solicitud = baja_pendiente(api_client, con_pago, otro)
    autenticar(api_client, user)
    response = resolver(api_client, con_pago, solicitud, accion="aprobar")
    assert response.status_code == 200
    assert response.data["estado"] == "aprobada"
    con_pago.refresh_from_db()
    assert not con_pago.memberships.exists()
    # Con cupo libre, el pool listo vuelve a abierto.
    assert con_pago.estado == Pool.Estado.ABIERTO
    assert con_pago.eventos.filter(tipo=EventoPool.Tipo.BAJA_APROBADA).exists()
    assert con_pago.eventos.filter(tipo=EventoPool.Tipo.SALIDA, datos__motivo="baja").exists()
    assert otro.notificaciones.filter(pool=con_pago, titulo__contains="aprobada").exists()


def test_aprobar_en_curso_mantiene_el_estado(api_client, con_pago, user, otro):
    poner_estado(con_pago, Pool.Estado.EN_CURSO)
    solicitud = baja_pendiente(api_client, con_pago, otro)
    autenticar(api_client, user)
    resolver(api_client, con_pago, solicitud, accion="aprobar")
    con_pago.refresh_from_db()
    assert con_pago.estado == Pool.Estado.EN_CURSO


def test_rechazar_pide_motivo_y_deja_al_integrante(api_client, con_pago, user, otro):
    solicitud = baja_pendiente(api_client, con_pago, otro)
    autenticar(api_client, user)
    sin_motivo = resolver(api_client, con_pago, solicitud, accion="rechazar")
    assert "motivo" in sin_motivo.data
    response = resolver(api_client, con_pago, solicitud, accion="rechazar", motivo="Ya compré")
    assert response.status_code == 200
    assert response.data["estado"] == "rechazada"
    assert response.data["motivo_rechazo"] == "Ya compré"
    assert con_pago.memberships.filter(usuario=otro).exists()
    # Después de un rechazo puede volver a pedirla.
    autenticar(api_client, otro)
    assert pedir(api_client, con_pago, motivo="Otra vez").status_code == 201


def test_resolver_solo_el_creador_y_solo_una_vez(api_client, con_pago, user, otro):
    solicitud = baja_pendiente(api_client, con_pago, otro)
    assert resolver(api_client, con_pago, solicitud, accion="aprobar").status_code == 403
    autenticar(api_client, user)
    assert resolver(api_client, con_pago, solicitud, accion="aprobar").status_code == 200
    assert resolver(api_client, con_pago, solicitud, accion="aprobar").status_code == 400


def test_devolucion_se_marca_y_se_confirma_en_orden(api_client, con_pago, user, otro):
    solicitud = baja_pendiente(api_client, con_pago, otro)
    autenticar(api_client, user)
    resolver(api_client, con_pago, solicitud, accion="aprobar")

    # El integrante no puede confirmar antes de que el administrador marque.
    autenticar(api_client, otro)
    assert devolucion(api_client, con_pago, solicitud).status_code == 400

    autenticar(api_client, user)
    hecha = devolucion(api_client, con_pago, solicitud)
    assert hecha.status_code == 200
    assert hecha.data["estado"] == "devuelta"
    assert otro.notificaciones.filter(pool=con_pago, titulo__contains="devolución").exists()
    # El administrador no puede marcarla dos veces.
    assert devolucion(api_client, con_pago, solicitud).status_code == 400

    autenticar(api_client, otro)
    recibida = devolucion(api_client, con_pago, solicitud)
    assert recibida.status_code == 200
    assert recibida.data["estado"] == "confirmada"
    assert user.notificaciones.filter(pool=con_pago, titulo__contains="confirmó").exists()


def test_devolucion_ajenos_403(api_client, con_pago, user, otro):
    solicitud = baja_pendiente(api_client, con_pago, otro)
    autenticar(api_client, user)
    resolver(api_client, con_pago, solicitud, accion="aprobar")
    tercero = otro.__class__.objects.create_user(
        email="t@example.com", username="t", dni="10000009", password="Zq7!mN2pLxD"
    )
    autenticar(api_client, tercero)
    assert devolucion(api_client, con_pago, solicitud).status_code == 403


def test_listar_bajas_creador_ve_todas_y_cada_uno_las_propias(api_client, con_pago, user, otro):
    baja_pendiente(api_client, con_pago, otro)
    url = reverse("pool-bajas", args=[con_pago.id])
    autenticar(api_client, user)
    assert len(api_client.get(url).data["results"]) == 1
    autenticar(api_client, otro)
    assert len(api_client.get(url).data["results"]) == 1
    tercero = otro.__class__.objects.create_user(
        email="t@example.com", username="t", dni="10000009", password="Zq7!mN2pLxD"
    )
    autenticar(api_client, tercero)
    assert api_client.get(url).data["results"] == []


def test_el_ex_integrante_sigue_viendo_su_solicitud_tras_salir(api_client, con_pago, user, otro):
    solicitud = baja_pendiente(api_client, con_pago, otro)
    autenticar(api_client, user)
    resolver(api_client, con_pago, solicitud, accion="aprobar")
    autenticar(api_client, otro)
    data = api_client.get(reverse("pool-bajas", args=[con_pago.id])).data["results"]
    assert [b["estado"] for b in data] == ["aprobada"]
