import importlib
import json
import logging
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from urllib.error import URLError

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connections
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from . import geocoding, views
from .models import (
    Category,
    Membership,
    Pool,
    PoolImage,
    SolicitudEliminacion,
    expirar_vencidos,
)

User = get_user_model()

PASSWORD = "Zq7!mN2pLxD"

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


def test_categorias_sembradas(db):
    nombres = set(Category.objects.values_list("nombre", flat=True))
    assert {"Bebidas", "Limpieza", "Hogar", "Electrónica", "Otros", "Higiene personal"} <= nombres
    assert "Alimentos" not in nombres


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


def test_delete_creador_ok(api_client, user, pool):
    autenticar(api_client, user)
    response = api_client.delete(reverse("pool-detail", args=[pool.id]))
    assert response.status_code == 204
    assert not Pool.objects.filter(pk=pool.pk).exists()


def test_delete_no_abierto_400(api_client, user, pool):
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)
    response = api_client.delete(reverse("pool-detail", args=[pool.id]))
    assert response.status_code == 400


# --- Unirse ---


def test_unirse_ok(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 3}, format="json"
    )
    assert response.status_code == 201
    assert Membership.objects.filter(pool=pool, usuario=otro, cantidad=3).exists()


def test_unirse_baja_disponible(api_client, otro, pool):
    autenticar(api_client, otro)
    api_client.post(reverse("pool-unirse", args=[pool.id]), {"cantidad": 3}, format="json")
    pool.refresh_from_db()
    assert pool.disponible == 5


def test_unirse_sobre_disponible_400(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 9}, format="json"
    )
    assert response.status_code == 400
    assert "cantidad" in response.data


def test_unirse_bajo_minimo_400(api_client, otro, categoria, user):
    pool = crear_pool(user, categoria, min_por_integrante=5)
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 2}, format="json"
    )
    assert response.status_code == 400
    assert "cantidad" in response.data


def test_unirse_creador_400(api_client, user, pool):
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1}, format="json"
    )
    assert response.status_code == 400


def test_unirse_duplicado_400(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1}, format="json"
    )
    assert response.status_code == 400


def test_unirse_no_abierto_400(api_client, otro, pool):
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1}, format="json"
    )
    assert response.status_code == 400


def test_unirse_llena_cambia_a_listo(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 8}, format="json"
    )
    assert response.status_code == 201
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.LISTO


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
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1}, format="json"
    )
    assert response.status_code == 201


def test_DW_3_2_unirse_a_vencido_400_sin_consumir_disponible(api_client, user, otro, categoria):
    pool = crear_pool_vencido(user, categoria)
    autenticar(api_client, otro)

    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1}, format="json"
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
    assert "q=Av.+Corrientes+1234%2C+CABA" in pedido.full_url
    assert "format=json" in pedido.full_url
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
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1}, format="json"
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


