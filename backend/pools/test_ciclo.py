"""Borrador, explorar solo con abiertos ajenos, reabrir/duplicar y autocompletado de direcciones."""
# ruff: noqa: F811 — los fixtures importados de tests.py se reciben como parámetros

import json
from datetime import timedelta
from unittest import mock

from django.urls import reverse
from django.utils import timezone

from .models import EventoPool, Membership, Pool
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


def ids(response):
    return {p["id"] for p in response.data["results"]}


def test_explorar_solo_lista_abiertos_de_otros(api_client, user, otro, categoria):
    """Regresión: Explorar mostraba pools en curso, cancelados y los propios."""
    abierto = crear_pool(otro, categoria, titulo="Abierto")
    for estado in (
        Pool.Estado.LISTO,
        Pool.Estado.EN_CURSO,
        Pool.Estado.FINALIZADO,
        Pool.Estado.CANCELADO,
        Pool.Estado.CADUCADO,
    ):
        poner_estado(crear_pool(otro, categoria, titulo=estado), estado)
    crear_pool(user, categoria, titulo="Mío")
    unido = crear_pool(otro, categoria, titulo="Ya reservado")
    Membership.objects.create(pool=unido, usuario=user, cantidad=1, telefono=TELEFONO)
    autenticar(api_client, user)

    response = api_client.get(reverse("pool-list"))

    assert ids(response) == {abierto.id}


def test_explorar_sin_sesion_solo_abiertos(api_client, user, categoria):
    abierto = crear_pool(user, categoria)
    poner_estado(crear_pool(user, categoria), Pool.Estado.EN_CURSO)
    assert ids(api_client.get(reverse("pool-list"))) == {abierto.id}


def test_perfil_publico_lista_los_pools_de_la_persona_sin_borradores(
    api_client, user, otro, categoria
):
    visible = poner_estado(crear_pool(otro, categoria), Pool.Estado.FINALIZADO)
    poner_estado(crear_pool(otro, categoria), Pool.Estado.BORRADOR)
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"), {"creador": otro.id})
    assert ids(response) == {visible.id}


def datos_pool(categoria, **extra):
    datos = {
        "titulo": "Pool nuevo",
        "nombre_producto": "Producto",
        "categoria": categoria.id,
        "enlace": "https://tienda.example.com/producto",
        "precio_unitario": "100.00",
        "cantidad_total": 10,
        "cantidad_creador": 2,
        "min_por_integrante": 1,
        "fecha_caducidad": (timezone.localdate() + timedelta(days=7)).isoformat(),
        "direccion": "Calle 1",
        "ciudad": "Cordoba",
    }
    datos.update(extra)
    return datos


def test_crear_como_borrador_no_se_ve_para_otros(api_client, user, otro, categoria):
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-list"), datos_pool(categoria, borrador=True), format="json"
    )
    assert response.status_code == 201
    assert response.data["estado"] == "borrador"
    pk = response.data["id"]
    assert pk in ids(api_client.get(reverse("pool-mios")))
    autenticar(api_client, otro)
    assert pk not in ids(api_client.get(reverse("pool-list"), {"creador": user.id}))
    assert api_client.get(reverse("pool-detail", args=[pk])).status_code == 404
    unirse = api_client.post(
        reverse("pool-unirse", args=[pk]),
        {"cantidad": 1, "telefono": TELEFONO},
        format="json",
    )
    assert unirse.status_code == 400  # no está abierto


def test_publicar_borrador_lo_abre(api_client, user, categoria):
    pool = poner_estado(crear_pool(user, categoria), Pool.Estado.BORRADOR)
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-publicar", args=[pool.id]))
    assert response.status_code == 200
    assert response.data["estado"] == "abierto"
    assert pool.eventos.filter(tipo=EventoPool.Tipo.ESTADO).exists()


def test_publicar_borrador_con_el_cupo_lleno_queda_listo(api_client, user, categoria):
    pool = crear_pool(user, categoria, cantidad_total=2, cantidad_creador=2)
    poner_estado(pool, Pool.Estado.BORRADOR)
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-publicar", args=[pool.id]))
    assert response.data["estado"] == "listo"


def test_publicar_solo_el_creador_y_solo_borradores(api_client, user, otro, categoria, pool):
    borrador = poner_estado(crear_pool(user, categoria), Pool.Estado.BORRADOR)
    autenticar(api_client, otro)
    assert api_client.post(reverse("pool-publicar", args=[borrador.id])).status_code == 404
    autenticar(api_client, user)
    assert api_client.post(reverse("pool-publicar", args=[pool.id])).status_code == 400


def test_publicar_borrador_con_fecha_vencida_pide_editar(api_client, user, categoria):
    pool = crear_pool(user, categoria, fecha_caducidad=timezone.localdate() - timedelta(days=1))
    poner_estado(pool, Pool.Estado.BORRADOR)
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-publicar", args=[pool.id]))
    assert response.status_code == 400
    assert "fecha_caducidad" in response.data


def test_borrador_se_edita_y_se_cancela(api_client, user, categoria):
    pool = poner_estado(crear_pool(user, categoria), Pool.Estado.BORRADOR)
    autenticar(api_client, user)
    editado = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"titulo": "Otro título"}, format="json"
    )
    assert editado.status_code == 200
    assert editado.data["estado"] == "borrador"
    cancelado = api_client.post(reverse("pool-cancelar", args=[pool.id]))
    assert cancelado.data["estado"] == "cancelado"


def test_cancelar_finalizado_o_cancelado_es_400(api_client, user, categoria):
    autenticar(api_client, user)
    for estado in (Pool.Estado.FINALIZADO, Pool.Estado.CANCELADO):
        pool = poner_estado(crear_pool(user, categoria), estado)
        assert api_client.post(reverse("pool-cancelar", args=[pool.id])).status_code == 400


def fecha(dias=10):
    return (timezone.localdate() + timedelta(days=dias)).isoformat()


def test_reabrir_pool_cancelado_sin_integrantes(api_client, user, categoria):
    pool = poner_estado(crear_pool(user, categoria), Pool.Estado.CANCELADO)
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-reabrir", args=[pool.id]),
        {"fecha_caducidad": fecha()},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["estado"] == "abierto"
    assert response.data["fecha_caducidad"] == fecha()


def test_reabrir_exige_fecha_valida(api_client, user, categoria):
    pool = poner_estado(crear_pool(user, categoria), Pool.Estado.CANCELADO)
    autenticar(api_client, user)
    url = reverse("pool-reabrir", args=[pool.id])
    assert api_client.post(url, {}, format="json").status_code == 400
    ayer = api_client.post(url, {"fecha_caducidad": fecha(-1)}, format="json")
    assert ayer.status_code == 400


def test_reabrir_con_integrantes_pide_duplicar(api_client, user, otro, categoria):
    pool = crear_pool(user, categoria)
    Membership.objects.create(pool=pool, usuario=otro, cantidad=2, telefono=TELEFONO)
    poner_estado(pool, Pool.Estado.CANCELADO)
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-reabrir", args=[pool.id]),
        {"fecha_caducidad": fecha()},
        format="json",
    )
    assert response.status_code == 400
    assert "duplicalo" in str(response.data)


def test_reabrir_solo_cancelados_y_solo_el_creador(api_client, user, otro, categoria, pool):
    autenticar(api_client, user)
    abierto = api_client.post(
        reverse("pool-reabrir", args=[pool.id]),
        {"fecha_caducidad": fecha()},
        format="json",
    )
    assert abierto.status_code == 400
    cancelado = poner_estado(crear_pool(user, categoria), Pool.Estado.CANCELADO)
    autenticar(api_client, otro)
    ajeno = api_client.post(
        reverse("pool-reabrir", args=[cancelado.id]),
        {"fecha_caducidad": fecha()},
        format="json",
    )
    assert ajeno.status_code == 403


def test_duplicar_crea_un_borrador_sin_integrantes(api_client, user, otro, categoria):
    origen = crear_pool(user, categoria, precio_envio="250.00", titulo="Perfume 100 ml")
    Membership.objects.create(pool=origen, usuario=otro, cantidad=2, telefono=TELEFONO)
    poner_estado(origen, Pool.Estado.CANCELADO)
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-duplicar", args=[origen.id]))
    assert response.status_code == 201
    copia = Pool.objects.get(pk=response.data["id"])
    assert copia.pk != origen.pk
    assert copia.estado == Pool.Estado.BORRADOR
    assert copia.titulo == "Perfume 100 ml"
    assert str(copia.precio_envio) == "250.00"
    assert copia.memberships.count() == 0
    assert copia.fecha_caducidad > timezone.localdate()
    origen.refresh_from_db()
    assert origen.estado == Pool.Estado.CANCELADO


def test_duplicar_solo_cerrados_y_solo_el_creador(api_client, user, otro, categoria, pool):
    autenticar(api_client, user)
    assert api_client.post(reverse("pool-duplicar", args=[pool.id])).status_code == 400
    cancelado = poner_estado(crear_pool(user, categoria), Pool.Estado.CANCELADO)
    autenticar(api_client, otro)
    assert api_client.post(reverse("pool-duplicar", args=[cancelado.id])).status_code == 403


def test_precio_envio_se_guarda_y_no_puede_ser_negativo(api_client, user, categoria):
    autenticar(api_client, user)
    ok = api_client.post(
        reverse("pool-list"),
        datos_pool(categoria, precio_envio="1500.50"),
        format="json",
    )
    assert ok.status_code == 201
    assert ok.data["precio_envio"] == "1500.50"
    malo = api_client.post(
        reverse("pool-list"), datos_pool(categoria, precio_envio="-1"), format="json"
    )
    assert malo.status_code == 400
    assert "precio_envio" in malo.data


NOMINATIM = [
    {
        "lat": "-31.4201",
        "lon": "-64.1888",
        "display_name": "Avenida Colón 100, Centro, Córdoba, Argentina",
        "address": {"road": "Avenida Colón", "house_number": "100", "city": "Córdoba"},
    },
    {
        "lat": "-31.4",
        "lon": "-64.2",
        "display_name": "Sin calle",
        "address": {"city": "Córdoba"},
    },
]


def test_buscar_direccion_devuelve_sugerencias(api_client, user):
    autenticar(api_client, user)
    with (
        mock.patch("pools.geocoding.urlopen") as urlopen,
        mock.patch("pools.geocoding._respetar_cuota"),
    ):
        urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
            NOMINATIM
        ).encode()
        response = api_client.get(reverse("pool-buscar-direccion"), {"q": "colon 100 cordoba"})
    assert response.status_code == 200
    assert response.data == [
        {
            "direccion": "Avenida Colón 100",
            "ciudad": "Córdoba",
            "etiqueta": "Avenida Colón 100, Centro, Córdoba, Argentina",
            "latitud": "-31.420100",
            "longitud": "-64.188800",
        }
    ]


def test_buscar_direccion_es_fail_soft(api_client, user):
    autenticar(api_client, user)
    with (
        mock.patch("pools.geocoding.urlopen", side_effect=OSError("sin red")),
        mock.patch("pools.geocoding._respetar_cuota"),
    ):
        response = api_client.get(reverse("pool-buscar-direccion"), {"q": "sin red 123"})
    assert response.status_code == 200
    assert response.data == []


def test_buscar_direccion_pide_sesion_y_largo_minimo(api_client, user):
    assert api_client.get(reverse("pool-buscar-direccion"), {"q": "colon"}).status_code == 401
    autenticar(api_client, user)
    assert api_client.get(reverse("pool-buscar-direccion"), {"q": "co"}).data == []
