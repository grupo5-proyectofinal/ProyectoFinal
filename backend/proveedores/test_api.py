"""Directorio de mayoristas y comparador de costo final (API)."""
# ruff: noqa: F811 — los fixtures importados de pools/tests.py se reciben como parámetros

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse

from pools import views as pool_views
from pools.models import Category, Membership
from pools.tests import (  # noqa: F401 — fixtures compartidos
    PASSWORD,
    api_client,
    autenticar,
    categoria,
    crear_pool,
    otro,
    user,
)

from .models import Comparacion, Oferta, ParametroCosto, Proveedor

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


def _csv(texto):
    return SimpleUploadedFile("mayoristas.csv", texto.encode("utf-8"), content_type="text/csv")


def test_importar_csv_crea_y_actualiza_por_dominio(api_client, staff, db):
    autenticar(api_client, staff)
    texto = (
        "nombre,sitio_url,rubros,provincia,verificado\n"
        "Textil Sur,https://textilsur.com.ar/?utm_source=x,Remera;Ropa,Salta,si\n"
        "Bebidas Ya,https://bebidasya.com,Bebidas,Córdoba,no\n"
        ",https://sin-nombre.com,Ropa,,no\n"
        "Rubro raro,https://raro.com,Rubro inexistente,,no\n"
    )

    response = api_client.post(
        reverse("proveedor-importar"), {"archivo": _csv(texto)}, format="multipart"
    )

    assert response.status_code == 200, response.data
    # Las tres filas con nombre y sitio válido se crean; la del rubro raro
    # también (solo deja una advertencia).
    assert response.data["creados"] == 3
    assert response.data["actualizados"] == 0
    assert response.data["salteados"] == 1
    assert response.data["total_errores"] == 1
    assert response.data["total_advertencias"] == 1
    textil = Proveedor.objects.get(nombre="Textil Sur")
    assert textil.estado == "aprobado"
    assert textil.verificado is True
    assert textil.sitio_url == "https://textilsur.com.ar/"
    assert set(textil.rubros.values_list("nombre", flat=True)) == {"Remera", "Ropa"}

    # Mismo dominio con www: actualiza, no duplica.
    texto2 = (
        "nombre,sitio_url,rubros,provincia,verificado\n"
        "Textil Sur actualizado,https://www.textilsur.com.ar/,Remera,Jujuy,no\n"
    )
    response2 = api_client.post(
        reverse("proveedor-importar"), {"archivo": _csv(texto2)}, format="multipart"
    )
    assert response2.status_code == 200
    assert response2.data["creados"] == 0
    assert response2.data["actualizados"] == 1
    textil.refresh_from_db()
    assert textil.nombre == "Textil Sur actualizado"
    assert textil.provincia == "Jujuy"
    assert textil.verificado is False
    assert set(textil.rubros.values_list("nombre", flat=True)) == {"Remera"}
    assert Proveedor.objects.filter(dominio="textilsur.com.ar").count() == 1


def test_importar_csv_requiere_staff(api_client, user):
    autenticar(api_client, user)
    response = api_client.post(
        reverse("proveedor-importar"),
        {"archivo": _csv("nombre,sitio_url\nX,https://x.com\n")},
        format="multipart",
    )
    assert response.status_code == 403


def test_importar_csv_valida_columnas_y_archivo(api_client, staff):
    autenticar(api_client, staff)
    sin_columnas = api_client.post(
        reverse("proveedor-importar"),
        {"archivo": _csv("nombre,provincia\nX,Salta\n")},
        format="multipart",
    )
    assert sin_columnas.status_code == 400
    assert "nombre y sitio_url" in sin_columnas.data["detail"]

    sin_archivo = api_client.post(reverse("proveedor-importar"), {}, format="multipart")
    assert sin_archivo.status_code == 400
    assert "archivo CSV" in sin_archivo.data["detail"]


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


# --- Parámetros -------------------------------------------------------------------


def test_parametros_publicos_y_solo_staff_edita(api_client, user, staff):
    claves = {p["clave"] for p in api_client.get(reverse("parametro-costo-list")).data}
    assert {"tipo_cambio_usd", "iva_importacion_pct"} <= claves
    url = reverse("parametro-costo-detail", args=["tipo_cambio_usd"])
    autenticar(api_client, user)
    assert api_client.patch(url, {"valor": "1200"}, format="json").status_code == 403
    autenticar(api_client, staff)
    assert api_client.patch(url, {"valor": "1200"}, format="json").status_code == 200
    assert ParametroCosto.objects.get(clave="tipo_cambio_usd").valor == Decimal(1200)


# --- Comparador ---------------------------------------------------------------------


def crear_comparacion(api_client, **datos):
    return api_client.post(
        reverse("comparacion-list"), {"titulo": "Yerba", "cantidad": 10, **datos}, format="json"
    )


def agregar_oferta(api_client, comparacion_id, **datos):
    base = {"comparacion": comparacion_id, "tienda": "Tienda", "precio_unitario": "100"}
    return api_client.post(reverse("oferta-list"), {**base, **datos}, format="json")


def test_comparacion_ordena_por_costo_total(api_client, user):
    autenticar(api_client, user)
    comparacion = crear_comparacion(api_client).data
    agregar_oferta(api_client, comparacion["id"], tienda="Barata con envío", precio_unitario="90", costo_envio="500")
    agregar_oferta(api_client, comparacion["id"], tienda="Cara sin envío", precio_unitario="110")
    data = api_client.get(reverse("comparacion-detail", args=[comparacion["id"]])).data
    assert [o["tienda"] for o in data["ofertas"]] == ["Cara sin envío", "Barata con envío"]
    assert data["ofertas"][0]["es_mejor"] is True
    assert data["resumen"]["ahorro"] == Decimal("300.00")
    assert data["ofertas"][0]["historial"][0]["precio"] == "110.00"


def test_importacion_sin_tipo_de_cambio_queda_sin_total(api_client, user):
    autenticar(api_client, user)
    comparacion = crear_comparacion(api_client).data
    agregar_oferta(api_client, comparacion["id"], moneda="usd", es_importacion=True)
    oferta = api_client.get(reverse("comparacion-detail", args=[comparacion["id"]])).data["ofertas"][0]
    assert oferta["moneda"] == "USD"
    assert oferta["costo"]["total"] is None
    assert oferta["costo"]["falta"] == "tipo_cambio"


def test_solo_el_creador_edita_y_ve_sus_comparaciones(api_client, user, otro):
    autenticar(api_client, user)
    comparacion = crear_comparacion(api_client).data
    autenticar(api_client, otro)
    assert api_client.get(reverse("comparacion-detail", args=[comparacion["id"]])).status_code == 404
    assert agregar_oferta(api_client, comparacion["id"]).status_code == 400
    assert api_client.get(reverse("comparacion-list")).data == []


def test_comparacion_del_pool_la_ven_los_integrantes(api_client, user, otro, categoria):
    pool = crear_pool(user, categoria)
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    autenticar(api_client, user)
    comparacion = crear_comparacion(api_client, pool=pool.id).data
    agregar_oferta(api_client, comparacion["id"])
    assert crear_comparacion(api_client, pool=pool.id).status_code == 400  # una por pool

    autenticar(api_client, otro)
    data = api_client.get(reverse("comparacion-de-pool", args=[pool.id])).data
    assert data["puede_editar"] is False and len(data["ofertas"]) == 1
    assert api_client.patch(
        reverse("comparacion-detail", args=[comparacion["id"]]), {"titulo": "x"}, format="json"
    ).status_code == 403
    assert crear_comparacion(api_client, pool=pool.id).status_code == 400  # no es el creador


def test_maximo_de_ofertas(api_client, user):
    autenticar(api_client, user)
    comparacion = crear_comparacion(api_client).data
    for i in range(10):
        assert agregar_oferta(api_client, comparacion["id"], tienda=f"T{i}").status_code == 201
    assert agregar_oferta(api_client, comparacion["id"], tienda="T11").status_code == 400


def test_cambiar_precio_guarda_historial(api_client, user):
    autenticar(api_client, user)
    comparacion = crear_comparacion(api_client).data
    oferta = agregar_oferta(api_client, comparacion["id"]).data
    api_client.patch(reverse("oferta-detail", args=[oferta["id"]]), {"precio_unitario": "95"}, format="json")
    api_client.patch(reverse("oferta-detail", args=[oferta["id"]]), {"notas": "sin cambio"}, format="json")
    assert list(Oferta.objects.get(pk=oferta["id"]).historial.values_list("precio", flat=True)) == [
        Decimal("100.00"),
        Decimal("95.00"),
    ]


def test_actualizar_precios_desde_el_enlace(api_client, user, monkeypatch):
    from . import views

    autenticar(api_client, user)
    comparacion = crear_comparacion(api_client).data
    agregar_oferta(api_client, comparacion["id"], url="https://tienda.com/p")
    agregar_oferta(api_client, comparacion["id"], tienda="Sin link")
    monkeypatch.setattr(
        views,
        "leer_enlace",
        lambda url: {"datos": {"precio_unitario": "88.00", "moneda": "ARS"}, "motivo": None, "aviso": None},
    )
    response = api_client.post(reverse("comparacion-actualizar-precios", args=[comparacion["id"]]))
    assert response.data["actualizadas"] == 1
    assert Oferta.objects.get(url="https://tienda.com/p").precio_unitario == Decimal("88.00")
    assert Comparacion.objects.get(pk=comparacion["id"]).ofertas.get(url="https://tienda.com/p").historial.count() == 2



# --- Regresiones de la revisión de la Fase 3 ---------------------------------------


def test_directorio_y_comparaciones_sin_paginar(api_client, user):
    # La UI no pagina: con más de 12 el resto quedaba inaccesible.
    for i in range(14):
        proveedor(nombre=f"M{i:02d}", sitio_url=f"https://m{i}.com.ar")
    assert len(api_client.get(reverse("proveedor-list")).data) == 14
    autenticar(api_client, user)
    for i in range(13):
        crear_comparacion(api_client, titulo=f"C{i}")
    listado = api_client.get(reverse("comparacion-list")).data
    assert len(listado) == 13
    assert listado[0]["cantidad_ofertas"] == 0 and listado[0]["ofertas"] is None


def test_actualizar_precios_de_una_importacion(api_client, user, monkeypatch):
    from . import views

    autenticar(api_client, user)
    comparacion = crear_comparacion(api_client).data
    agregar_oferta(api_client, comparacion["id"], url="https://www.amazon.com/dp/X", moneda="USD", precio_unitario="40")
    monkeypatch.setattr(
        views,
        "leer_enlace",
        lambda url: {
            "datos": {"precio_unitario": None, "precio_moneda": "35.50", "moneda": "USD"},
            "motivo": None,
            "aviso": "…",
        },
    )
    response = api_client.post(reverse("comparacion-actualizar-precios", args=[comparacion["id"]]))
    assert response.data["actualizadas"] == 1
    assert Oferta.objects.get(url="https://www.amazon.com/dp/X").precio_unitario == Decimal("35.50")


def test_historial_trae_los_ultimos_puntos_en_orden(api_client, user):
    from .models import PrecioHistorico

    autenticar(api_client, user)
    comparacion = crear_comparacion(api_client).data
    oferta = agregar_oferta(api_client, comparacion["id"]).data
    for precio in range(101, 116):
        PrecioHistorico.objects.create(oferta_id=oferta["id"], precio=precio)
    historial = api_client.get(reverse("comparacion-detail", args=[comparacion["id"]])).data["ofertas"][0][
        "historial"
    ]
    assert len(historial) == 12
    precios = [h["precio"] for h in historial]
    assert (precios[0], precios[-1]) == ("104.00", "115.00")
