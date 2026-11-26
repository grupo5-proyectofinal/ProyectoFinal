"""Edición de reserva del creador (`cantidad_creador`) y publicación desde borrador."""
# ruff: noqa: F811 — los fixtures importados de tests.py se reciben como parámetros

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from .models import Membership, Pool
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


def crear_borrador(api_client, user, categoria, **overrides):
    """Crea un pool en estado borrador usando la API."""
    autenticar(api_client, user)
    datos = {"titulo": "Mate imperial", "categoria": categoria.id, "borrador": True}
    datos.update(overrides)
    response = api_client.post(reverse("pool-list"), datos, format="json")
    assert response.status_code == 201
    return Pool.objects.get(pk=response.data["id"])


def test_editar_cantidad_creador_en_borrador(api_client, user, categoria):
    borrador = crear_borrador(api_client, user, categoria)
    assert borrador.cantidad_creador == 1

    response = api_client.patch(
        reverse("pool-detail", args=[borrador.id]),
        {"cantidad_creador": 3, "cantidad_total": 10},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["cantidad_creador"] == 3
    assert response.data["disponible"] == 7


def test_editar_cantidad_creador_en_pool_abierto_con_y_sin_miembros(
    api_client, user, otro, categoria
):
    abierto = crear_pool(user, categoria, cantidad_total=10, cantidad_creador=2)
    autenticar(api_client, user)

    sin_miembros = api_client.patch(
        reverse("pool-detail", args=[abierto.id]),
        {"cantidad_creador": 4},
        format="json",
    )
    assert sin_miembros.status_code == 200
    assert sin_miembros.data["cantidad_creador"] == 4
    assert sin_miembros.data["disponible"] == 6

    Membership.objects.create(pool=abierto, usuario=otro, cantidad=3, telefono=TELEFONO)
    con_miembros = api_client.patch(
        reverse("pool-detail", args=[abierto.id]),
        {"cantidad_creador": 5},
        format="json",
    )
    assert con_miembros.status_code == 200
    assert con_miembros.data["cantidad_creador"] == 5
    assert con_miembros.data["disponible"] == 2


def test_guardar_cantidad_creador_mayor_que_total_400(api_client, user, categoria):
    borrador = crear_borrador(api_client, user, categoria, cantidad_total=5, cantidad_creador=1)
    response = api_client.patch(
        reverse("pool-detail", args=[borrador.id]),
        {"cantidad_creador": 6},
        format="json",
    )
    assert response.status_code == 400
    assert "cantidad_creador" in response.data


def test_publicar_borrador_con_cantidad_creador_igual_a_total_400(api_client, user, categoria):
    borrador = crear_borrador(
        api_client,
        user,
        categoria,
        nombre_producto="Mate",
        enlace="https://tienda.example/mate",
        precio_unitario="15000.00",
        cantidad_total=4,
        cantidad_creador=4,
        direccion="Av. Colón 100",
        ciudad="Córdoba",
        fecha_caducidad=(timezone.localdate() + timedelta(days=10)).isoformat(),
    )
    response = api_client.post(reverse("pool-publicar", args=[borrador.id]), {}, format="json")
    assert response.status_code == 400
    assert "cantidad_total" in response.data


def test_flujo_patch_y_publicar_borrador(api_client, user, categoria):
    borrador = crear_borrador(api_client, user, categoria)
    fecha = (timezone.localdate() + timedelta(days=15)).isoformat()

    patch_resp = api_client.patch(
        reverse("pool-detail", args=[borrador.id]),
        {
            "nombre_producto": "Mate imperial",
            "enlace": "https://tienda.example/mate",
            "precio_unitario": "12000.00",
            "precio_envio": "1500.00",
            "cantidad_total": 10,
            "cantidad_creador": 2,
            "min_por_integrante": 1,
            "fecha_caducidad": fecha,
            "tipo_pago": "sin_especificar",
            "direccion": "Av. Colón 100",
            "ciudad": "Córdoba",
        },
        format="json",
    )
    assert patch_resp.status_code == 200
    assert patch_resp.data["estado"] == Pool.Estado.BORRADOR

    pub_resp = api_client.post(reverse("pool-publicar", args=[borrador.id]), {}, format="json")
    assert pub_resp.status_code == 200
    assert pub_resp.data["estado"] == Pool.Estado.ABIERTO
    assert pub_resp.data["cantidad_creador"] == 2
    assert pub_resp.data["disponible"] == 8
