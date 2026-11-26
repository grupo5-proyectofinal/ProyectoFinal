from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Category, Membership, Pool

User = get_user_model()
PASSWORD = "Zq7!mN2pLxD"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def categoria():
    return Category.objects.create(nombre="Alimentos", slug="alimentos")


def _crear_usuario(username):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=PASSWORD,
    )


def _crear_pool(usuario, categoria, ciudad, estado=Pool.Estado.ABIERTO):
    return Pool.objects.create(
        creador=usuario,
        categoria=categoria,
        titulo=f"Pool en {ciudad or 'sin ciudad'}",
        nombre_producto="Producto",
        precio_unitario="100.00",
        cantidad_total=10,
        cantidad_creador=2,
        fecha_caducidad=timezone.localdate() + timedelta(days=7),
        direccion="Calle 1",
        ciudad=ciudad,
        estado=estado,
    )


@pytest.mark.django_db
def test_ciudades_todos_publico_excluye_borradores_y_finalizados(api_client, categoria):
    creador = _crear_usuario("creador")
    _crear_pool(creador, categoria, "Rosario", estado=Pool.Estado.ABIERTO)
    _crear_pool(creador, categoria, "Mendoza", estado=Pool.Estado.BORRADOR)
    _crear_pool(creador, categoria, "Salta", estado=Pool.Estado.FINALIZADO)

    resp = api_client.get(reverse("pool-ciudades"))
    assert resp.status_code == 200
    assert resp.json() == ["Rosario"]


@pytest.mark.django_db
def test_ciudades_todos_excluye_propios_y_unidos_si_autenticado(api_client, categoria):
    yo = _crear_usuario("yo")
    otro = _crear_usuario("otro")
    _crear_pool(yo, categoria, "Mendoza")
    pool_unido = _crear_pool(otro, categoria, "Tucumán")
    Membership.objects.create(pool=pool_unido, usuario=yo, cantidad=1, telefono="3515551234")
    _crear_pool(otro, categoria, "Rosario")

    api_client.force_authenticate(yo)
    resp = api_client.get(reverse("pool-ciudades"), {"tab": "todos"})
    assert resp.status_code == 200
    assert resp.json() == ["Rosario"]


@pytest.mark.django_db
def test_ciudades_deduplica_normaliza_espacios_y_ordena(api_client, categoria):
    creador = _crear_usuario("creador")
    _crear_pool(creador, categoria, "  rosario ")
    _crear_pool(creador, categoria, "Rosario")
    _crear_pool(creador, categoria, "Corrientes")
    _crear_pool(creador, categoria, "Córdoba")
    _crear_pool(creador, categoria, "  Buenos   Aires ")
    _crear_pool(creador, categoria, "buenos aires")
    _crear_pool(creador, categoria, "   ")
    _crear_pool(creador, categoria, "")

    resp = api_client.get(reverse("pool-ciudades"))
    assert resp.status_code == 200
    assert resp.json() == ["Buenos Aires", "Córdoba", "Corrientes", "Rosario"]


@pytest.mark.django_db
def test_ciudades_respuesta_vacia(api_client):
    resp = api_client.get(reverse("pool-ciudades"))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_ciudades_tab_mios_autenticado_y_anonimo(api_client, categoria):
    yo = _crear_usuario("yo")
    otro = _crear_usuario("otro")
    _crear_pool(yo, categoria, "Neuquén", estado=Pool.Estado.BORRADOR)
    _crear_pool(yo, categoria, "Bariloche", estado=Pool.Estado.ABIERTO)
    _crear_pool(otro, categoria, "Rosario", estado=Pool.Estado.ABIERTO)

    resp_anon = api_client.get(reverse("pool-ciudades"), {"tab": "mios"})
    assert resp_anon.status_code == 200
    assert resp_anon.json() == []

    api_client.force_authenticate(yo)
    resp_auth = api_client.get(reverse("pool-ciudades"), {"tab": "mios"})
    assert resp_auth.status_code == 200
    assert resp_auth.json() == ["Bariloche", "Neuquén"]


@pytest.mark.django_db
def test_ciudades_tab_unidos_autenticado_y_anonimo(api_client, categoria):
    yo = _crear_usuario("yo")
    otro = _crear_usuario("otro")
    pool_unido = _crear_pool(otro, categoria, "La Plata")
    Membership.objects.create(pool=pool_unido, usuario=yo, cantidad=1, telefono="3515551234")
    _crear_pool(otro, categoria, "Rosario")
    _crear_pool(yo, categoria, "Mendoza")

    resp_anon = api_client.get(reverse("pool-ciudades"), {"tab": "unidos"})
    assert resp_anon.status_code == 200
    assert resp_anon.json() == []

    api_client.force_authenticate(yo)
    resp_auth = api_client.get(reverse("pool-ciudades"), {"tab": "unidos"})
    assert resp_auth.status_code == 200
    assert resp_auth.json() == ["La Plata"]
