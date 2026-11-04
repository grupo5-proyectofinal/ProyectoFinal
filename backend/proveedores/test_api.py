"""Directorio de mayoristas (API)."""
# ruff: noqa: F811 — los fixtures importados de pools/tests.py se reciben como parámetros


import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from pools import views as pool_views
from pools.models import Category
from pools.tests import (  # noqa: F401 — fixtures compartidos
    PASSWORD,
    api_client,
    autenticar,
    categoria,
    crear_pool,
    otro,
    user,
)

from .models import Proveedor

User = get_user_model()


@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    monkeypatch.setattr(pool_views, "geocodificar", lambda direccion, ciudad: None)


@pytest.fixture
def staff(db):
    return User.objects.create_user(
        email="staff@example.com", username="staff", dni="40111222", password=PASSWORD, is_staff=True
    )


def proveedor(**datos):
    base = {"nombre": "Mayorista Uno", "sitio_url": "https://mayorista-uno.com.ar", "estado": "aprobado"}
    return Proveedor.objects.create(**{**base, **datos})


# --- Directorio -----------------------------------------------------------------


def test_publico_ve_solo_aprobados_y_filtra(api_client, db):
    ropa = Category.objects.get(nombre="Ropa")
    remera = Category.objects.get(nombre="Remera")
    a = proveedor(nombre="Textil Norte", sitio_url="https://textilnorte.com.ar", provincia="Salta")
    a.rubros.add(remera)
    proveedor(nombre="Pendiente SA", sitio_url="https://pendiente.com", estado="pendiente")
    proveedor(nombre="Bebidas Ya", sitio_url="https://bebidasya.com")

    nombres = lambda r: [p["nombre"] for p in r.data]
    assert sorted(nombres(api_client.get(reverse("proveedor-list")))) == ["Bebidas Ya", "Textil Norte"]
    # Filtrar por el rubro principal incluye a quien cargó la subcategoría.
    assert nombres(api_client.get(reverse("proveedor-list"), {"rubro": ropa.id})) == ["Textil Norte"]
    assert nombres(api_client.get(reverse("proveedor-list"), {"provincia": "salta"})) == ["Textil Norte"]
    assert nombres(api_client.get(reverse("proveedor-list"), {"q": "bebidas"})) == ["Bebidas Ya"]


def test_sugerir_queda_pendiente_y_sin_verificar(api_client, user):
    autenticar(api_client, user)
    response = api_client.post(
        reverse("proveedor-list"),
        {"nombre": "Nuevo", "sitio_url": "https://nuevo.com/?utm_source=x", "verificado": True},
        format="json",
    )
    assert response.status_code == 201, response.data
    creado = Proveedor.objects.get(nombre="Nuevo")
    assert creado.estado == "pendiente"
    assert creado.verificado is False
    assert creado.sugerido_por == user
    assert creado.sitio_url == "https://nuevo.com/"
    # El público no lo ve hasta que lo aprueban.
    api_client.force_authenticate(None)
    api_client.credentials()
    assert api_client.get(reverse("proveedor-list")).data == []


def test_sitio_repetido_no_se_duplica(api_client, user):
    proveedor(sitio_url="https://www.repetido.com")
    autenticar(api_client, user)
    response = api_client.post(
        reverse("proveedor-list"), {"nombre": "Otro", "sitio_url": "https://repetido.com/tienda"}, format="json"
    )
    assert response.status_code == 400
    assert "ya está en el directorio" in str(response.data["sitio_url"])


def test_staff_aprueba_rechaza_y_edita(api_client, staff, user):
    pendiente = proveedor(estado="pendiente")
    autenticar(api_client, user)
    assert api_client.post(reverse("proveedor-aprobar", args=[pendiente.id])).status_code == 403
    autenticar(api_client, staff)
    assert api_client.post(reverse("proveedor-aprobar", args=[pendiente.id])).status_code == 200
    pendiente.refresh_from_db()
    assert pendiente.estado == "aprobado"
    response = api_client.patch(
        reverse("proveedor-detail", args=[pendiente.id]), {"verificado": True}, format="json"
    )
    assert response.status_code == 200
    assert api_client.get(reverse("proveedor-list"), {"estado": "pendiente"}).data == []


def test_detalle_con_analisis_y_pools_del_sitio(api_client, user, categoria):
    p = proveedor(sitio_url="https://mayorista-uno.com.ar")
    crear_pool(user, categoria, titulo="Del sitio", enlace="https://www.mayorista-uno.com.ar/p/1")
    crear_pool(user, categoria, titulo="Impostor", enlace="https://mayorista-uno.com.ar.evil.com/p")
    data = api_client.get(reverse("proveedor-detail", args=[p.id])).data
    assert data["analisis"]["nivel"] in {"alto", "medio", "bajo"}
    assert data["pools_total"] == 1
    assert [x["titulo"] for x in data["pools_activos"]] == ["Del sitio"]


def test_importar_mayoristas_desde_csv(tmp_path, db):
    archivo = tmp_path / "mayoristas.csv"
    archivo.write_text(
        "nombre,sitio_url,rubros,provincia,ciudad,compra_minima,envio,medios_pago,verificado\n"
        "Textil Norte,https://textilnorte.com.ar,Ropa;Remera,Salta,Salta,12 prendas,A todo el país,Transferencia,si\n"
        "Sin URL,,Ropa,,,,,,no\n",
        encoding="utf-8",
    )
    call_command("importar_mayoristas", str(archivo))
    textil = Proveedor.objects.get(nombre="Textil Norte")
    assert textil.estado == "aprobado" and textil.verificado
    assert sorted(textil.rubros.values_list("nombre", flat=True)) == ["Remera", "Ropa"]
    assert not Proveedor.objects.filter(nombre="Sin URL").exists()
    # Idempotente: volver a importar actualiza, no duplica.
    call_command("importar_mayoristas", str(archivo))
    assert Proveedor.objects.filter(dominio="textilnorte.com.ar").count() == 1


def test_directorio_sin_paginar(api_client, db):
    # La UI no pagina: con más de 12 el resto quedaba inaccesible.
    for i in range(14):
        proveedor(nombre=f"M{i:02d}", sitio_url=f"https://m{i}.com.ar")
    assert len(api_client.get(reverse("proveedor-list")).data) == 14
