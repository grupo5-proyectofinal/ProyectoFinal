"""Tests del endpoint de ciudades disponibles por pestaña."""
# ruff: noqa: F811 — los fixtures importados de tests.py se reciben como parámetros

import pytest
from django.urls import reverse

from .models import Membership, Pool
from .tests import (  # noqa: F401 — fixtures compartidos
    TELEFONO,
    api_client,
    autenticar,
    categoria,
    crear_pool,
    otro,
    poner_estado,
    user,
)


@pytest.mark.django_db
def test_ciudades_todos_publico_excluye_borradores_y_finalizados(api_client, user, categoria):
    crear_pool(user, categoria, ciudad="Rosario")
    poner_estado(crear_pool(user, categoria, ciudad="Mendoza"), Pool.Estado.BORRADOR)
    poner_estado(crear_pool(user, categoria, ciudad="Salta"), Pool.Estado.FINALIZADO)

    resp = api_client.get(reverse("pool-ciudades"))
    assert resp.status_code == 200
    assert resp.json() == ["Rosario"]


@pytest.mark.django_db
def test_ciudades_todos_excluye_propios_y_unidos_si_autenticado(
    api_client, user, otro, categoria
):
    crear_pool(user, categoria, ciudad="Mendoza")
    pool_unido = crear_pool(otro, categoria, ciudad="Tucumán")
    Membership.objects.create(pool=pool_unido, usuario=user, cantidad=1, telefono=TELEFONO)
    crear_pool(otro, categoria, ciudad="Rosario")

    autenticar(api_client, user)
    resp = api_client.get(reverse("pool-ciudades"), {"tab": "todos"})
    assert resp.status_code == 200
    assert resp.json() == ["Rosario"]


@pytest.mark.django_db
def test_ciudades_deduplica_normaliza_espacios_y_ordena(api_client, user, categoria):
    for ciudad in (
        "  rosario ",
        "Rosario",
        "Corrientes",
        "Córdoba",
        "  Buenos   Aires ",
        "buenos aires",
        "   ",
        "",
    ):
        crear_pool(user, categoria, ciudad=ciudad)

    resp = api_client.get(reverse("pool-ciudades"))
    assert resp.status_code == 200
    assert resp.json() == ["Buenos Aires", "Córdoba", "Corrientes", "Rosario"]


@pytest.mark.django_db
def test_ciudades_respuesta_vacia(api_client):
    resp = api_client.get(reverse("pool-ciudades"))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_ciudades_tab_mios_autenticado_y_anonimo(api_client, user, otro, categoria):
    poner_estado(crear_pool(user, categoria, ciudad="Neuquén"), Pool.Estado.BORRADOR)
    crear_pool(user, categoria, ciudad="Bariloche")
    crear_pool(otro, categoria, ciudad="Rosario")

    resp_anon = api_client.get(reverse("pool-ciudades"), {"tab": "mios"})
    assert resp_anon.status_code == 200
    assert resp_anon.json() == []

    autenticar(api_client, user)
    resp_auth = api_client.get(reverse("pool-ciudades"), {"tab": "mios"})
    assert resp_auth.status_code == 200
    assert resp_auth.json() == ["Bariloche", "Neuquén"]


@pytest.mark.django_db
def test_ciudades_tab_unidos_autenticado_y_anonimo(api_client, user, otro, categoria):
    pool_unido = crear_pool(otro, categoria, ciudad="La Plata")
    Membership.objects.create(pool=pool_unido, usuario=user, cantidad=1, telefono=TELEFONO)
    crear_pool(otro, categoria, ciudad="Rosario")
    crear_pool(user, categoria, ciudad="Mendoza")

    resp_anon = api_client.get(reverse("pool-ciudades"), {"tab": "unidos"})
    assert resp_anon.status_code == 200
    assert resp_anon.json() == []

    autenticar(api_client, user)
    resp_auth = api_client.get(reverse("pool-ciudades"), {"tab": "unidos"})
    assert resp_auth.status_code == 200
    assert resp_auth.json() == ["La Plata"]
