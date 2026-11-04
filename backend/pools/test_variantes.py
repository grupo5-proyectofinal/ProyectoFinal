"""Atributos por categoría (Iteración 3: "Ropa > Remera > Talle, Color")."""
# ruff: noqa: F811 — los fixtures importados de tests.py se reciben como parámetros

import json

import pytest
from django.urls import reverse

from . import views
from .models import Category, Membership
from .tests import (  # noqa: F401 — fixtures compartidos
    api_client,
    autenticar,
    crear_pool,
    otro,
    payload,
    user,
)
from .variantes import resumen

TELEFONO = "3515551234"


@pytest.fixture(autouse=True)
def sin_geocoding(monkeypatch):
    monkeypatch.setattr(views, "geocodificar", lambda direccion, ciudad: None)


@pytest.fixture
def remera(db):
    return Category.objects.get(nombre="Remera")


@pytest.fixture
def pool_remeras(user, remera):
    return crear_pool(
        user,
        remera,
        cantidad_total=10,
        cantidad_creador=1,
        atributos={"Talle": ["S", "M", "L"], "Color": ["Negro", "Blanco"]},
    )


def unirse(api_client, pool, cantidad, detalle=None):
    datos = {"cantidad": cantidad, "telefono": TELEFONO}
    if detalle is not None:
        datos["detalle"] = detalle
    return api_client.post(reverse("pool-unirse", args=[pool.id]), datos, format="json")


def fila(talle, color, cantidad):
    return {"atributos": {"Talle": talle, "Color": color}, "cantidad": cantidad}


# --- Catálogo ------------------------------------------------------------------


def test_subcategorias_heredan_atributos(api_client, db):
    categorias = {c["nombre"]: c for c in api_client.get(reverse("category-list")).data}
    ropa, remera = categorias["Ropa"], categorias["Remera"]
    assert remera["padre"] == ropa["id"]
    assert [a["nombre"] for a in remera["atributos"]] == ["Talle", "Color"]
    talle = remera["atributos"][0]
    assert talle["opciones"][:3] == ["XS", "S", "M"]
    assert categorias["Perfume"]["atributos"][0]["nombre"] == "Contenido"


def test_categorias_sin_n_mas_1(api_client, db, django_assert_max_num_queries):
    with django_assert_max_num_queries(4):
        api_client.get(reverse("category-list"))


# --- Crear pool con variantes -----------------------------------------------


def test_crear_pool_con_atributos_ordena_y_limpia(api_client, user, remera):
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-list"),
        payload(remera, atributos={"Color": ["Blanco", "Negro"], "Talle": ["L", "S"]}),
        format="json",
    )
    assert response.status_code == 201, response.data
    # Las opciones quedan en el orden de la categoría (S antes que L).
    assert response.data["atributos"] == {"Color": ["Negro", "Blanco"], "Talle": ["S", "L"]}


def test_crear_pool_multipart_con_atributos_en_texto(api_client, user, remera):
    # "Crear pool" manda FormData (por las imágenes): los atributos llegan como texto.
    autenticar(api_client, user)
    datos = payload(remera, atributos=json.dumps({"Talle": ["M"]}))
    response = api_client.post(reverse("pool-list"), datos, format="multipart")
    assert response.status_code == 201, response.data
    assert response.data["atributos"] == {"Talle": ["M"]}


@pytest.mark.parametrize(
    ("atributos", "mensaje"),
    [
        ({"Talle": ["XXXL"]}, "no es una opción"),
        ({"Sabor": ["Menta"]}, "no tiene el atributo"),
        ({"Talle": "M"}, "Elegí las opciones"),
    ],
)
def test_atributos_invalidos(api_client, user, remera, atributos, mensaje):
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-list"), payload(remera, atributos=atributos), format="json")
    assert response.status_code == 400
    assert mensaje in str(response.data["atributos"])


def test_atributos_no_se_cambian_con_miembros(api_client, user, otro, pool_remeras):
    Membership.objects.create(pool=pool_remeras, usuario=otro, cantidad=1, detalle=[fila("S", "Negro", 1)])
    autenticar(api_client, user)
    response = api_client.patch(
        reverse("pool-detail", args=[pool_remeras.id]), {"atributos": {"Talle": ["S"]}}, format="json"
    )
    assert response.status_code == 400
    assert "inmutable" in str(response.data["atributos"])


# --- Unirse eligiendo variantes ---------------------------------------------


def test_unirse_reparte_la_cantidad_entre_variantes(api_client, otro, pool_remeras):
    autenticar(api_client, otro)
    response = unirse(api_client, pool_remeras, 3, [fila("M", "Negro", 2), fila("L", "Blanco", 1)])
    assert response.status_code == 201, response.data
    membresia = Membership.objects.get(pool=pool_remeras, usuario=otro)
    assert membresia.detalle == [fila("M", "Negro", 2), fila("L", "Blanco", 1)]


def test_filas_repetidas_se_agrupan(api_client, otro, pool_remeras):
    autenticar(api_client, otro)
    unirse(api_client, pool_remeras, 3, [fila("M", "Negro", 1), fila("M", "Negro", 2)])
    assert Membership.objects.get(usuario=otro).detalle == [fila("M", "Negro", 3)]


@pytest.mark.parametrize(
    ("detalle", "mensaje"),
    [
        # En el orden de la categoría (variantes_vigentes), no en el de jsonb.
        (None, "Elegí talle y color"),
        ([fila("M", "Negro", 1)], "suman 1 y tu reserva es de 2"),
        ([fila("XL", "Negro", 2)], "Elegí talle de las opciones"),
        ([{"atributos": {"Talle": "M"}, "cantidad": 2}], "Elegí color"),
        ([fila("M", "Negro", 0)], "al menos 1 unidad"),
        ({"Talle": "M"}, "Formato inválido"),
        ("no es una lista", "Formato inválido"),
    ],
)
def test_unirse_con_variantes_invalidas(api_client, otro, pool_remeras, detalle, mensaje):
    autenticar(api_client, otro)
    response = unirse(api_client, pool_remeras, 2, detalle)
    assert response.status_code == 400
    assert mensaje in str(response.data["detalle"])
    assert not Membership.objects.filter(usuario=otro).exists()


def test_pool_sin_variantes_ignora_el_detalle(api_client, otro, user, categoria_otros):
    pool = crear_pool(user, categoria_otros)
    autenticar(api_client, otro)
    response = unirse(api_client, pool, 1, [fila("M", "Negro", 1)])
    assert response.status_code == 201
    assert Membership.objects.get(usuario=otro).detalle == []


def test_cambiar_cantidad_pide_variantes_de_nuevo(api_client, otro, pool_remeras):
    autenticar(api_client, otro)
    unirse(api_client, pool_remeras, 1, [fila("S", "Negro", 1)])
    url = reverse("pool-mi-membresia", args=[pool_remeras.id])
    sin_detalle = api_client.patch(url, {"cantidad": 2}, format="json")
    assert sin_detalle.status_code == 400
    ok = api_client.patch(
        url, {"cantidad": 2, "detalle": [fila("S", "Negro", 1), fila("M", "Blanco", 1)]}, format="json"
    )
    assert ok.status_code == 200, ok.data
    assert Membership.objects.get(usuario=otro).detalle == [fila("S", "Negro", 1), fila("M", "Blanco", 1)]


# --- Quién ve qué -------------------------------------------------------------


def test_creador_ve_las_variantes_y_los_demas_solo_las_propias(api_client, user, otro, pool_remeras):
    autenticar(api_client, otro)
    unirse(api_client, pool_remeras, 2, [fila("M", "Negro", 2)])
    url = reverse("pool-detail", args=[pool_remeras.id])

    mio = api_client.get(url).data["miembros"][0]
    assert mio["detalle"] == [fila("M", "Negro", 2)]

    autenticar(api_client, user)
    assert api_client.get(url).data["miembros"][0]["detalle"] == [fila("M", "Negro", 2)]

    api_client.force_authenticate(None)
    api_client.credentials()
    publico = api_client.get(url).data["miembros"]
    assert all("detalle" not in m for m in publico)


def test_resumen_suma_por_variante():
    detalles = [
        [fila("M", "Negro", 2), fila("L", "Blanco", 1)],
        [{"atributos": {"Color": "Negro", "Talle": "M"}, "cantidad": 3}],
        [],
    ]
    assert resumen(detalles) == [
        ({"Color": "Negro", "Talle": "M"}, 5),
        ({"Color": "Blanco", "Talle": "L"}, 1),
    ]


@pytest.fixture
def categoria_otros(db):
    return Category.objects.get(nombre="Otros")


def test_variantes_ordenadas_como_la_categoria(api_client, pool_remeras):
    data = api_client.get(reverse("pool-detail", args=[pool_remeras.id])).data
    assert data["variantes"] == [
        {"nombre": "Talle", "opciones": ["S", "M", "L"]},
        {"nombre": "Color", "opciones": ["Negro", "Blanco"]},
    ]


def test_listado_con_variantes_sin_n_mas_1(api_client, user, remera, django_assert_max_num_queries):
    for i in range(6):
        crear_pool(user, remera, titulo=f"P{i}", atributos={"Talle": ["M"]})
    with django_assert_max_num_queries(12):
        response = api_client.get(reverse("pool-list"))
    assert all(p["variantes"] for p in response.data["results"])


# --- Regresiones de la revisión de la Fase 2 -------------------------------------


def test_filtrar_por_ropa_incluye_subcategorias(api_client, user, remera):
    crear_pool(user, remera, titulo="Remeras")
    ropa = Category.objects.get(nombre="Ropa")
    response = api_client.get(reverse("pool-list"), {"categoria": ropa.id})
    assert [p["titulo"] for p in response.data["results"]] == ["Remeras"]


def test_cambio_de_variantes_sin_cambiar_cantidad_deja_evento_propio(api_client, otro, pool_remeras):
    from .models import EventoPool

    autenticar(api_client, otro)
    unirse(api_client, pool_remeras, 2, [fila("M", "Negro", 2)])
    url = reverse("pool-mi-membresia", args=[pool_remeras.id])
    api_client.patch(url, {"cantidad": 2, "detalle": [fila("L", "Negro", 2)]}, format="json")
    evento = EventoPool.objects.filter(pool=pool_remeras, tipo="cantidad").get()
    assert evento.datos == {"antes": 2, "despues": 2, "variantes": True}
    # Mismas filas en otro orden: no es un cambio.
    api_client.patch(url, {"cantidad": 2, "detalle": [fila("L", "Negro", 2)]}, format="json")
    assert EventoPool.objects.filter(pool=pool_remeras, tipo="cantidad").count() == 1


def test_variante_que_sale_del_catalogo_deja_de_pedirse(api_client, otro, pool_remeras):
    # Si una migración saca "Blanco" de la categoría, la API y la validación dejan
    # de ofrecerlo a la vez (nadie queda trabado eligiendo algo inexistente).
    from .models import AtributoCategoria

    color = AtributoCategoria.objects.get(categoria__nombre="Ropa", nombre="Color")
    color.opciones = [c for c in color.opciones if c != "Blanco"]
    color.save()
    data = api_client.get(reverse("pool-detail", args=[pool_remeras.id])).data
    assert {"nombre": "Color", "opciones": ["Negro"]} in data["variantes"]
    autenticar(api_client, otro)
    assert unirse(api_client, pool_remeras, 1, [fila("S", "Blanco", 1)]).status_code == 400
    assert unirse(api_client, pool_remeras, 1, [fila("S", "Negro", 1)]).status_code == 201


# --- Backoffice de categorías (Fase 3) ----------------------------------------


@pytest.fixture
def staff(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email="staff-cat@example.com", username="staffcat", dni="40999111", password="x", is_staff=True
    )


def test_solo_staff_administra_categorias(api_client, user, staff):
    ropa = Category.objects.get(nombre="Ropa")
    autenticar(api_client, user)
    assert api_client.post(reverse("category-list"), {"nombre": "Short"}, format="json").status_code == 403
    autenticar(api_client, staff)
    response = api_client.post(
        reverse("category-list"), {"nombre": "  Short  ", "padre": ropa.id}, format="json"
    )
    assert response.status_code == 201, response.data
    assert response.data["nombre"] == "Short"
    # Hereda Color de Ropa aunque todavía no tenga atributos propios.
    assert [a["nombre"] for a in response.data["atributos"]] == ["Color"]


def test_un_solo_nivel_de_subcategorias(api_client, staff):
    remera = Category.objects.get(nombre="Remera")
    ropa = Category.objects.get(nombre="Ropa")
    autenticar(api_client, staff)
    nieta = api_client.post(reverse("category-list"), {"nombre": "Manga corta", "padre": remera.id}, format="json")
    assert nieta.status_code == 400
    con_hijas = api_client.patch(reverse("category-detail", args=[ropa.id]), {"padre": remera.id}, format="json")
    assert con_hijas.status_code == 400


def test_reemplazar_atributos_propios(api_client, staff, remera):
    autenticar(api_client, staff)
    url = reverse("category-atributos", args=[remera.id])
    response = api_client.put(
        url, {"atributos": [{"nombre": "Talle", "opciones": ["S", "M", "M", " L "]}]}, format="json"
    )
    assert response.status_code == 200, response.data
    assert response.data["propios"] == [{"nombre": "Talle", "opciones": ["S", "M", "L"]}]
    vacio = api_client.put(url, {"atributos": [{"nombre": "Talle", "opciones": []}]}, format="json")
    assert vacio.status_code == 400


def test_no_se_borra_una_categoria_en_uso(api_client, staff, user, remera):
    crear_pool(user, remera)
    autenticar(api_client, staff)
    response = api_client.delete(reverse("category-detail", args=[remera.id]))
    assert response.status_code == 400
    assert Category.objects.filter(pk=remera.pk).exists()



def test_nombre_de_categoria_normalizado_no_duplica(api_client, staff):
    autenticar(api_client, staff)
    for nombre in ("  remera ", "Remera", "REMERA"):
        response = api_client.post(reverse("category-list"), {"nombre": nombre}, format="json")
        assert response.status_code == 400
        assert "Ya existe" in str(response.data["nombre"])
