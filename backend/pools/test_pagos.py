"""Pagos con comprobante y confirmación de recepción del producto."""
# ruff: noqa: F811 — los fixtures importados de tests.py se reciben como parámetros

import importlib

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from .models import EventoPool, Membership, Pool
from .tests import (  # noqa: F401 — fixtures compartidos
    PASSWORD,
    api_client,
    autenticar,
    categoria,
    crear_pool,
    imagen_bytes,
    otro,
    poner_estado,
    pool,
    user,
)

User = get_user_model()

PDF = b"%PDF-1.4\n%fake\n"


@pytest.fixture(autouse=True)
def privado(settings, tmp_path):
    settings.PRIVATE_MEDIA_ROOT = tmp_path / "privado"
    return settings.PRIVATE_MEDIA_ROOT


def nuevo_usuario(n):
    return User.objects.create_user(
        email=f"pago{n}@example.com",
        username=f"pago{n}",
        dni=f"500000{n:02d}",
        password=PASSWORD,
    )


@pytest.fixture
def miembro(db):
    return nuevo_usuario(1)


@pytest.fixture
def listo(pool, miembro):
    """Pool listo con un miembro (pago pendiente)."""
    Membership.objects.create(pool=pool, usuario=miembro, cantidad=3)
    return poner_estado(pool, Pool.Estado.LISTO)


def png(nombre="comprobante.png"):
    return SimpleUploadedFile(nombre, imagen_bytes("PNG"), content_type="image/png")


def subir(api_client, pool, archivo):
    return api_client.post(
        reverse("pool-comprobante", args=[pool.id]), {"comprobante": archivo}, format="multipart"
    )


def membresia(pool, usuario):
    return Membership.objects.get(pool=pool, usuario=usuario)


def revisar(api_client, pool, membership, **datos):
    return api_client.post(
        reverse("pool-revisar-pago", args=[pool.id, membership.id]), datos, format="json"
    )


# --- Subir comprobante -------------------------------------------------------


def test_subir_comprobante_png(api_client, listo, miembro, privado):
    autenticar(api_client, miembro)

    response = subir(api_client, listo, png())

    assert response.status_code == 200
    assert response.data["pago_estado"] == "enviado"
    assert response.data["tiene_comprobante"] is True
    m = membresia(listo, miembro)
    assert m.pago_enviado is not None
    assert (privado / m.comprobante.name).is_file()
    assert EventoPool.objects.filter(pool=listo, tipo="pago_enviado").exists()


def test_subir_comprobante_pdf(api_client, listo, miembro):
    autenticar(api_client, miembro)

    archivo = SimpleUploadedFile("c.pdf", PDF, content_type="application/pdf")
    response = subir(api_client, listo, archivo)

    assert response.status_code == 200


def test_subir_comprobante_invalido(api_client, listo, miembro):
    autenticar(api_client, miembro)

    archivo = SimpleUploadedFile("c.txt", b"hola", content_type="text/plain")
    response = subir(api_client, listo, archivo)

    assert response.status_code == 400
    assert "comprobante" in response.data


def test_subir_comprobante_gif_rechazado(api_client, listo, miembro):
    autenticar(api_client, miembro)

    archivo = SimpleUploadedFile("c.gif", imagen_bytes("GIF"), content_type="image/gif")
    response = subir(api_client, listo, archivo)

    assert response.status_code == 400


def test_subir_comprobante_muy_grande(api_client, listo, miembro):
    autenticar(api_client, miembro)

    archivo = SimpleUploadedFile("c.pdf", PDF + b"0" * (5 * 1024 * 1024), content_type="application/pdf")
    response = subir(api_client, listo, archivo)

    assert response.status_code == 400


def test_subir_comprobante_pool_abierto_400(api_client, pool, miembro):
    Membership.objects.create(pool=pool, usuario=miembro, cantidad=1)
    autenticar(api_client, miembro)

    assert subir(api_client, pool, png()).status_code == 400


def test_subir_comprobante_no_miembro_403(api_client, listo, otro):
    autenticar(api_client, otro)

    assert subir(api_client, listo, png()).status_code == 403


def test_subir_comprobante_creador_403(api_client, listo, user):
    autenticar(api_client, user)

    assert subir(api_client, listo, png()).status_code == 403


def test_subir_comprobante_sin_auth_401(api_client, listo):
    assert subir(api_client, listo, png()).status_code == 401


def test_reemplazar_comprobante_rechazado(api_client, listo, user, miembro, privado):
    autenticar(api_client, miembro)
    subir(api_client, listo, png("uno.png"))
    anterior = membresia(listo, miembro).comprobante.name
    autenticar(api_client, user)
    revisar(api_client, listo, membresia(listo, miembro), accion="rechazar", motivo="Monto mal")

    autenticar(api_client, miembro)
    response = subir(api_client, listo, png("dos.png"))

    assert response.status_code == 200
    m = membresia(listo, miembro)
    assert m.pago_estado == "enviado"
    assert m.pago_motivo_rechazo == ""
    assert m.comprobante.name != anterior


def test_no_reemplaza_pago_confirmado(api_client, listo, user, miembro):
    autenticar(api_client, miembro)
    subir(api_client, listo, png())
    autenticar(api_client, user)
    revisar(api_client, listo, membresia(listo, miembro), accion="confirmar")

    autenticar(api_client, miembro)
    assert subir(api_client, listo, png()).status_code == 400


# --- Ver comprobante ---------------------------------------------------------


def test_ver_comprobante_creador_y_dueno(api_client, listo, user, miembro):
    autenticar(api_client, miembro)
    subir(api_client, listo, png())
    m = membresia(listo, miembro)
    url = reverse("pool-ver-comprobante", args=[listo.id, m.id])

    for quien in (user, miembro):
        autenticar(api_client, quien)
        response = api_client.get(url)
        assert response.status_code == 200
        assert b"".join(response.streaming_content) == imagen_bytes("PNG")


def test_ver_comprobante_tercero_403(api_client, listo, miembro, otro):
    autenticar(api_client, miembro)
    subir(api_client, listo, png())
    m = membresia(listo, miembro)

    autenticar(api_client, otro)
    response = api_client.get(reverse("pool-ver-comprobante", args=[listo.id, m.id]))

    assert response.status_code == 403


def test_ver_comprobante_sin_auth_401(api_client, listo, miembro):
    m = membresia(listo, miembro)

    response = api_client.get(reverse("pool-ver-comprobante", args=[listo.id, m.id]))

    assert response.status_code == 401


def test_ver_comprobante_inexistente_404(api_client, listo, user, miembro):
    autenticar(api_client, user)
    m = membresia(listo, miembro)

    response = api_client.get(reverse("pool-ver-comprobante", args=[listo.id, m.id]))

    assert response.status_code == 404


# --- Revisar pago ------------------------------------------------------------


def test_creador_confirma_pago(api_client, listo, user, miembro):
    autenticar(api_client, miembro)
    subir(api_client, listo, png())

    autenticar(api_client, user)
    response = revisar(api_client, listo, membresia(listo, miembro), accion="confirmar")

    assert response.status_code == 200
    assert response.data["pago_estado"] == "confirmado"
    evento = EventoPool.objects.get(pool=listo, tipo="pago_confirmado")
    assert evento.datos == {"usuario": miembro.username}


def test_creador_rechaza_con_motivo(api_client, listo, user, miembro):
    autenticar(api_client, miembro)
    subir(api_client, listo, png())

    autenticar(api_client, user)
    response = revisar(
        api_client, listo, membresia(listo, miembro), accion="rechazar", motivo="  Falta $100  "
    )

    assert response.status_code == 200
    m = membresia(listo, miembro)
    assert m.pago_estado == "rechazado"
    assert m.pago_motivo_rechazo == "Falta $100"
    evento = EventoPool.objects.get(pool=listo, tipo="pago_rechazado")
    assert "Falta" not in str(evento.datos)


def test_rechazo_sin_motivo_400(api_client, listo, user, miembro):
    autenticar(api_client, miembro)
    subir(api_client, listo, png())

    autenticar(api_client, user)
    response = revisar(api_client, listo, membresia(listo, miembro), accion="rechazar")

    assert response.status_code == 400
    assert "motivo" in response.data


def test_revisar_sin_comprobante_400(api_client, listo, user, miembro):
    autenticar(api_client, user)

    response = revisar(api_client, listo, membresia(listo, miembro), accion="confirmar")

    assert response.status_code == 400


def test_solo_creador_revisa(api_client, listo, miembro):
    autenticar(api_client, miembro)
    subir(api_client, listo, png())

    response = revisar(api_client, listo, membresia(listo, miembro), accion="confirmar")

    assert response.status_code == 403


# --- Visibilidad -------------------------------------------------------------


def test_visibilidad_de_datos_de_pago(api_client, listo, user, miembro):
    tercero = nuevo_usuario(2)
    Membership.objects.create(pool=listo, usuario=tercero, cantidad=1)
    autenticar(api_client, miembro)
    subir(api_client, listo, png())
    autenticar(api_client, user)
    revisar(api_client, listo, membresia(listo, miembro), accion="rechazar", motivo="Ilegible")
    url = reverse("pool-detail", args=[listo.id])

    def fila(quien):
        autenticar(api_client, quien)
        miembros = api_client.get(url).data["miembros"]
        return next(m for m in miembros if m["usuario"]["id"] == miembro.id)

    del_creador = fila(user)
    assert del_creador["pago_motivo_rechazo"] == "Ilegible"
    assert del_creador["tiene_comprobante"] is True
    assert del_creador["monto"] == "300.00"

    del_dueno = fila(miembro)
    assert del_dueno["pago_motivo_rechazo"] == "Ilegible"
    assert "telefono" not in del_dueno

    del_tercero = fila(tercero)
    assert del_tercero["pago_estado"] == "rechazado"
    assert "pago_motivo_rechazo" not in del_tercero
    assert "tiene_comprobante" not in del_tercero


def test_listado_no_expone_pagos(api_client, listo, user):
    autenticar(api_client, user)

    resultados = api_client.get(reverse("pool-list")).data["results"]

    miembro = resultados[0]["miembros"][0]
    assert "pago_estado" not in miembro
    assert "monto" not in miembro


# --- Transiciones ------------------------------------------------------------


def test_confirmar_pedido_bloqueado_con_pagos_pendientes(api_client, listo, user):
    autenticar(api_client, user)

    response = api_client.post(reverse("pool-confirmar", args=[listo.id]))

    assert response.status_code == 400
    assert "Faltan confirmar 1 pago." in str(response.data)
    listo.refresh_from_db()
    assert listo.estado == Pool.Estado.LISTO


def test_confirmar_pedido_con_todos_los_pagos(api_client, listo, user, miembro):
    autenticar(api_client, miembro)
    subir(api_client, listo, png())
    autenticar(api_client, user)
    revisar(api_client, listo, membresia(listo, miembro), accion="confirmar")

    response = api_client.post(reverse("pool-confirmar", args=[listo.id]))

    assert response.status_code == 200
    assert response.data["estado"] == "en_curso"


def test_recepcion_y_finalizar(api_client, listo, user, miembro):
    membresia(listo, miembro)
    Membership.objects.filter(pool=listo).update(pago_estado="confirmado")
    poner_estado(listo, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)

    bloqueado = api_client.post(reverse("pool-finalizar", args=[listo.id]))
    assert bloqueado.status_code == 400
    assert "por confirmar la recepción" in str(bloqueado.data)

    autenticar(api_client, miembro)
    response = api_client.post(reverse("pool-recepcion", args=[listo.id]))
    assert response.status_code == 200
    assert response.data["recepcion_confirmada"] is not None
    assert EventoPool.objects.filter(pool=listo, tipo="recepcion").exists()

    repetida = api_client.post(reverse("pool-recepcion", args=[listo.id]))
    assert repetida.status_code == 400

    autenticar(api_client, user)
    final = api_client.post(reverse("pool-finalizar", args=[listo.id]))
    assert final.status_code == 200
    assert final.data["estado"] == "finalizado"


def test_recepcion_solo_en_curso(api_client, listo, miembro):
    autenticar(api_client, miembro)

    assert api_client.post(reverse("pool-recepcion", args=[listo.id])).status_code == 400


def test_recepcion_no_miembro_403(api_client, listo, otro):
    poner_estado(listo, Pool.Estado.EN_CURSO)
    autenticar(api_client, otro)

    assert api_client.post(reverse("pool-recepcion", args=[listo.id])).status_code == 403


def test_finalizar_sin_miembros(api_client, user, categoria):
    pool = poner_estado(crear_pool(user, categoria), Pool.Estado.EN_CURSO)
    autenticar(api_client, user)

    assert api_client.post(reverse("pool-finalizar", args=[pool.id])).status_code == 200


# --- Membresía fija tras pagar ----------------------------------------------


def test_no_salir_ni_cambiar_cantidad_tras_pagar(api_client, listo, miembro):
    autenticar(api_client, miembro)
    subir(api_client, listo, png())

    salir = api_client.delete(reverse("pool-salir", args=[listo.id]))
    cambiar = api_client.patch(
        reverse("pool-mi-membresia", args=[listo.id]), {"cantidad": 1}, format="json"
    )

    assert salir.status_code == 400
    assert cambiar.status_code == 400
    assert membresia(listo, miembro).cantidad == 3


def test_salir_con_pago_rechazado(api_client, listo, user, miembro):
    autenticar(api_client, miembro)
    subir(api_client, listo, png())
    autenticar(api_client, user)
    revisar(api_client, listo, membresia(listo, miembro), accion="rechazar", motivo="No")

    autenticar(api_client, miembro)
    assert api_client.delete(reverse("pool-salir", args=[listo.id])).status_code == 204


# --- Sin efectivo y migración de datos ---------------------------------------


def test_efectivo_ya_no_es_tipo_de_pago(api_client, pool, user):
    autenticar(api_client, user)

    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"tipo_pago": "efectivo"}, format="json"
    )

    assert response.status_code == 400
    assert "tipo_pago" in response.data


def test_migracion_pagos(user, categoria, miembro):
    migracion = importlib.import_module("pools.migrations.0009_pagos_recepcion")
    efectivo = crear_pool(user, categoria)
    Pool.objects.filter(pk=efectivo.pk).update(tipo_pago="efectivo")
    en_curso = poner_estado(crear_pool(user, categoria), Pool.Estado.EN_CURSO)
    finalizado = poner_estado(crear_pool(user, categoria), Pool.Estado.FINALIZADO)
    for p in (efectivo, en_curso, finalizado):
        Membership.objects.create(pool=p, usuario=miembro, cantidad=1)

    migracion.migrar_datos(apps, None)

    efectivo.refresh_from_db()
    assert efectivo.tipo_pago == "transferencia"
    assert membresia(efectivo, miembro).pago_estado == "pendiente"
    assert membresia(en_curso, miembro).pago_estado == "confirmado"
    assert membresia(en_curso, miembro).recepcion_confirmada is None
    assert membresia(finalizado, miembro).recepcion_confirmada is not None
    assert timezone.now() >= membresia(finalizado, miembro).recepcion_confirmada
