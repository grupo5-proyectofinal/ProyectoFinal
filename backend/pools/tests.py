import importlib
import json
import logging
import socket
import urllib.request
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from . import confianza, geocoding, views
from .models import (
    Category,
    EventoPool,
    Membership,
    Mensaje,
    Pool,
    PoolImage,
    SolicitudEliminacion,
    expirar_vencidos,
)

User = get_user_model()

PASSWORD = "Zq7!mN2pLxD"

# Teléfono válido de referencia para los payloads de unirse (la unión ahora lo requiere).
TELEFONO = "3515551234"

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def imagen_bytes(formato):
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "red").save(buffer, format=formato)
    return buffer.getvalue()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="a@example.com", username="a", dni="10000001", password=PASSWORD
    )


@pytest.fixture
def otro(db):
    return User.objects.create_user(
        email="b@example.com", username="b", dni="10000002", password=PASSWORD
    )


@pytest.fixture
def categoria(db):
    return Category.objects.create(nombre="Prueba")


def autenticar(api_client, user):
    api_client.force_authenticate(user)


def payload(categoria, **overrides):
    data = {
        "titulo": "Pool de yerba",
        "nombre_producto": "Yerba 1kg",
        "descripcion": "Compra grupal",
        "categoria": categoria.id,
        "precio_unitario": "1500.00",
        "cantidad_total": 10,
        "cantidad_creador": 2,
        "min_por_integrante": 1,
        "fecha_caducidad": (timezone.localdate() + timedelta(days=7)).isoformat(),
        "tipo_pago": "efectivo",
        "direccion": "Calle 1",
        "ciudad": "Cordoba",
    }
    data.update(overrides)
    return data


def crear_pool(usuario, categoria, **overrides):
    datos = {
        "creador": usuario,
        "categoria": categoria,
        "titulo": "Pool",
        "nombre_producto": "Producto",
        "precio_unitario": "100.00",
        "cantidad_total": 10,
        "cantidad_creador": 2,
        "fecha_caducidad": timezone.localdate() + timedelta(days=7),
        "direccion": "Calle 1",
        "ciudad": "Cordoba",
    }
    datos.update(overrides)
    return Pool.objects.create(**datos)


def poner_estado(pool, estado):
    pool.estado = estado
    pool.save(update_fields=["estado"])
    return pool


@pytest.fixture
def pool(user, categoria):
    return crear_pool(user, categoria)


# --- Categorias ---

MIGRACION_ANTERIOR = "0002_seed_categories"
MIGRACION_CATEGORIAS = "0003_higiene_personal_baja_alimentos"
migracion_categorias = importlib.import_module(f"pools.migrations.{MIGRACION_CATEGORIAS}")


def migrar_pools(destino):
    MigrationExecutor(connections["default"]).migrate([("pools", destino)])


def apps_historicas(destino):
    """Apps en el estado de la migración indicada (sin los campos de la 0004)."""
    return MigrationExecutor(connections["default"]).loader.project_state(
        [("pools", destino)]
    ).apps


def crear_pool_anterior(apps_previas, user, categoria, **overrides):
    """Crea un pool con el modelo histórico de 0002 (sin latitud/longitud)."""
    datos = {
        "creador_id": user.pk,
        "categoria_id": categoria.pk,
        "titulo": "Pool",
        "nombre_producto": "Producto",
        "precio_unitario": "100.00",
        "cantidad_total": 10,
        "cantidad_creador": 2,
        "fecha_caducidad": timezone.localdate() + timedelta(days=7),
        "direccion": "Calle 1",
        "ciudad": "Cordoba",
    }
    datos.update(overrides)
    return apps_previas.get_model("pools", "Pool").objects.create(**datos)


def test_DW_1_1_categorias_incluye_higiene_sin_alimentos(api_client, db):
    response = api_client.get(reverse("category-list"))
    assert response.status_code == 200
    nombres = {c["nombre"] for c in response.data["results"]}
    assert nombres == {"Bebidas", "Limpieza", "Hogar", "Electrónica", "Otros", "Higiene personal"}


def test_DW_1_2_pool_en_alimentos_migra_a_otros(db, user):
    migrar_pools(MIGRACION_ANTERIOR)
    previas = apps_historicas(MIGRACION_ANTERIOR)
    # El reverse de 0003 recrea "Alimentos" y elimina "Higiene personal".
    assert Category.objects.filter(nombre="Alimentos").exists()
    assert not Category.objects.filter(nombre="Higiene personal").exists()

    alimentos = Category.objects.get(nombre="Alimentos")
    abierto = crear_pool_anterior(previas, user, alimentos, titulo="En Alimentos")
    cancelado = crear_pool_anterior(
        previas, user, alimentos, titulo="Cancelado", estado=Pool.Estado.CANCELADO
    )

    migrar_pools(MIGRACION_CATEGORIAS)
    finales = apps_historicas(MIGRACION_CATEGORIAS).get_model("pools", "Pool")

    assert finales.objects.get(pk=abierto.pk).categoria.nombre == "Otros"
    assert finales.objects.get(pk=cancelado.pk).categoria.nombre == "Otros"
    assert finales.objects.get(pk=cancelado.pk).estado == Pool.Estado.CANCELADO
    assert not Category.objects.filter(nombre="Alimentos").exists()
    assert Category.objects.filter(nombre="Higiene personal").exists()


def test_migracion_sin_otros_recrea_categoria(db, user):
    migrar_pools(MIGRACION_ANTERIOR)
    previas = apps_historicas(MIGRACION_ANTERIOR)
    alimentos = Category.objects.get(nombre="Alimentos")
    Category.objects.get(nombre="Otros").delete()
    pool = crear_pool_anterior(previas, user, alimentos)

    migrar_pools(MIGRACION_CATEGORIAS)
    finales = apps_historicas(MIGRACION_CATEGORIAS).get_model("pools", "Pool")

    otros = Category.objects.get(nombre="Otros")
    assert finales.objects.get(pk=pool.pk).categoria_id == otros.pk


def test_migracion_higiene_preexistente_no_duplica(db, user):
    migrar_pools(MIGRACION_ANTERIOR)
    previas = apps_historicas(MIGRACION_ANTERIOR)
    Category.objects.create(nombre="Higiene personal")
    alimentos = Category.objects.get(nombre="Alimentos")
    pool = crear_pool_anterior(previas, user, alimentos)

    migrar_pools(MIGRACION_CATEGORIAS)
    finales = apps_historicas(MIGRACION_CATEGORIAS).get_model("pools", "Pool")

    assert Category.objects.filter(nombre="Higiene personal").count() == 1
    assert finales.objects.get(pk=pool.pk).categoria.nombre == "Otros"


def test_migracion_forward_idempotente(db):
    migracion_categorias.actualizar_categorias(apps, None)
    migracion_categorias.actualizar_categorias(apps, None)

    nombres = set(Category.objects.values_list("nombre", flat=True))
    assert nombres == {"Bebidas", "Limpieza", "Hogar", "Electrónica", "Otros", "Higiene personal"}


def test_migracion_reverse_idempotente(db):
    migracion_categorias.revertir_categorias(apps, None)
    migracion_categorias.revertir_categorias(apps, None)

    assert Category.objects.filter(nombre="Alimentos").count() == 1
    assert not Category.objects.filter(nombre="Higiene personal").exists()


def test_migracion_reverse_conserva_higiene_con_pools(db, user):
    higiene = Category.objects.get(nombre="Higiene personal")
    pool = crear_pool(user, higiene)

    migracion_categorias.revertir_categorias(apps, None)

    assert Category.objects.filter(nombre="Alimentos").exists()
    assert Category.objects.filter(nombre="Higiene personal").exists()
    assert Pool.objects.get(pk=pool.pk).categoria_id == higiene.pk


# --- Creacion y listado ---


def test_crear_pool_requiere_auth(api_client, categoria):
    response = api_client.post(reverse("pool-list"), payload(categoria), format="json")
    assert response.status_code == 401


def test_crear_pool_ok(api_client, user, categoria):
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-list"), payload(categoria), format="json")
    assert response.status_code == 201
    assert response.data["creador"]["id"] == user.id
    assert response.data["estado"] == "abierto"
    assert response.data["disponible"] == 8


def test_crear_pool_cantidad_creador_mayor_total(api_client, user, categoria):
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-list"), payload(categoria, cantidad_creador=11), format="json"
    )
    assert response.status_code == 400
    assert "cantidad_creador" in response.data


def test_crear_pool_fecha_pasada(api_client, user, categoria):
    autenticar(api_client, user)
    ayer = (timezone.localdate() - timedelta(days=1)).isoformat()
    response = api_client.post(
        reverse("pool-list"), payload(categoria, fecha_caducidad=ayer), format="json"
    )
    assert response.status_code == 400
    assert "fecha_caducidad" in response.data


def test_crear_pool_fecha_mas_de_30_dias(api_client, user, categoria):
    autenticar(api_client, user)
    lejos = (timezone.localdate() + timedelta(days=31)).isoformat()
    response = api_client.post(
        reverse("pool-list"), payload(categoria, fecha_caducidad=lejos), format="json"
    )
    assert response.status_code == 400
    assert "fecha_caducidad" in response.data


def test_list_publica_sin_token(api_client, pool):
    response = api_client.get(reverse("pool-list"))
    assert response.status_code == 200
    assert response.data["count"] == 1


def test_list_paginado(api_client, user, categoria):
    for i in range(13):
        crear_pool(user, categoria, titulo=f"Pool {i}")
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"))
    assert response.status_code == 200
    assert response.data["count"] == 13
    assert len(response.data["results"]) == 12


# --- Disponible ---


def test_disponible_resta_miembros(db, user, pool):
    Membership.objects.create(pool=pool, usuario=user, cantidad=3)
    assert pool.disponible == 5


def test_disponible_nunca_negativa(db, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=user, cantidad=20)
    assert pool.disponible == 0


# --- Filtros y ordering ---


def test_filtro_q(api_client, user, categoria):
    crear_pool(user, categoria, titulo="Yerba por mayor")
    crear_pool(user, categoria, titulo="Fideos")
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"), {"q": "yerba"})
    assert response.data["count"] == 1


def test_filtro_categoria(api_client, user, categoria):
    otra = Category.objects.create(nombre="Otra")
    crear_pool(user, categoria)
    crear_pool(user, otra)
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"), {"categoria": otra.id})
    assert response.data["count"] == 1


def test_filtro_precio(api_client, user, categoria):
    crear_pool(user, categoria, precio_unitario="100.00")
    crear_pool(user, categoria, precio_unitario="500.00")
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"), {"precio_min": 200, "precio_max": 600})
    assert response.data["count"] == 1


def test_filtro_ciudad(api_client, user, categoria):
    crear_pool(user, categoria, ciudad="Rosario")
    crear_pool(user, categoria, ciudad="Mendoza")
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"), {"ciudad": "rosar"})
    assert response.data["count"] == 1


def test_filtro_estado(api_client, user, categoria):
    crear_pool(user, categoria)
    poner_estado(crear_pool(user, categoria), Pool.Estado.CANCELADO)
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"), {"estado": "abierto"})
    assert response.data["count"] == 1


def test_ordering_precio(api_client, user, categoria):
    crear_pool(user, categoria, titulo="Caro", precio_unitario="900.00")
    crear_pool(user, categoria, titulo="Barato", precio_unitario="100.00")
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"), {"ordering": "precio_unitario"})
    titulos = [p["titulo"] for p in response.data["results"]]
    assert titulos == ["Barato", "Caro"]


# --- Detalle ---


def test_retrieve_incrementa_vistas(api_client, user, pool):
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.status_code == 200
    pool.refresh_from_db()
    assert pool.vistas == 1


def test_retrieve_devuelve_disponible_y_miembros(api_client, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.data["disponible"] == 5
    assert response.data["miembros"][0]["usuario"]["username"] == otro.username


# --- Edicion y borrado ---


def test_patch_no_creador_403(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"titulo": "Otro"}, format="json"
    )
    assert response.status_code == 403


def test_patch_creador_ok(api_client, user, pool):
    autenticar(api_client, user)
    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"titulo": "Nuevo"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["titulo"] == "Nuevo"


def test_patch_no_abierto_400(api_client, user, pool):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)
    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"titulo": "Nuevo"}, format="json"
    )
    assert response.status_code == 400


def test_patch_inmutable_con_miembros_400(api_client, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    autenticar(api_client, user)
    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"titulo": "Nuevo"}, format="json"
    )
    assert response.status_code == 400
    assert "titulo" in response.data


def test_delete_no_creador_403(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.delete(reverse("pool-detail", args=[pool.id]))
    assert response.status_code == 403


def test_delete_no_abierto_400(api_client, user, pool):
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)
    response = api_client.delete(reverse("pool-detail", args=[pool.id]))
    assert response.status_code == 400


# --- Unirse ---


def test_unirse_ok(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 3, "telefono": TELEFONO}, format="json"
    )
    assert response.status_code == 201
    assert Membership.objects.filter(pool=pool, usuario=otro, cantidad=3).exists()


def test_unirse_baja_disponible(api_client, otro, pool):
    autenticar(api_client, otro)
    api_client.post(reverse("pool-unirse", args=[pool.id]), {"cantidad": 3, "telefono": TELEFONO}, format="json")
    pool.refresh_from_db()
    assert pool.disponible == 5


def test_unirse_sobre_disponible_400(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 9, "telefono": TELEFONO}, format="json"
    )
    assert response.status_code == 400
    assert "cantidad" in response.data


def test_unirse_bajo_minimo_400(api_client, otro, categoria, user):
    pool = crear_pool(user, categoria, min_por_integrante=5)
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 2, "telefono": TELEFONO}, format="json"
    )
    assert response.status_code == 400
    assert "cantidad" in response.data


def test_unirse_creador_400(api_client, user, pool):
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1, "telefono": TELEFONO}, format="json"
    )
    assert response.status_code == 400


def test_unirse_duplicado_400(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1, "telefono": TELEFONO}, format="json"
    )
    assert response.status_code == 400


def test_unirse_no_abierto_400(api_client, otro, pool):
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1, "telefono": TELEFONO}, format="json"
    )
    assert response.status_code == 400


def test_unirse_llena_cambia_a_listo(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 8, "telefono": TELEFONO}, format="json"
    )
    assert response.status_code == 201
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.LISTO


# --- Unión con datos y privacidad por rol (Plan 3, Fase 1) ---


def union_payload(cantidad=3, **overrides):
    data = {"cantidad": cantidad, "telefono": TELEFONO}
    data.update(overrides)
    return data


def test_DW_1_1_unirse_sin_telefono_400(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 3}, format="json"
    )
    assert response.status_code == 400
    assert "telefono" in response.data
    assert not Membership.objects.filter(pool=pool, usuario=otro).exists()


def test_DW_1_1_unirse_telefono_vacio_400(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]),
        union_payload(telefono="   "),
        format="json",
    )
    assert response.status_code == 400
    assert "telefono" in response.data


def test_DW_1_1_unirse_telefono_invalido_400(api_client, otro, pool):
    autenticar(api_client, otro)
    for telefono in ("abc", "12345", "3515551234x"):
        response = api_client.post(
            reverse("pool-unirse", args=[pool.id]),
            union_payload(telefono=telefono),
            format="json",
        )
        assert response.status_code == 400, telefono
        assert "telefono" in response.data


def test_DW_1_1_unirse_guarda_telefono_y_mensaje(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]),
        union_payload(telefono="351 555 1234", mensaje="  Hola, me sumo!  "),
        format="json",
    )
    assert response.status_code == 201
    membership = Membership.objects.get(pool=pool, usuario=otro)
    assert membership.telefono == "351 555 1234"
    assert membership.mensaje == "Hola, me sumo!"


def _crear_miembro_con_datos(pool, usuario, cantidad=1):
    return Membership.objects.create(
        pool=pool, usuario=usuario, cantidad=cantidad, telefono=TELEFONO, mensaje="Me sumo"
    )


def test_DW_1_2_creador_ve_telefono_y_mensaje_en_detalle(api_client, user, otro, pool):
    _crear_miembro_con_datos(pool, otro)
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    miembro = response.data["miembros"][0]
    assert miembro["telefono"] == TELEFONO
    assert miembro["mensaje"] == "Me sumo"


def test_DW_1_2_miembro_no_ve_telefono_y_mensaje(api_client, user, otro, pool):
    _crear_miembro_con_datos(pool, otro)
    autenticar(api_client, otro)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    miembro = response.data["miembros"][0]
    assert "telefono" not in miembro
    assert "mensaje" not in miembro


def test_DW_1_2_otro_integrante_no_ve_pii(api_client, user, otro, pool):
    _crear_miembro_con_datos(pool, otro)
    tercero = User.objects.create_user(
        email="c@example.com", username="c", dni="10000003", password=PASSWORD
    )
    Membership.objects.create(pool=pool, usuario=tercero, cantidad=1)
    autenticar(api_client, tercero)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    for miembro in response.data["miembros"]:
        assert "telefono" not in miembro
        assert "mensaje" not in miembro


def test_DW_1_2_publico_no_ve_telefono_y_mensaje(api_client, user, otro, pool):
    _crear_miembro_con_datos(pool, otro)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.status_code == 200
    miembro = response.data["miembros"][0]
    assert "telefono" not in miembro
    assert "mensaje" not in miembro


def test_DW_1_2_listado_no_expone_telefono_y_mensaje(api_client, user, otro, pool):
    _crear_miembro_con_datos(pool, otro)
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"))
    miembro = response.data["results"][0]["miembros"][0]
    assert "telefono" not in miembro
    assert "mensaje" not in miembro


# --- Salir y editar membresia ---


def test_salir_ok(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, otro)
    response = api_client.delete(reverse("pool-salir", args=[pool.id]))
    assert response.status_code == 204
    pool.refresh_from_db()
    assert pool.disponible == 8


def test_salir_de_listo_vuelve_abierto(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=8)
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, otro)
    response = api_client.delete(reverse("pool-salir", args=[pool.id]))
    assert response.status_code == 204
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.ABIERTO


def test_salir_sin_membresia_400(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.delete(reverse("pool-salir", args=[pool.id]))
    assert response.status_code == 400


def test_mi_membresia_cambia_cantidad(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, otro)
    response = api_client.patch(
        reverse("pool-mi-membresia", args=[pool.id]), {"cantidad": 6}, format="json"
    )
    assert response.status_code == 200
    assert Membership.objects.get(pool=pool, usuario=otro).cantidad == 6
    assert response.data["disponible"] == 2


def test_mi_membresia_sobre_disponible_400(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, otro)
    response = api_client.patch(
        reverse("pool-mi-membresia", args=[pool.id]), {"cantidad": 9}, format="json"
    )
    assert response.status_code == 400
    assert "cantidad" in response.data


# --- Transiciones de estado ---


def test_confirmar_listo_a_en_curso(api_client, user, pool):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-confirmar", args=[pool.id]))
    assert response.status_code == 200
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.EN_CURSO


def test_confirmar_no_creador_403(api_client, otro, pool):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, otro)
    response = api_client.post(reverse("pool-confirmar", args=[pool.id]))
    assert response.status_code == 403


def test_finalizar_en_curso(api_client, user, pool):
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-finalizar", args=[pool.id]))
    assert response.status_code == 200
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.FINALIZADO


def test_cancelar_abierto(api_client, user, pool):
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-cancelar", args=[pool.id]))
    assert response.status_code == 200
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.CANCELADO


def test_cancelar_finalizado_400(api_client, user, pool):
    poner_estado(pool, Pool.Estado.FINALIZADO)
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-cancelar", args=[pool.id]))
    assert response.status_code == 400


# --- Caducidad ---


def crear_pool_vencido(usuario, categoria, **overrides):
    """Pool abierto con la fecha de caducidad de ayer (la validación no corre en el ORM)."""
    overrides.setdefault("fecha_caducidad", timezone.localdate() - timedelta(days=1))
    return crear_pool(usuario, categoria, **overrides)


def test_DW_3_1_lectura_cancela_pool_vencido(api_client, user, categoria):
    pool = crear_pool_vencido(user, categoria)
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-detail", args=[pool.id]))

    assert response.status_code == 200
    assert response.data["estado"] == "cancelado"
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.CANCELADO


def test_lectura_de_listado_cancela_vencidos_y_el_filtro_los_excluye(api_client, user, categoria):
    vencido = crear_pool_vencido(user, categoria, titulo="Vencido")
    vigente = crear_pool(user, categoria, titulo="Vigente")

    response = api_client.get(reverse("pool-list"))

    estados = {p["id"]: p["estado"] for p in response.data["results"]}
    assert estados == {vencido.id: "cancelado", vigente.id: "abierto"}

    response = api_client.get(reverse("pool-list"), {"estado": "abierto"})
    assert [p["id"] for p in response.data["results"]] == [vigente.id]


def test_pool_que_vence_hoy_sigue_vigente(api_client, user, otro, categoria):
    pool = crear_pool(user, categoria, fecha_caducidad=timezone.localdate())
    autenticar(api_client, otro)

    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.data["estado"] == "abierto"

    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1, "telefono": TELEFONO}, format="json"
    )
    assert response.status_code == 201


def test_DW_3_2_unirse_a_vencido_400_sin_consumir_disponible(api_client, user, otro, categoria):
    pool = crear_pool_vencido(user, categoria)
    autenticar(api_client, otro)

    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1, "telefono": TELEFONO}, format="json"
    )

    assert response.status_code == 400
    assert "El pool está vencido." in str(response.data)
    assert not Membership.objects.filter(pool=pool, usuario=otro).exists()
    pool.refresh_from_db()
    assert pool.disponible == 8


def test_salir_de_pool_vencido_400_conserva_membresia(api_client, user, otro, categoria):
    pool = crear_pool_vencido(user, categoria)
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, otro)

    response = api_client.delete(reverse("pool-salir", args=[pool.id]))

    assert response.status_code == 400
    assert "El pool está vencido." in str(response.data)
    assert Membership.objects.filter(pool=pool, usuario=otro).exists()


def test_mi_membresia_en_pool_vencido_400_sin_cambios(api_client, user, otro, categoria):
    pool = crear_pool_vencido(user, categoria)
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, otro)

    response = api_client.patch(
        reverse("pool-mi-membresia", args=[pool.id]), {"cantidad": 6}, format="json"
    )

    assert response.status_code == 400
    assert Membership.objects.get(pool=pool, usuario=otro).cantidad == 3


def test_editar_pool_vencido_400_y_queda_cancelado(api_client, user, categoria):
    pool = crear_pool_vencido(user, categoria)
    autenticar(api_client, user)

    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"titulo": "Nuevo"}, format="json"
    )

    assert response.status_code == 400
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.CANCELADO
    assert pool.titulo == "Pool"


def test_DW_3_4_listo_vencido_no_se_cancela(api_client, user, categoria):
    ayer = timezone.localdate() - timedelta(days=1)
    pool = crear_pool(user, categoria, estado=Pool.Estado.LISTO, fecha_caducidad=ayer)
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-detail", args=[pool.id]))

    assert response.data["estado"] == "listo"
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.LISTO


def test_DW_3_3_comando_cancela_vencidos_e_ignora_otros_estados(user, categoria, capsys):
    ayer = timezone.localdate() - timedelta(days=1)
    vencido = crear_pool_vencido(user, categoria, titulo="Abierto vencido")
    de_hoy = crear_pool(user, categoria, titulo="Vence hoy", fecha_caducidad=timezone.localdate())
    listo = crear_pool(
        user, categoria, titulo="Listo", estado=Pool.Estado.LISTO, fecha_caducidad=ayer
    )
    en_curso = crear_pool(
        user, categoria, titulo="En curso", estado=Pool.Estado.EN_CURSO, fecha_caducidad=ayer
    )
    finalizado = crear_pool(
        user, categoria, titulo="Finalizado", estado=Pool.Estado.FINALIZADO, fecha_caducidad=ayer
    )
    cancelado = crear_pool(
        user, categoria, titulo="Cancelado", estado=Pool.Estado.CANCELADO, fecha_caducidad=ayer
    )

    call_command("expirar_pools")

    assert capsys.readouterr().out.strip() == "Pools cancelados: 1."
    esperados = (
        (vencido, Pool.Estado.CANCELADO),
        (de_hoy, Pool.Estado.ABIERTO),
        (listo, Pool.Estado.LISTO),
        (en_curso, Pool.Estado.EN_CURSO),
        (finalizado, Pool.Estado.FINALIZADO),
        (cancelado, Pool.Estado.CANCELADO),
    )
    for pool, esperado in esperados:
        pool.refresh_from_db()
        assert pool.estado == esperado

    call_command("expirar_pools")
    assert capsys.readouterr().out.strip() == "Pools cancelados: 0."


def test_expirar_vencidos_devuelve_pks_y_es_idempotente(user, categoria):
    primero = crear_pool_vencido(user, categoria)
    segundo = crear_pool_vencido(user, categoria)
    crear_pool(user, categoria, fecha_caducidad=timezone.localdate())

    assert sorted(expirar_vencidos()) == sorted([primero.pk, segundo.pk])
    assert expirar_vencidos() == []


# --- mios / unidos ---


def test_mios(api_client, user, otro, categoria, pool):
    crear_pool(otro, categoria, titulo="De otro")
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-mios"))
    assert response.data["count"] == 1
    assert response.data["results"][0]["titulo"] == pool.titulo


def test_unidos(api_client, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    autenticar(api_client, otro)
    response = api_client.get(reverse("pool-unidos"))
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == pool.id


# --- DW-6.3: filtros y ordering por pestaña (mios / unidos) ---


@pytest.fixture(params=["mios", "unidos"])
def pestana(request):
    return request.param


def pool_en_pestana(pestana, user, otro, categoria, **overrides):
    """Pool visible en la pestaña: propio en mios, con membership en unidos."""
    if pestana == "mios":
        return crear_pool(user, categoria, **overrides)
    pool = crear_pool(otro, categoria, **overrides)
    Membership.objects.create(pool=pool, usuario=user, cantidad=1)
    return pool


def pool_fuera_de_pestana(pestana, user, otro, categoria, **overrides):
    """Pool que matchea los filtros pero no pertenece a la pestaña."""
    if pestana == "mios":
        return crear_pool(otro, categoria, **overrides)
    return crear_pool(user, categoria, **overrides)


def test_DW_6_3_filtro_q_por_pestana(pestana, api_client, user, otro, categoria):
    visible = pool_en_pestana(pestana, user, otro, categoria, titulo="Yerba visible")
    pool_en_pestana(pestana, user, otro, categoria, titulo="Fideos")
    pool_fuera_de_pestana(pestana, user, otro, categoria, titulo="Yerba ajena")
    autenticar(api_client, user)
    response = api_client.get(reverse(f"pool-{pestana}"), {"q": "yerba"})
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == visible.id


def test_DW_6_3_filtro_categoria_por_pestana(pestana, api_client, user, otro, categoria):
    otra = Category.objects.create(nombre="Otra")
    pool_en_pestana(pestana, user, otro, categoria, titulo="Base")
    visible = pool_en_pestana(pestana, user, otro, otra, titulo="En otra")
    pool_fuera_de_pestana(pestana, user, otro, otra, titulo="Ajena")
    autenticar(api_client, user)
    response = api_client.get(reverse(f"pool-{pestana}"), {"categoria": otra.id})
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == visible.id


def test_DW_6_3_filtro_precio_por_pestana(pestana, api_client, user, otro, categoria):
    visible = pool_en_pestana(pestana, user, otro, categoria, precio_unitario="300.00")
    pool_en_pestana(pestana, user, otro, categoria, precio_unitario="100.00")
    pool_en_pestana(pestana, user, otro, categoria, precio_unitario="900.00")
    pool_fuera_de_pestana(pestana, user, otro, categoria, precio_unitario="400.00")
    autenticar(api_client, user)
    response = api_client.get(
        reverse(f"pool-{pestana}"), {"precio_min": 200, "precio_max": 600}
    )
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == visible.id


def test_DW_6_3_filtro_ciudad_por_pestana(pestana, api_client, user, otro, categoria):
    visible = pool_en_pestana(pestana, user, otro, categoria, ciudad="Rosario")
    pool_en_pestana(pestana, user, otro, categoria, ciudad="Mendoza")
    pool_fuera_de_pestana(pestana, user, otro, categoria, ciudad="Rosario")
    autenticar(api_client, user)
    response = api_client.get(reverse(f"pool-{pestana}"), {"ciudad": "rosar"})
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == visible.id


def test_DW_6_3_filtro_estado_por_pestana(pestana, api_client, user, otro, categoria):
    pool_en_pestana(pestana, user, otro, categoria, titulo="Abierto")
    cancelado = pool_en_pestana(pestana, user, otro, categoria, titulo="Cancelado")
    poner_estado(cancelado, Pool.Estado.CANCELADO)
    ajena = pool_fuera_de_pestana(pestana, user, otro, categoria, titulo="Cancelado ajeno")
    poner_estado(ajena, Pool.Estado.CANCELADO)
    autenticar(api_client, user)
    response = api_client.get(reverse(f"pool-{pestana}"), {"estado": "cancelado"})
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == cancelado.id


def test_DW_6_3_ordering_por_pestana(pestana, api_client, user, otro, categoria):
    pool_en_pestana(pestana, user, otro, categoria, titulo="Barato", precio_unitario="100.00")
    pool_en_pestana(pestana, user, otro, categoria, titulo="Caro", precio_unitario="900.00")
    pool_fuera_de_pestana(
        pestana, user, otro, categoria, titulo="Medio", precio_unitario="500.00"
    )
    autenticar(api_client, user)
    url = reverse(f"pool-{pestana}")
    asc = api_client.get(url, {"ordering": "precio_unitario"})
    assert [p["titulo"] for p in asc.data["results"]] == ["Barato", "Caro"]
    desc = api_client.get(url, {"ordering": "-precio_unitario"})
    assert [p["titulo"] for p in desc.data["results"]] == ["Caro", "Barato"]


def test_DW_6_3_paginacion_por_pestana(pestana, api_client, user, otro, categoria):
    for i in range(13):
        pool_en_pestana(
            pestana, user, otro, categoria, titulo=f"Pool {i}", precio_unitario=f"{i + 1}.00"
        )
    autenticar(api_client, user)
    url = reverse(f"pool-{pestana}")
    primera = api_client.get(url, {"ordering": "precio_unitario"})
    assert primera.data["count"] == 13
    assert len(primera.data["results"]) == 12
    assert primera.data["results"][0]["titulo"] == "Pool 0"
    segunda = api_client.get(url, {"ordering": "precio_unitario", "page": 2})
    assert len(segunda.data["results"]) == 1
    assert segunda.data["results"][0]["titulo"] == "Pool 12"
    assert segunda.data["next"] is None


# --- Integrantes y mi_cantidad ---


def test_integrantes_cuenta_memberships(api_client, user, otro, categoria, pool):
    tercero = User.objects.create_user(
        email="c@example.com", username="c", dni="10000003", password=PASSWORD
    )
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    Membership.objects.create(pool=pool, usuario=tercero, cantidad=2)
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.data["integrantes"] == 3


def test_pool_sin_memberships_un_integrante(api_client, user, pool):
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.data["integrantes"] == 1


def test_unidos_integrantes_no_se_limita_al_usuario(api_client, user, otro, categoria, pool):
    tercero = User.objects.create_user(
        email="c@example.com", username="c", dni="10000003", password=PASSWORD
    )
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    Membership.objects.create(pool=pool, usuario=tercero, cantidad=2)
    autenticar(api_client, otro)
    response = api_client.get(reverse("pool-unidos"))
    assert response.data["results"][0]["integrantes"] == 3


def test_mi_cantidad_null_y_con_valor(api_client, otro, pool):
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.data["mi_cantidad"] is None

    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, otro)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.data["mi_cantidad"] == 3


# --- Imagenes ---


def subir_imagen(api_client, pool):
    upload = SimpleUploadedFile("img.png", PNG_1X1, content_type="image/png")
    return api_client.post(
        reverse("pool-subir-imagen", args=[pool.id]), {"imagen": upload}, format="multipart"
    )


def test_subir_imagen_ok(api_client, user, pool, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    autenticar(api_client, user)
    response = subir_imagen(api_client, pool)
    assert response.status_code == 201
    assert pool.imagenes.count() == 1


def test_subir_imagen_limite_10(api_client, user, pool, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    for i in range(10):
        PoolImage.objects.create(pool=pool, imagen=f"pools/fake{i}.png")
    autenticar(api_client, user)
    response = subir_imagen(api_client, pool)
    assert response.status_code == 400


def test_subir_imagen_no_creador_403(api_client, otro, pool, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    autenticar(api_client, otro)
    response = subir_imagen(api_client, pool)
    assert response.status_code == 403


def test_borrar_imagen(api_client, user, pool, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    imagen = PoolImage.objects.create(pool=pool, imagen="pools/fake.png")
    autenticar(api_client, user)
    response = api_client.delete(reverse("pool-borrar-imagen", args=[pool.id, imagen.id]))
    assert response.status_code == 204
    assert pool.imagenes.count() == 0


def test_subir_imagen_formato_invalido(api_client, user, pool, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    archivo = SimpleUploadedFile("img.gif", imagen_bytes("GIF"), content_type="image/gif")
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-subir-imagen", args=[pool.id]), {"imagen": archivo}, format="multipart"
    )
    assert response.status_code == 400
    assert "imagen" in response.data


# --- Estado abierto/listo fuera de unirse ---


def test_crear_pool_lleno_queda_listo(api_client, user, categoria):
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-list"),
        payload(categoria, cantidad_total=2, cantidad_creador=2),
        format="json",
    )
    assert response.status_code == 201
    assert response.data["disponible"] == 0
    assert response.data["estado"] == "listo"


def test_patch_creador_sobre_suscribe_400(api_client, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=5)
    autenticar(api_client, user)
    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"cantidad_creador": 6}, format="json"
    )
    assert response.status_code == 400
    assert "cantidad_creador" in response.data


def test_patch_creador_completa_queda_listo(api_client, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=5)
    autenticar(api_client, user)
    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"cantidad_creador": 5}, format="json"
    )
    assert response.status_code == 200
    assert response.data["disponible"] == 0
    assert response.data["estado"] == "listo"


def test_miembro_baja_cantidad_vuelve_abierto(api_client, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=5)
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, otro)
    response = api_client.patch(
        reverse("pool-mi-membresia", args=[pool.id]), {"cantidad": 4}, format="json"
    )
    assert response.status_code == 200
    assert response.data["disponible"] == 4
    assert response.data["estado"] == "abierto"


# --- Lecturas publicas y PII ---


def test_categorias_publicas_sin_token(api_client, categoria):
    response = api_client.get(reverse("category-list"))
    assert response.status_code == 200


def test_mios_requiere_auth(api_client):
    response = api_client.get(reverse("pool-mios"))
    assert response.status_code == 401


def test_unidos_requiere_auth(api_client):
    response = api_client.get(reverse("pool-unidos"))
    assert response.status_code == 401


def test_detalle_publico_sin_email(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.status_code == 200
    assert "email" not in response.data["creador"]
    assert "email" not in response.data["miembros"][0]["usuario"]


# --- Geocodificacion ---


class RespuestaNominatim:
    def __init__(self, cuerpo):
        self.cuerpo = json.dumps(cuerpo).encode("utf-8")

    def read(self):
        return self.cuerpo

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class RelojFalso:
    """Reemplaza time.monotonic/time.sleep para probar la cuota sin esperar."""

    def __init__(self, momentos):
        self.momentos = iter(momentos)
        self.esperas = []

    def monotonic(self):
        return next(self.momentos)

    def sleep(self, segundos):
        self.esperas.append(segundos)


def urlopen_fijo(cuerpo, pedidos=None):
    def urlopen_falso(pedido, timeout=None):
        if pedidos is not None:
            pedidos.append(pedido)
        return RespuestaNominatim(cuerpo)

    return urlopen_falso


@pytest.fixture(autouse=True)
def geocodificacion_sin_red(monkeypatch):
    """Ningún test toca Nominatim: el hook de las vistas es un fake offline."""
    monkeypatch.setattr(views, "geocodificar", lambda direccion, ciudad: None)
    monkeypatch.setattr(geocoding, "INTERVALO_MINIMO", 0)


class NominatimFalso:
    """Doble de la HTTP de Nominatim; acumula los pedidos y permite cambiarla."""

    def __init__(self):
        self.pedidos = []
        self.cuerpo = [{"lat": "-31.416700", "lon": "-64.183300"}]

    def urlopen(self, pedido, timeout=None):
        self.pedidos.append(pedido)
        return RespuestaNominatim(self.cuerpo)


@pytest.fixture
def nominatim(geocodificacion_sin_red, monkeypatch):
    """Restaura la cadena real (vista → geocoding) con la HTTP mockeada."""
    falso = NominatimFalso()
    monkeypatch.setattr(geocoding, "urlopen", falso.urlopen)
    monkeypatch.setattr(views, "geocodificar", geocoding.geocodificar)
    return falso


def test_geocodificar_ok_devuelve_decimales(monkeypatch):
    monkeypatch.setattr(
        geocoding, "urlopen", urlopen_fijo([{"lat": "-31.4167", "lon": "-64.1833"}])
    )
    assert geocoding.geocodificar("Av. Corrientes 1234", "CABA") == (
        Decimal("-31.4167"),
        Decimal("-64.1833"),
    )


def test_geocodificar_normaliza_a_seis_decimales(monkeypatch):
    monkeypatch.setattr(
        geocoding, "urlopen", urlopen_fijo([{"lat": "-34.6045415", "lon": "-58.3958768"}])
    )
    assert geocoding.geocodificar("Av. Corrientes 1234", "CABA") == (
        Decimal("-34.604542"),
        Decimal("-58.395877"),
    )


def test_geocodificar_sin_resultados_devuelve_none(monkeypatch):
    monkeypatch.setattr(geocoding, "urlopen", urlopen_fijo([]))
    assert geocoding.geocodificar("Calle Inexistente 999", "Cordoba") is None


def test_geocodificar_error_de_red_devuelve_none_y_loguea(monkeypatch, caplog):
    def urlopen_roto(pedido, timeout=None):
        raise URLError("sin conexión")

    monkeypatch.setattr(geocoding, "urlopen", urlopen_roto)
    with caplog.at_level(logging.WARNING, logger="pools.geocoding"):
        assert geocoding.geocodificar("Calle 1", "Cordoba") is None
    assert "No se pudo geocodificar" in caplog.text


def test_geocodificar_respuesta_malformada_devuelve_none(monkeypatch, caplog):
    monkeypatch.setattr(geocoding, "urlopen", urlopen_fijo([{"lat": "no-es-numero", "lon": "1"}]))
    with caplog.at_level(logging.WARNING, logger="pools.geocoding"):
        assert geocoding.geocodificar("Calle 1", "Cordoba") is None
    assert "Coordenadas inválidas" in caplog.text

    monkeypatch.setattr(geocoding, "urlopen", urlopen_fijo({"error": "algo"}))
    assert geocoding.geocodificar("Calle 1", "Cordoba") is None


def test_geocodificar_nan_devuelve_none(monkeypatch):
    # Decimal("NaN") pasa cualquier comparación de rango sin error: hay que descartarlo antes.
    monkeypatch.setattr(geocoding, "urlopen", urlopen_fijo([{"lat": "NaN", "lon": "-64.1"}]))
    assert geocoding.geocodificar("Calle 1", "Cordoba") is None

    monkeypatch.setattr(geocoding, "urlopen", urlopen_fijo([{"lat": "-31.4", "lon": "NaN"}]))
    assert geocoding.geocodificar("Calle 1", "Cordoba") is None


def test_geocodificar_nan_en_crear_pool_no_explota(api_client, user, categoria, monkeypatch):
    monkeypatch.setattr(geocoding, "urlopen", urlopen_fijo([{"lat": "NaN", "lon": "NaN"}]))
    monkeypatch.setattr(views, "geocodificar", geocoding.geocodificar)
    autenticar(api_client, user)

    response = api_client.post(reverse("pool-list"), payload(categoria), format="json")

    assert response.status_code == 201
    pool = Pool.objects.get(pk=response.data["id"])
    assert pool.latitud is None and pool.longitud is None


def test_geocodificar_coordenadas_fuera_de_rango_descarta(monkeypatch):
    monkeypatch.setattr(geocoding, "urlopen", urlopen_fijo([{"lat": "91.0", "lon": "-64.1"}]))
    assert geocoding.geocodificar("Calle 1", "Cordoba") is None

    monkeypatch.setattr(geocoding, "urlopen", urlopen_fijo([{"lat": "-31.4", "lon": "181.0"}]))
    assert geocoding.geocodificar("Calle 1", "Cordoba") is None


def test_geocodificar_toma_el_primer_resultado(monkeypatch):
    monkeypatch.setattr(
        geocoding,
        "urlopen",
        urlopen_fijo([{"lat": "-31.1", "lon": "-64.1"}, {"lat": "-30.0", "lon": "-63.0"}]),
    )
    assert geocoding.geocodificar("Calle 1", "Cordoba") == (Decimal("-31.1"), Decimal("-64.1"))


def test_geocodificar_arma_consulta_y_user_agent(monkeypatch):
    pedidos = []
    monkeypatch.setattr(geocoding, "urlopen", urlopen_fijo([{"lat": "1", "lon": "2"}], pedidos))

    geocoding.geocodificar("Av. Corrientes 1234", "CABA")

    pedido = pedidos[0]
    query = parse_qs(urlsplit(pedido.full_url).query)
    assert query["q"] == ["Av. Corrientes 1234, CABA"]
    assert query["format"] == ["json"]
    assert pedido.get_header("User-agent") == geocoding.USER_AGENT


def test_geocodificar_consulta_vacia_no_llama(monkeypatch):
    pedidos = []
    monkeypatch.setattr(geocoding, "urlopen", urlopen_fijo([{"lat": "1", "lon": "2"}], pedidos))
    assert geocoding.geocodificar("", "") is None
    assert pedidos == []


def test_geocodificar_timeout_devuelve_none(monkeypatch):
    def urlopen_timeout(pedido, timeout=None):
        raise TimeoutError("se agotó el tiempo de espera")

    monkeypatch.setattr(geocoding, "urlopen", urlopen_timeout)
    assert geocoding.geocodificar("Calle 1", "Cordoba") is None


def test_cuota_geocodificacion_espacia_pedidos(monkeypatch):
    reloj = RelojFalso([100.0, 100.0, 100.25, 100.25])
    monkeypatch.setattr(geocoding, "time", reloj)
    monkeypatch.setattr(geocoding, "INTERVALO_MINIMO", 1.0)
    monkeypatch.setattr(geocoding, "_ultimo_pedido", 0.0)

    geocoding._respetar_cuota()
    geocoding._respetar_cuota()

    assert reloj.esperas == [pytest.approx(0.75)]


def test_DW_2_1_crear_pool_guarda_coords(api_client, user, categoria, nominatim):
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-list"), payload(categoria), format="json")
    assert response.status_code == 201

    pool = Pool.objects.get(pk=response.data["id"])
    assert (pool.latitud, pool.longitud) == (Decimal("-31.416700"), Decimal("-64.183300"))
    assert Decimal(response.data["latitud"]) == Decimal("-31.416700")
    assert Decimal(response.data["longitud"]) == Decimal("-64.183300")
    assert len(nominatim.pedidos) == 1


def test_DW_2_2_crear_pool_con_geocodificacion_caida_coords_null(
    api_client, user, categoria, monkeypatch
):
    def urlopen_roto(pedido, timeout=None):
        raise URLError("Nominatim caído")

    monkeypatch.setattr(geocoding, "urlopen", urlopen_roto)
    monkeypatch.setattr(views, "geocodificar", geocoding.geocodificar)
    autenticar(api_client, user)

    response = api_client.post(reverse("pool-list"), payload(categoria), format="json")

    assert response.status_code == 201
    pool = Pool.objects.get(pk=response.data["id"])
    assert pool.latitud is None and pool.longitud is None
    assert response.data["latitud"] is None and response.data["longitud"] is None


def test_DW_2_2_crear_pool_sin_resultados_coords_null(api_client, user, categoria, monkeypatch):
    monkeypatch.setattr(geocoding, "urlopen", urlopen_fijo([]))
    monkeypatch.setattr(views, "geocodificar", geocoding.geocodificar)
    autenticar(api_client, user)

    response = api_client.post(reverse("pool-list"), payload(categoria), format="json")

    assert response.status_code == 201
    pool = Pool.objects.get(pk=response.data["id"])
    assert pool.latitud is None and pool.longitud is None


def test_DW_2_4_editar_direccion_actualiza_coords(api_client, user, categoria, nominatim):
    autenticar(api_client, user)
    creado = api_client.post(reverse("pool-list"), payload(categoria), format="json")
    nominatim.cuerpo = [{"lat": "-32.950000", "lon": "-60.650000"}]

    response = api_client.patch(
        reverse("pool-detail", args=[creado.data["id"]]),
        {"direccion": "Calle Nueva 456"},
        format="json",
    )

    assert response.status_code == 200
    pool = Pool.objects.get(pk=creado.data["id"])
    assert (pool.latitud, pool.longitud) == (Decimal("-32.950000"), Decimal("-60.650000"))
    assert len(nominatim.pedidos) == 2


def test_DW_2_4_editar_sin_cambiar_direccion_no_geocodifica(
    api_client, user, categoria, nominatim
):
    autenticar(api_client, user)
    creado = api_client.post(reverse("pool-list"), payload(categoria), format="json")
    assert len(nominatim.pedidos) == 1

    # El form de edición reenvía dirección y ciudad sin cambios: no debe re-consultar.
    response = api_client.patch(
        reverse("pool-detail", args=[creado.data["id"]]),
        {"titulo": "Otro título", "direccion": "Calle 1", "ciudad": "Cordoba"},
        format="json",
    )

    assert response.status_code == 200
    assert len(nominatim.pedidos) == 1
    assert Pool.objects.get(pk=creado.data["id"]).latitud == Decimal("-31.416700")


def test_pool_viejo_sin_coords_geocodifica_al_guardar(api_client, user, pool, nominatim):
    autenticar(api_client, user)
    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"titulo": "Nuevo título"}, format="json"
    )

    assert response.status_code == 200
    assert len(nominatim.pedidos) == 1
    pool.refresh_from_db()
    assert pool.latitud == Decimal("-31.416700")


def test_editar_direccion_con_falla_descarta_coords_viejas(
    api_client, user, categoria, nominatim, monkeypatch
):
    autenticar(api_client, user)
    creado = api_client.post(reverse("pool-list"), payload(categoria), format="json")
    assert Pool.objects.get(pk=creado.data["id"]).latitud is not None

    def urlopen_roto(pedido, timeout=None):
        raise URLError("Nominatim caído")

    monkeypatch.setattr(geocoding, "urlopen", urlopen_roto)
    response = api_client.patch(
        reverse("pool-detail", args=[creado.data["id"]]),
        {"direccion": "Calle Nueva 456"},
        format="json",
    )

    assert response.status_code == 200
    pool = Pool.objects.get(pk=creado.data["id"])
    assert pool.latitud is None and pool.longitud is None


def test_latitud_longitud_read_only(api_client, user, pool):
    autenticar(api_client, user)
    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]),
        {"latitud": "12.345678", "longitud": "-65.000000"},
        format="json",
    )

    assert response.status_code == 200
    pool.refresh_from_db()
    assert pool.latitud is None and pool.longitud is None


# --- Eliminación con aprobación ---


def crear_miembro(pool, n):
    usuario = User.objects.create_user(
        email=f"miembro{n}@example.com",
        username=f"miembro{n}",
        dni=f"400000{n:02d}",
        password=PASSWORD,
    )
    Membership.objects.create(pool=pool, usuario=usuario, cantidad=1)
    return usuario


def pool_en_curso_con_miembros(user, categoria, n):
    pool = crear_pool(user, categoria, cantidad_total=10, cantidad_creador=2)
    for i in range(n):
        crear_miembro(pool, i)
    poner_estado(pool, Pool.Estado.EN_CURSO)
    return pool


def test_DW_4_1_creador_solicita_201(api_client, user, categoria, pool):
    crear_miembro(pool, 0)
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)

    response = api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    assert response.status_code == 201
    assert response.data["estado"] == "pendiente"
    assert "id" in response.data
    assert SolicitudEliminacion.objects.filter(pool=pool, estado="pendiente").exists()


def test_DW_4_1_salir_y_unirse_bloqueados_con_pendiente(api_client, user, categoria, pool):
    otro = crear_miembro(pool, 0)
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)
    assert api_client.post(reverse("pool-eliminacion", args=[pool.id])).status_code == 201

    autenticar(api_client, otro)
    response = api_client.delete(reverse("pool-salir", args=[pool.id]))
    assert response.status_code == 400
    assert "solicitud de eliminación" in str(response.data)
    assert Membership.objects.filter(pool=pool, usuario=otro).exists()

    tercero = User.objects.create_user(
        email="c@example.com", username="c", dni="10000003", password=PASSWORD
    )
    autenticar(api_client, tercero)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1, "telefono": TELEFONO}, format="json"
    )
    assert response.status_code == 400
    assert not Membership.objects.filter(pool=pool, usuario=tercero).exists()


def test_DW_4_2_unanimidad_borra_pool_y_memberships(api_client, user, categoria, pool):
    crear_miembro(pool, 0)
    crear_miembro(pool, 1)
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)
    assert api_client.post(reverse("pool-eliminacion", args=[pool.id])).status_code == 201

    autenticar(api_client, User.objects.get(username="miembro0"))
    primer = api_client.post(
        reverse("pool-eliminacion-voto", args=[pool.id]), {"acepta": True}, format="json"
    )
    assert primer.status_code == 200
    assert primer.data["estado"] == "pendiente"
    assert Pool.objects.filter(pk=pool.pk).exists()

    autenticar(api_client, User.objects.get(username="miembro1"))
    ultimo = api_client.post(
        reverse("pool-eliminacion-voto", args=[pool.id]), {"acepta": True}, format="json"
    )
    assert ultimo.status_code == 200
    assert ultimo.data["estado"] == "aprobada"
    assert not Pool.objects.filter(pk=pool.pk).exists()
    assert not Membership.objects.filter(pool_id=pool.pk).exists()
    assert not SolicitudEliminacion.objects.filter(pool_id=pool.pk).exists()


def test_DW_4_3_un_rechazo_cierra_y_pool_intacto(api_client, user, categoria, pool):
    crear_miembro(pool, 0)
    crear_miembro(pool, 1)
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)
    api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    autenticar(api_client, User.objects.get(username="miembro0"))
    api_client.post(
        reverse("pool-eliminacion-voto", args=[pool.id]), {"acepta": True}, format="json"
    )

    autenticar(api_client, User.objects.get(username="miembro1"))
    response = api_client.post(
        reverse("pool-eliminacion-voto", args=[pool.id]), {"acepta": False}, format="json"
    )

    assert response.status_code == 200
    assert response.data["estado"] == "rechazada"
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.EN_CURSO
    assert SolicitudEliminacion.objects.get(pool=pool).estado == "rechazada"


def test_DW_4_4_no_creador_403(api_client, otro, pool):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, otro)

    response = api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    assert response.status_code == 403


def test_DW_4_4_no_miembro_403(api_client, user, categoria, pool):
    crear_miembro(pool, 0)
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)
    api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    tercero = User.objects.create_user(
        email="c@example.com", username="c", dni="10000003", password=PASSWORD
    )
    autenticar(api_client, tercero)
    response = api_client.post(
        reverse("pool-eliminacion-voto", args=[pool.id]), {"acepta": True}, format="json"
    )

    assert response.status_code == 403


def test_DW_4_4_solicitud_duplicada_400(api_client, user, categoria, pool):
    crear_miembro(pool, 0)
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)
    assert api_client.post(reverse("pool-eliminacion", args=[pool.id])).status_code == 201

    response = api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    assert response.status_code == 400
    assert SolicitudEliminacion.objects.filter(pool=pool).count() == 1


def test_DW_4_4_voto_duplicado_400(api_client, user, categoria, pool):
    crear_miembro(pool, 0)
    crear_miembro(pool, 1)
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)
    api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    autenticar(api_client, User.objects.get(username="miembro0"))
    api_client.post(
        reverse("pool-eliminacion-voto", args=[pool.id]), {"acepta": True}, format="json"
    )
    response = api_client.post(
        reverse("pool-eliminacion-voto", args=[pool.id]), {"acepta": True}, format="json"
    )

    assert response.status_code == 400
    assert "Ya votaste" in str(response.data)


def test_DW_4_4_solicitar_en_abierto_400(api_client, user, pool):
    autenticar(api_client, user)

    response = api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    assert response.status_code == 400


def test_DW_4_4_votar_en_abierto_400(api_client, user, categoria, pool):
    miembro = crear_miembro(pool, 0)
    autenticar(api_client, miembro)

    response = api_client.post(
        reverse("pool-eliminacion-voto", args=[pool.id]), {"acepta": True}, format="json"
    )

    assert response.status_code == 400
    assert "No hay una solicitud" in str(response.data)


def test_DW_4_4_creador_vota_400(api_client, user, categoria, pool):
    crear_miembro(pool, 0)
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)
    api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    response = api_client.post(
        reverse("pool-eliminacion-voto", args=[pool.id]), {"acepta": True}, format="json"
    )

    assert response.status_code == 400
    assert "El creador no puede votar" in str(response.data)


def test_DW_4_5_eliminar_directo_en_abierto_regresion(api_client, user, pool):
    autenticar(api_client, user)

    response = api_client.delete(reverse("pool-detail", args=[pool.id]))

    assert response.status_code == 204
    assert not Pool.objects.filter(pk=pool.pk).exists()


def test_solicitud_cero_miembros_borra_inmediato(api_client, user, categoria, pool):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)

    response = api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    assert response.status_code == 200
    assert response.data["estado"] == "aprobada"
    assert not Pool.objects.filter(pk=pool.pk).exists()


def test_solicitud_se_cierra_al_finalizar(api_client, user, categoria, pool):
    crear_miembro(pool, 0)
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)
    api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    response = api_client.post(reverse("pool-finalizar", args=[pool.id]))

    assert response.status_code == 200
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.FINALIZADO
    assert SolicitudEliminacion.objects.get(pool=pool).estado == "cancelada"


def test_rechazo_permite_re_solicitar(api_client, user, categoria, pool):
    crear_miembro(pool, 0)
    crear_miembro(pool, 1)
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)
    api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    autenticar(api_client, User.objects.get(username="miembro0"))
    api_client.post(
        reverse("pool-eliminacion-voto", args=[pool.id]), {"acepta": False}, format="json"
    )

    autenticar(api_client, user)
    response = api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    assert response.status_code == 201
    assert SolicitudEliminacion.objects.filter(pool=pool).count() == 2


def test_get_eliminacion_muestra_votos(api_client, user, categoria, pool):
    crear_miembro(pool, 0)
    crear_miembro(pool, 1)
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)
    api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    autenticar(api_client, User.objects.get(username="miembro0"))
    api_client.post(
        reverse("pool-eliminacion-voto", args=[pool.id]), {"acepta": True}, format="json"
    )

    autenticar(api_client, user)
    response = api_client.get(reverse("pool-eliminacion", args=[pool.id]))

    assert response.status_code == 200
    assert response.data["estado"] == "pendiente"
    assert response.data["total"] == 2
    assert response.data["aceptaron"] == 1
    assert len(response.data["votos"]) == 1
    assert response.data["votos"][0]["acepta"] is True
    assert response.data["votos"][0]["usuario"]["username"] == "miembro0"


def test_get_eliminacion_no_participante_403(api_client, user, categoria, pool):
    crear_miembro(pool, 0)
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)
    api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    tercero = User.objects.create_user(
        email="x@example.com", username="x", dni="99999999", password=PASSWORD
    )
    autenticar(api_client, tercero)
    response = api_client.get(reverse("pool-eliminacion", args=[pool.id]))

    assert response.status_code == 403


def test_mi_membresia_bloqueado_con_pendiente(api_client, user, categoria, pool):
    miembro = crear_miembro(pool, 0)
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)
    api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    autenticar(api_client, miembro)
    response = api_client.patch(
        reverse("pool-mi-membresia", args=[pool.id]), {"cantidad": 2}, format="json"
    )

    assert response.status_code == 400
    assert "solicitud de eliminación" in str(response.data)


# --- Análisis del enlace (Plan 3, Fase 2) ---

ENLACE_VALIDO = "https://www.mercadolibre.com.ar/yerba-1kg"
CLAVES_ENLACE = ["formato", "https", "longitud", "ip_literal", "acortador", "tld", "uso"]


def validaciones_de(analisis):
    return {v["clave"]: v for v in analisis["validaciones"]}


def red_prohibida(monkeypatch):
    """Cualquier intento de red explota: el analizador no debe tocar la URL."""

    def prohibido(*args, **kwargs):
        raise AssertionError("El análisis del enlace no debe hacer red")

    monkeypatch.setattr(socket, "getaddrinfo", prohibido)
    monkeypatch.setattr(urllib.request, "urlopen", prohibido)


def test_DW_2_1_enlace_valido_todas_ok():
    analisis = confianza.analizar_enlace(ENLACE_VALIDO, uso=2)
    assert analisis["nivel"] == "alto"
    assert [v["clave"] for v in analisis["validaciones"]] == CLAVES_ENLACE
    assert all(v["ok"] for v in analisis["validaciones"])
    assert all(v["detalle"] for v in analisis["validaciones"])


def test_DW_2_1_url_malformada_nivel_bajo_con_detalle():
    for url in (
        "",
        "   ",
        None,
        123,
        "no es una url",
        "http://",
        "javascript:alert(1)",
        "https://[::1",
        "https://localhost/x",  # host sin punto: no es un dominio público
    ):
        analisis = confianza.analizar_enlace(url)
        assert analisis["nivel"] == "bajo", url
        assert analisis["validaciones"] == [
            {"clave": "formato", "ok": False, "detalle": "El enlace no tiene un formato válido."}
        ], url


def test_DW_2_1_http_sin_https_nivel_medio():
    analisis = confianza.analizar_enlace("http://www.tienda.com.ar/producto")
    assert analisis["nivel"] == "medio"
    validacion = validaciones_de(analisis)["https"]
    assert not validacion["ok"]
    assert "HTTPS" in validacion["detalle"]


def test_DW_2_1_ip_literal_alerta():
    for url in ("https://192.168.0.1/admin", "https://[::1]/panel"):
        analisis = confianza.analizar_enlace(url)
        assert analisis["nivel"] == "bajo", url
        assert not validaciones_de(analisis)["ip_literal"]["ok"], url


def test_DW_2_1_acortador_alerta():
    analisis = confianza.analizar_enlace("https://bit.ly/oferta-123")
    assert analisis["nivel"] == "medio"
    validacion = validaciones_de(analisis)["acortador"]
    assert not validacion["ok"]
    assert "acortador" in validacion["detalle"].lower()


def test_DW_2_1_tld_sospechoso():
    urls = (
        "https://sorteo-premios.xyz/gana",  # TLD frecuente en abuso
        "https://xn--ofertas-9za.com/",  # punycode (homógrafo)
        "https://a.b.c.d.evil.com/",  # demasiados subdominios
        "https://a.b.c.d.com/",  # cinco niveles: el límite es >4
    )
    for url in urls:
        analisis = confianza.analizar_enlace(url)
        assert analisis["nivel"] == "bajo", url
        assert not validaciones_de(analisis)["tld"]["ok"], url


def test_DW_2_1_longitud_larga():
    url = "https://tienda.com.ar/" + "a" * 200
    analisis = confianza.analizar_enlace(url)
    assert analisis["nivel"] == "medio"
    validacion = validaciones_de(analisis)["longitud"]
    assert not validacion["ok"]
    assert str(len(url)) in validacion["detalle"]


def test_DW_2_1_longitud_limite():
    """El límite es 150: exacto pasa, uno más no (borde del umbral)."""
    base = "https://tienda.com.ar/"
    al_limite = base + "a" * 128
    assert len(al_limite) == 150
    assert validaciones_de(confianza.analizar_enlace(al_limite))["longitud"]["ok"] is True

    pasado = al_limite + "a"
    assert len(pasado) == 151
    validacion = validaciones_de(confianza.analizar_enlace(pasado))["longitud"]
    assert validacion["ok"] is False
    assert "151" in validacion["detalle"]


def test_DW_2_1_normaliza_mayusculas_y_scheme_implicito():
    # Scheme implícito: se asume https y el análisis no falla por eso.
    implicito = confianza.analizar_enlace("MERCADOLIBRE.COM.AR/OFERTA")
    assert implicito["nivel"] == "alto"
    assert validaciones_de(implicito)["https"]["ok"]

    # Scheme explícito en mayúsculas: HTTPS no debe leerse como "no usa HTTPS".
    explicito = confianza.analizar_enlace("HTTPS://WWW.TIENDA.COM.AR/OFERTA")
    assert validaciones_de(explicito)["https"]["ok"]

    assert confianza.dominio_de("MERCADOLIBRE.COM.AR/OFERTA") == "mercadolibre.com.ar"
    assert confianza.dominio_de("HTTPS://WWW.MercadoLibre.com.AR/x") == "www.mercadolibre.com.ar"
    # El mismo dominio en distintas formas cuenta igual.
    assert confianza.dominio_de("http://tienda.com.ar/a") == confianza.dominio_de("tienda.com.ar/b")


def test_DW_2_1_dominio_de_malformado_none():
    for url in ("", "no es una url", "javascript:alert(1)", None):
        assert confianza.dominio_de(url) is None, url


def test_DW_2_3_uso_refleja_conteo():
    primero = validaciones_de(confianza.analizar_enlace(ENLACE_VALIDO, uso=1))["uso"]
    assert not primero["ok"]
    assert "Primer uso" in primero["detalle"]

    repetido = validaciones_de(confianza.analizar_enlace(ENLACE_VALIDO, uso=2))["uso"]
    assert repetido["ok"]
    assert "Uso alto" in repetido["detalle"]
    assert "2" in repetido["detalle"]

    mucho = validaciones_de(confianza.analizar_enlace(ENLACE_VALIDO, uso=7))["uso"]
    assert "7" in mucho["detalle"]

    # El uso es una señal aparte: no altera el nivel de confianza.
    assert confianza.analizar_enlace(ENLACE_VALIDO, uso=0)["nivel"] == "alto"


def test_DW_2_3_conteos_dominio_exactos(user, categoria):
    """El conteo por lote devuelve solo los dominios pedidos y sin falsos positivos."""
    crear_pool(user, categoria, titulo="A", enlace="https://www.tienda.com.ar/a")
    crear_pool(user, categoria, titulo="B", enlace="HTTPS://WWW.TIENDA.COM.AR/b")
    crear_pool(user, categoria, titulo="Decoy", enlace="https://www.tienda.com.ar.evil.com/c")

    # El decoy contiene al dominio pedido como substring pero no debe contar.
    assert confianza.conteos_dominio(["https://www.tienda.com.ar/x"]) == {"www.tienda.com.ar": 2}
    assert confianza.conteos_dominio(["https://www.tienda.com.ar.evil.com/c"]) == {
        "www.tienda.com.ar.evil.com": 1
    }
    assert confianza.conteos_dominio(["", None, "no es una url"]) == {}


def test_DW_2_2_detalle_con_enlace_expone_analisis(api_client, user, pool):
    pool.enlace = ENLACE_VALIDO
    pool.save(update_fields=["enlace"])
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-detail", args=[pool.id]))

    assert response.status_code == 200
    analisis = response.data["analisis_enlace"]
    assert analisis["nivel"] == "alto"
    assert [v["clave"] for v in analisis["validaciones"]] == CLAVES_ENLACE
    for validacion in analisis["validaciones"]:
        assert set(validacion) == {"clave", "ok", "detalle"}


def test_DW_2_2_sin_enlace_analisis_null(api_client, user, pool):
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-detail", args=[pool.id]))

    assert response.status_code == 200
    assert response.data["analisis_enlace"] is None


def test_DW_2_2_listado_tambien_expone_analisis(api_client, user, categoria, pool):
    pool.enlace = "https://www.tienda.com.ar/x"
    pool.save(update_fields=["enlace"])
    crear_pool(user, categoria, titulo="Otra compra", enlace="https://www.tienda.com.ar/y")
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-list"))

    assert response.status_code == 200
    assert len(response.data["results"]) == 2
    for fila in response.data["results"]:
        assert fila["analisis_enlace"]["nivel"] == "alto"
        assert validaciones_de(fila["analisis_enlace"])["uso"]["ok"] is True


def test_DW_2_3_uso_cuenta_pools_mismo_dominio(api_client, user, categoria, pool):
    pool.enlace = "https://www.tienda.com.ar/producto/1"
    pool.save(update_fields=["enlace"])
    crear_pool(user, categoria, titulo="Segunda", enlace="https://www.tienda.com.ar/producto/2")
    crear_pool(
        user, categoria, titulo="Tercera", enlace="HTTPS://WWW.TIENDA.COM.AR/producto/3"
    )
    # Decoys: otro dominio, y uno que contiene al analizado como substring.
    crear_pool(user, categoria, titulo="Otra tienda", enlace="https://otra.com.ar/x")
    crear_pool(
        user, categoria, titulo="Parecido", enlace="https://www.tienda.com.ar.evil.com/x"
    )
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-detail", args=[pool.id]))

    assert response.status_code == 200
    uso = validaciones_de(response.data["analisis_enlace"])["uso"]
    assert uso["ok"] is True
    assert "3" in uso["detalle"]


def test_DW_2_3_dominio_unico_es_primer_uso(api_client, user, categoria, pool):
    pool.enlace = "https://unica.com.ar/x"
    pool.save(update_fields=["enlace"])
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-detail", args=[pool.id]))

    uso = validaciones_de(response.data["analisis_enlace"])["uso"]
    assert uso["ok"] is False
    assert "Primer uso" in uso["detalle"]


def test_listado_analisis_sin_n_mas_uno(api_client, user, categoria):
    """El conteo de uso es por lote: la cantidad de queries no crece con los pools."""
    crear_pool(user, categoria, titulo="Uno", enlace="https://uno.com.ar/x")
    autenticar(api_client, user)

    with CaptureQueriesContext(connection) as primera:
        assert api_client.get(reverse("pool-list")).status_code == 200

    for i in range(5):
        crear_pool(user, categoria, titulo=f"Pool {i}", enlace=f"https://tienda{i}.com.ar/x")
    with CaptureQueriesContext(connection) as segunda:
        assert api_client.get(reverse("pool-list")).status_code == 200

    assert len(segunda) == len(primera)


def test_DW_2_4_analizar_sin_red(monkeypatch):
    red_prohibida(monkeypatch)
    esperados = {
        ENLACE_VALIDO: "alto",
        "http://192.168.0.1/x": "bajo",
        "https://bit.ly/abc": "medio",
        "no es una url": "bajo",
    }
    for url, nivel in esperados.items():
        assert confianza.analizar_enlace(url)["nivel"] == nivel, url


def test_DW_2_4_detalle_no_hace_fetch(api_client, user, pool, monkeypatch):
    pool.enlace = ENLACE_VALIDO
    pool.save(update_fields=["enlace"])
    red_prohibida(monkeypatch)
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-detail", args=[pool.id]))

    assert response.status_code == 200
    assert response.data["analisis_enlace"]["nivel"] == "alto"


def test_DW_2_4_confianza_sin_imports_de_red():
    """Revisión automatizada: el módulo no importa ni referencia mecanismos de red.

    Punto ciego conocido: solo cubre los mecanismos listados; la garantía de
    comportamiento la da `test_DW_2_4_analizar_sin_red` con la red prohibida.
    """
    fuente = Path(confianza.__file__).read_text(encoding="utf-8")
    for prohibido in ("urlopen", "urlretrieve", "requests", "httpx", "http.client", "socket"):
        assert prohibido not in fuente, prohibido


# --- Historial del pool (Plan 3, Fase 3) ---


def eventos_de(pool):
    """Eventos del pool en orden de creación (el API los devuelve al revés)."""
    return list(EventoPool.objects.filter(pool=pool).order_by("creado", "id"))


def test_crear_pool_registra_evento_creado(api_client, user, categoria):
    autenticar(api_client, user)

    response = api_client.post(reverse("pool-list"), payload(categoria), format="json")

    assert response.status_code == 201
    evento = EventoPool.objects.get(pool_id=response.data["id"])
    assert evento.tipo == EventoPool.Tipo.CREADO
    assert evento.actor == user
    assert evento.datos == {}


def test_DW_3_1_unirse_registra_evento_union(api_client, otro, pool):
    autenticar(api_client, otro)

    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), union_payload(cantidad=3), format="json"
    )

    assert response.status_code == 201
    evento = EventoPool.objects.get(pool=pool)
    assert evento.tipo == EventoPool.Tipo.UNION
    assert evento.actor == otro
    assert evento.datos == {"cantidad": 3}


def test_DW_3_4_evento_de_union_sin_pii(api_client, otro, pool):
    """El teléfono y el mensaje del miembro nunca entran al historial."""
    autenticar(api_client, otro)

    api_client.post(
        reverse("pool-unirse", args=[pool.id]),
        union_payload(cantidad=2, telefono="351 555 1234", mensaje="Me sumo"),
        format="json",
    )

    assert EventoPool.objects.get(pool=pool).datos == {"cantidad": 2}


def test_DW_3_1_salir_registra_evento_salida(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, otro)

    response = api_client.delete(reverse("pool-salir", args=[pool.id]))

    assert response.status_code == 204
    evento = EventoPool.objects.get(pool=pool)
    assert evento.tipo == EventoPool.Tipo.SALIDA
    assert evento.actor == otro
    assert evento.datos == {"cantidad": 3}


def test_DW_3_1_cantidad_registra_evento_con_antes_y_despues(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, otro)

    response = api_client.patch(
        reverse("pool-mi-membresia", args=[pool.id]), {"cantidad": 6}, format="json"
    )

    assert response.status_code == 200
    evento = EventoPool.objects.get(pool=pool)
    assert evento.tipo == EventoPool.Tipo.CANTIDAD
    assert evento.actor == otro
    assert evento.datos == {"antes": 3, "despues": 6}


def test_mi_membresia_sin_cambios_no_registra(api_client, otro, pool):
    """Dirty: repetir la misma cantidad no ensucia el historial."""
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, otro)

    response = api_client.patch(
        reverse("pool-mi-membresia", args=[pool.id]), {"cantidad": 3}, format="json"
    )

    assert response.status_code == 200
    assert not EventoPool.objects.filter(pool=pool).exists()


def test_DW_3_1_edicion_registra_campos_cambiados(api_client, user, pool):
    autenticar(api_client, user)

    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]),
        {"titulo": "Otro título", "descripcion": "Nueva"},
        format="json",
    )

    assert response.status_code == 200
    evento = EventoPool.objects.get(pool=pool)
    assert evento.tipo == EventoPool.Tipo.EDICION
    assert evento.actor == user
    assert evento.datos == {"campos": ["descripcion", "titulo"]}


def test_edicion_sin_cambios_no_registra(api_client, user, pool):
    """Dirty: un PATCH con los mismos valores no deja evento."""
    autenticar(api_client, user)

    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]),
        {"titulo": pool.titulo, "precio_unitario": str(pool.precio_unitario)},
        format="json",
    )

    assert response.status_code == 200
    assert not EventoPool.objects.filter(pool=pool).exists()


def test_DW_3_1_confirmar_registra_evento_estado(api_client, user, pool):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)

    response = api_client.post(reverse("pool-confirmar", args=[pool.id]))

    assert response.status_code == 200
    evento = EventoPool.objects.get(pool=pool)
    assert evento.tipo == EventoPool.Tipo.ESTADO
    assert evento.actor == user
    assert evento.datos == {"estado": "en_curso"}


def test_finalizar_y_cancelar_registran_estado(api_client, user, categoria, pool):
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)
    assert api_client.post(reverse("pool-finalizar", args=[pool.id])).status_code == 200

    cancelable = crear_pool(user, categoria, titulo="Para cancelar")
    autenticar(api_client, user)
    assert api_client.post(reverse("pool-cancelar", args=[cancelable.id])).status_code == 200

    assert EventoPool.objects.get(pool=pool).datos == {"estado": "finalizado"}
    assert EventoPool.objects.get(pool=cancelable).datos == {"estado": "cancelado"}


def test_imagenes_registran_eventos(api_client, user, pool, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    autenticar(api_client, user)
    assert subir_imagen(api_client, pool).status_code == 201
    imagen = pool.imagenes.get()
    assert (
        api_client.delete(
            reverse("pool-borrar-imagen", args=[pool.id, imagen.id])
        ).status_code
        == 204
    )

    eventos = eventos_de(pool)
    assert [e.tipo for e in eventos] == [EventoPool.Tipo.IMAGEN, EventoPool.Tipo.IMAGEN]
    assert [e.datos["accion"] for e in eventos] == ["agregada", "eliminada"]
    assert all(e.actor == user for e in eventos)


def test_DW_3_2_expiracion_registra_evento_sin_actor(user, categoria):
    pool = crear_pool_vencido(user, categoria)

    expirar_vencidos()

    evento = EventoPool.objects.get(pool=pool)
    assert evento.tipo == EventoPool.Tipo.EXPIRADO
    assert evento.actor is None
    assert evento.datos == {}


def test_DW_3_2_expiracion_por_lectura_registra_una_vez(api_client, user, categoria):
    """La cancelación perezosa (cada lectura) deja un solo evento, no uno por request."""
    pool = crear_pool_vencido(user, categoria)
    autenticar(api_client, user)

    assert api_client.get(reverse("pool-detail", args=[pool.id])).status_code == 200
    assert api_client.get(reverse("pool-list")).status_code == 200

    assert EventoPool.objects.filter(pool=pool, tipo=EventoPool.Tipo.EXPIRADO).count() == 1


def test_DW_3_2_solicitud_registra_actor_creador(api_client, user, categoria, pool):
    crear_miembro(pool, 0)
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)

    response = api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    assert response.status_code == 201
    evento = EventoPool.objects.get(pool=pool)
    assert evento.tipo == EventoPool.Tipo.SOLICITUD_ELIMINACION
    assert evento.actor == user


def test_DW_3_2_voto_registra_actor_miembro(api_client, user, categoria, pool):
    miembro = crear_miembro(pool, 0)
    crear_miembro(pool, 1)
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)
    api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    autenticar(api_client, miembro)
    response = api_client.post(
        reverse("pool-eliminacion-voto", args=[pool.id]), {"acepta": True}, format="json"
    )

    assert response.status_code == 200
    evento = EventoPool.objects.get(pool=pool, tipo=EventoPool.Tipo.VOTO_ELIMINACION)
    assert evento.actor == miembro
    assert evento.datos == {"acepta": True}


def test_voto_que_rechaza_registra_evento(api_client, user, categoria, pool):
    """Dirty: un rechazo deja el pool en pie y el voto queda en el historial."""
    miembro = crear_miembro(pool, 0)
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)
    api_client.post(reverse("pool-eliminacion", args=[pool.id]))

    autenticar(api_client, miembro)
    response = api_client.post(
        reverse("pool-eliminacion-voto", args=[pool.id]), {"acepta": False}, format="json"
    )

    assert response.data["estado"] == "rechazada"
    evento = EventoPool.objects.get(pool=pool, tipo=EventoPool.Tipo.VOTO_ELIMINACION)
    assert evento.datos == {"acepta": False}


def test_eventos_se_borran_con_el_pool(api_client, user, categoria):
    autenticar(api_client, user)
    creado = api_client.post(reverse("pool-list"), payload(categoria), format="json")
    pool_id = creado.data["id"]
    assert EventoPool.objects.filter(pool_id=pool_id).exists()

    assert api_client.delete(reverse("pool-detail", args=[pool_id])).status_code == 204

    assert not EventoPool.objects.filter(pool_id=pool_id).exists()


def test_DW_3_3_creador_ve_historial(api_client, user, categoria):
    autenticar(api_client, user)
    pool_id = api_client.post(reverse("pool-list"), payload(categoria), format="json").data["id"]

    response = api_client.get(reverse("pool-historial", args=[pool_id]))

    assert response.status_code == 200
    assert response.data["count"] == 1
    evento = response.data["results"][0]
    assert set(evento.keys()) == {"tipo", "actor", "datos", "creado"}
    assert evento["tipo"] == "creado"
    assert evento["actor"]["username"] == "a"
    assert evento["datos"] == {}


def test_DW_3_3_miembro_ve_historial(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    EventoPool.objects.create(pool=pool, tipo=EventoPool.Tipo.CREADO, actor=pool.creador)
    autenticar(api_client, otro)

    response = api_client.get(reverse("pool-historial", args=[pool.id]))

    assert response.status_code == 200
    assert [e["tipo"] for e in response.data["results"]] == ["creado"]


def test_DW_3_3_no_integrante_403(api_client, otro, pool):
    autenticar(api_client, otro)

    response = api_client.get(reverse("pool-historial", args=[pool.id]))

    assert response.status_code == 403


def test_DW_3_3_anonimo_401(api_client, pool):
    response = api_client.get(reverse("pool-historial", args=[pool.id]))

    assert response.status_code == 401


def test_DW_3_3_pool_inexistente_404(api_client, user):
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-historial", args=[99999]))

    assert response.status_code == 404


def test_historial_vacio_pool_previo(api_client, user, pool):
    """Dirty: los pools anteriores a la feature no tienen eventos; el estado es vacío."""
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-historial", args=[pool.id]))

    assert response.status_code == 200
    assert response.data["results"] == []
    assert response.data["count"] == 0


def test_DW_3_3_historial_paginado(api_client, user, pool):
    """Dirty: 14 eventos → 12 en la página 1 (con next) y 2 en la 2; más nuevo primero."""
    for n in range(14):
        EventoPool.objects.create(pool=pool, tipo=EventoPool.Tipo.EDICION, datos={"n": n})
    autenticar(api_client, user)

    primera = api_client.get(reverse("pool-historial", args=[pool.id]))

    assert primera.status_code == 200
    assert primera.data["count"] == 14
    assert len(primera.data["results"]) == 12
    assert primera.data["next"] is not None
    assert primera.data["results"][0]["datos"] == {"n": 13}

    segunda = api_client.get(reverse("pool-historial", args=[pool.id]), {"page": 2})

    assert len(segunda.data["results"]) == 2
    assert segunda.data["next"] is None
    assert segunda.data["results"][-1]["datos"] == {"n": 0}


def test_DW_3_2_historial_muestra_evento_de_sistema(api_client, user, categoria):
    """El actor del sistema viaja como null en el contrato."""
    pool = crear_pool_vencido(user, categoria)
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-historial", args=[pool.id]))

    assert response.status_code == 200
    evento = response.data["results"][0]
    assert evento["tipo"] == "expirado"
    assert evento["actor"] is None


def test_actor_desactivado_conserva_su_nombre(api_client, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    autenticar(api_client, otro)
    api_client.patch(
        reverse("pool-mi-membresia", args=[pool.id]), {"cantidad": 2}, format="json"
    )
    otro.is_active = False
    otro.save(update_fields=["is_active"])

    autenticar(api_client, user)
    response = api_client.get(reverse("pool-historial", args=[pool.id]))

    assert response.status_code == 200
    assert response.data["results"][0]["actor"]["username"] == "b"


# --- Chat (Fase 4) ---


def crear_mensaje(pool, autor, texto="Hola", **overrides):
    datos = {"pool": pool, "autor": autor, "texto": texto}
    datos.update(overrides)
    return Mensaje.objects.create(**datos)


def test_DW_4_1_chat_miembro_envia_y_lee(api_client, otro, pool):
    poner_estado(pool, Pool.Estado.LISTO)
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    autenticar(api_client, otro)
    url = reverse("pool-mensajes", args=[pool.id])

    creado = api_client.post(url, {"texto": "  Hola a todos  "}, format="json")

    assert creado.status_code == 201
    assert set(creado.data) == {"id", "autor", "texto", "creado"}
    assert creado.data["texto"] == "Hola a todos"
    assert creado.data["autor"]["username"] == "b"

    leido = api_client.get(url)

    assert leido.status_code == 200
    assert leido.data["hay_mas"] is False
    assert [m["texto"] for m in leido.data["results"]] == ["Hola a todos"]
    assert leido.data["results"][0]["id"] == creado.data["id"]
    assert leido.data["results"][0]["autor"]["id"] == otro.id


def test_DW_4_1_chat_creador_escribe_y_lee(api_client, user, otro, pool):
    """El creador participa del chat sin tener Membership."""
    poner_estado(pool, Pool.Estado.LISTO)
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    autenticar(api_client, user)
    url = reverse("pool-mensajes", args=[pool.id])

    assert api_client.post(url, {"texto": "Hola"}, format="json").status_code == 201

    autenticar(api_client, otro)
    leido = api_client.get(url)

    assert [m["texto"] for m in leido.data["results"]] == ["Hola"]


def test_DW_4_1_chat_no_integrante_403_get_y_post(api_client, otro, pool):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, otro)
    url = reverse("pool-mensajes", args=[pool.id])

    leido = api_client.get(url)
    enviado = api_client.post(url, {"texto": "Hola"}, format="json")

    assert leido.status_code == 403
    assert leido.data == {"detail": "Solo los integrantes pueden acceder al chat."}
    assert enviado.status_code == 403
    assert not Mensaje.objects.exists()


def test_DW_4_1_chat_anonimo_401(api_client, pool):
    url = reverse("pool-mensajes", args=[pool.id])

    assert api_client.get(url).status_code == 401
    assert api_client.post(url, {"texto": "Hola"}, format="json").status_code == 401


def test_DW_4_1_chat_pool_inexistente_404(api_client, user):
    autenticar(api_client, user)
    url = reverse("pool-mensajes", args=[99999])

    assert api_client.get(url).status_code == 404
    assert api_client.post(url, {"texto": "Hola"}, format="json").status_code == 404


def test_DW_4_2_chat_desde_devuelve_solo_lo_nuevo(api_client, user, pool):
    crear_mensaje(pool, user, "uno")
    segundo = crear_mensaje(pool, user, "dos")
    tercero = crear_mensaje(pool, user, "tres")
    autenticar(api_client, user)

    response = api_client.get(
        reverse("pool-mensajes", args=[pool.id]), {"desde": segundo.id}
    )

    assert response.status_code == 200
    assert [m["id"] for m in response.data["results"]] == [tercero.id]
    assert response.data["hay_mas"] is False


def test_DW_4_2_chat_orden_ascendente(api_client, user, pool):
    ids = [crear_mensaje(pool, user, f"m{n}").id for n in range(4)]
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-mensajes", args=[pool.id]))

    assert [m["id"] for m in response.data["results"]] == ids


def test_DW_4_2_chat_limit_recorta_y_hay_mas(api_client, user, pool):
    ids = [crear_mensaje(pool, user, f"m{n}").id for n in range(3)]
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-mensajes", args=[pool.id]), {"limit": 2})

    assert [m["id"] for m in response.data["results"]] == ids[:2]
    assert response.data["hay_mas"] is True


def test_DW_4_2_chat_hay_mas_false_en_el_limite_exacto(api_client, user, pool):
    ids = [crear_mensaje(pool, user, f"m{n}").id for n in range(2)]
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-mensajes", args=[pool.id]), {"limit": 2})

    assert [m["id"] for m in response.data["results"]] == ids
    assert response.data["hay_mas"] is False


def test_DW_4_2_chat_default_50(api_client, user, pool):
    Mensaje.objects.bulk_create(
        [Mensaje(pool=pool, autor=user, texto=f"m{n}") for n in range(55)]
    )
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-mensajes", args=[pool.id]))

    assert len(response.data["results"]) == 50
    assert response.data["hay_mas"] is True


def test_DW_4_2_chat_limit_maximo_200(api_client, user, pool):
    Mensaje.objects.bulk_create(
        [Mensaje(pool=pool, autor=user, texto=f"m{n}") for n in range(205)]
    )
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-mensajes", args=[pool.id]), {"limit": 500})

    assert len(response.data["results"]) == 200
    assert response.data["hay_mas"] is True


def test_DW_4_2_chat_limit_invalido_y_clamp(api_client, user, pool):
    crear_mensaje(pool, user, "uno")
    crear_mensaje(pool, user, "dos")
    autenticar(api_client, user)
    url = reverse("pool-mensajes", args=[pool.id])

    assert len(api_client.get(url, {"limit": 0}).data["results"]) == 1
    assert len(api_client.get(url, {"limit": -5}).data["results"]) == 1
    assert len(api_client.get(url, {"limit": "abc"}).data["results"]) == 2


def test_DW_4_2_chat_desde_invalido_es_cero(api_client, user, pool):
    ids = [crear_mensaje(pool, user, f"m{n}").id for n in range(2)]
    autenticar(api_client, user)
    url = reverse("pool-mensajes", args=[pool.id])

    for desde in ("abc", "", "-3", "2.5"):
        response = api_client.get(url, {"desde": desde})
        assert [m["id"] for m in response.data["results"]] == ids, desde


def test_DW_4_2_chat_polling_con_ultimo_id(api_client, user, otro, pool):
    """Flujo de polling: `desde` = último id que vio el cliente, solo lo nuevo."""
    poner_estado(pool, Pool.Estado.LISTO)
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    crear_mensaje(pool, user, "uno")
    crear_mensaje(pool, otro, "dos")
    autenticar(api_client, user)
    url = reverse("pool-mensajes", args=[pool.id])

    primera = api_client.get(url, {"desde": 0})

    assert [m["texto"] for m in primera.data["results"]] == ["uno", "dos"]
    ultimo = primera.data["results"][-1]["id"]

    autenticar(api_client, otro)
    api_client.post(url, {"texto": "tres"}, format="json")

    segunda = api_client.get(url, {"desde": ultimo})

    assert [m["texto"] for m in segunda.data["results"]] == ["tres"]


@pytest.mark.parametrize("texto", ["", "   ", "\n\t ", None])
def test_DW_4_3_chat_texto_vacio_400_sin_persistir(api_client, user, pool, texto):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)

    response = api_client.post(
        reverse("pool-mensajes", args=[pool.id]), {"texto": texto}, format="json"
    )

    assert response.status_code == 400
    assert "texto" in response.data
    assert not Mensaje.objects.exists()


def test_DW_4_3_chat_texto_faltante_400(api_client, user, pool):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)

    response = api_client.post(reverse("pool-mensajes", args=[pool.id]), {}, format="json")

    assert response.status_code == 400
    assert response.data["texto"] == ["El texto es obligatorio."]
    assert not Mensaje.objects.exists()


def test_DW_4_3_chat_texto_mayor_a_1000_400_sin_persistir(api_client, user, pool):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)

    response = api_client.post(
        reverse("pool-mensajes", args=[pool.id]), {"texto": "a" * 1001}, format="json"
    )

    assert response.status_code == 400
    assert response.data["texto"] == ["El texto no puede superar los 1000 caracteres."]
    assert not Mensaje.objects.exists()


def test_DW_4_3_chat_texto_limite_1000_ok(api_client, user, pool):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)
    texto = "a" * 1000

    response = api_client.post(
        reverse("pool-mensajes", args=[pool.id]), {"texto": texto}, format="json"
    )

    assert response.status_code == 201
    assert Mensaje.objects.get().texto == texto


@pytest.mark.parametrize(
    ("entrada", "esperado"), [("  hola  ", "hola"), ("\n hola \t", "hola")]
)
def test_DW_4_3_chat_texto_se_normaliza(api_client, user, pool, entrada, esperado):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)

    response = api_client.post(
        reverse("pool-mensajes", args=[pool.id]), {"texto": entrada}, format="json"
    )

    assert response.status_code == 201
    assert response.data["texto"] == esperado
    assert Mensaje.objects.get().texto == esperado


@pytest.mark.parametrize(
    ("estado", "esperado"),
    [
        (Pool.Estado.ABIERTO, 400),
        (Pool.Estado.CANCELADO, 400),
        (Pool.Estado.LISTO, 201),
        (Pool.Estado.EN_CURSO, 201),
        (Pool.Estado.FINALIZADO, 201),
    ],
)
def test_DW_4_4_chat_escritura_por_estado(api_client, user, pool, estado, esperado):
    poner_estado(pool, estado)
    autenticar(api_client, user)

    response = api_client.post(
        reverse("pool-mensajes", args=[pool.id]), {"texto": "Hola"}, format="json"
    )

    assert response.status_code == esperado
    assert Mensaje.objects.count() == (1 if esperado == 201 else 0)


def test_DW_4_4_chat_error_de_estado_es_ar(api_client, user, pool):
    poner_estado(pool, Pool.Estado.CANCELADO)
    autenticar(api_client, user)

    response = api_client.post(
        reverse("pool-mensajes", args=[pool.id]), {"texto": "Hola"}, format="json"
    )

    assert response.status_code == 400
    assert response.data == ["No se pueden enviar mensajes en el estado 'cancelado'."]


@pytest.mark.parametrize("estado", [e.value for e in Pool.Estado])
def test_DW_4_4_chat_lectura_permitida_en_todos_los_estados(api_client, user, pool, estado):
    crear_mensaje(pool, user, "previo")
    poner_estado(pool, estado)
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-mensajes", args=[pool.id]))

    assert response.status_code == 200
    assert [m["texto"] for m in response.data["results"]] == ["previo"]


def test_chat_mensajes_de_otro_pool_no_se_mezclan(api_client, user, otro, categoria, pool):
    """Integrante del pool A: no lee ni escribe el chat del pool B."""
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    otro_pool = crear_pool(user, categoria, titulo="Otro")
    crear_mensaje(otro_pool, user, "secreto")
    autenticar(api_client, otro)
    url_ajeno = reverse("pool-mensajes", args=[otro_pool.id])

    assert api_client.get(url_ajeno).status_code == 403
    assert api_client.post(url_ajeno, {"texto": "Hola"}, format="json").status_code == 403

    propio = api_client.get(reverse("pool-mensajes", args=[pool.id]))
    assert propio.status_code == 200
    assert propio.data["results"] == []


def test_chat_autor_desactivado_sigue_visible(api_client, user, otro, pool):
    crear_mensaje(pool, otro, "hola")
    otro.is_active = False
    otro.save(update_fields=["is_active"])
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-mensajes", args=[pool.id]))

    assert response.status_code == 200
    assert response.data["results"][0]["autor"]["username"] == "b"


def test_chat_mensajes_se_borran_con_el_pool(api_client, user, pool):
    crear_mensaje(pool, user, "hola")
    autenticar(api_client, user)

    assert api_client.delete(reverse("pool-detail", args=[pool.id])).status_code == 204

    assert not Mensaje.objects.exists()


def test_chat_respuesta_listado_tiene_solo_results_y_hay_mas(api_client, user, pool):
    """Contrato que consume la UI de la Fase 5."""
    crear_mensaje(pool, user, "hola")
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-mensajes", args=[pool.id]))

    assert set(response.data) == {"results", "hay_mas"}
    assert set(response.data["results"][0]) == {"id", "autor", "texto", "creado"}
    assert {"id", "username", "foto"} <= set(response.data["results"][0]["autor"])


def test_chat_post_ignora_autor_e_id_del_body(api_client, otro, user, pool):
    """`autor` e `id` son read-only: no se pueden falsificar desde el body."""
    poner_estado(pool, Pool.Estado.LISTO)
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    autenticar(api_client, otro)

    response = api_client.post(
        reverse("pool-mensajes", args=[pool.id]),
        {"texto": "Hola", "autor": user.id, "id": 999},
        format="json",
    )

    assert response.status_code == 201
    assert Mensaje.objects.get().autor_id == otro.id


def test_chat_listado_sin_n_mas_uno(api_client, user, otro, pool):
    """El listado no hace una query por autor (select_related)."""
    crear_mensaje(pool, user, "uno")
    autenticar(api_client, user)
    url = reverse("pool-mensajes", args=[pool.id])

    with CaptureQueriesContext(connection) as primera:
        assert api_client.get(url).status_code == 200

    for n in range(5):
        crear_mensaje(pool, otro, f"m{n}")
    with CaptureQueriesContext(connection) as segunda:
        assert api_client.get(url).status_code == 200

    assert len(segunda) == len(primera)


