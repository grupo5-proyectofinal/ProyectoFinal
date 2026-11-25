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


def borrador_completo(user, categoria, **extra):
    datos = {"enlace": "https://tienda.example.com/p"}
    datos.update(extra)
    return poner_estado(crear_pool(user, categoria, **datos), Pool.Estado.BORRADOR)


def test_publicar_borrador_lo_abre(api_client, user, categoria):
    pool = borrador_completo(user, categoria)
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-publicar", args=[pool.id]))
    assert response.status_code == 200
    assert response.data["estado"] == "abierto"
    assert pool.eventos.filter(tipo=EventoPool.Tipo.ESTADO).exists()


def test_guardar_borrador_a_medias_solo_pide_titulo_y_categoria(api_client, user, categoria):
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-list"),
        {"titulo": "Algo para armar", "categoria": categoria.id, "borrador": True},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["estado"] == "borrador"
    sin_titulo = api_client.post(
        reverse("pool-list"), {"categoria": categoria.id, "borrador": True}, format="json"
    )
    assert sin_titulo.status_code == 400
    assert "titulo" in sin_titulo.data


def test_sin_borrador_siguen_siendo_obligatorios_los_datos(api_client, user, categoria):
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-list"), {"titulo": "A", "categoria": categoria.id}, format="json"
    )
    assert response.status_code == 400
    assert "precio_unitario" in response.data


def test_borrador_a_medias_se_completa_por_partes_y_recien_entonces_se_publica(
    api_client, user, categoria
):
    autenticar(api_client, user)
    pk = api_client.post(
        reverse("pool-list"),
        {"titulo": "A medias", "categoria": categoria.id, "borrador": True},
        format="json",
    ).data["id"]
    publicar = reverse("pool-publicar", args=[pk])
    incompleto = api_client.post(publicar)
    assert incompleto.status_code == 400
    for campo in ("nombre_producto", "enlace", "precio_unitario", "cantidad_total", "direccion"):
        assert campo in incompleto.data, campo
    # Se puede guardar un campo vacío de nuevo sin que el borrador se rompa.
    assert (
        api_client.patch(
            reverse("pool-detail", args=[pk]), {"nombre_producto": "", "ciudad": ""}, format="json"
        ).status_code
        == 200
    )
    completo = api_client.patch(
        reverse("pool-detail", args=[pk]),
        {
            "nombre_producto": "Perfume X",
            "enlace": "https://tienda.example.com/p",
            "precio_unitario": "1000.00",
            "cantidad_total": 10,
            "cantidad_creador": 2,
            "direccion": "Calle 1",
            "ciudad": "Córdoba",
        },
        format="json",
    )
    assert completo.status_code == 200, completo.data
    assert api_client.post(publicar).data["estado"] == "abierto"


def test_publicar_pide_alias_si_cobra_por_transferencia(api_client, user, categoria):
    pool = borrador_completo(user, categoria, tipo_pago=Pool.TipoPago.TRANSFERENCIA)
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-publicar", args=[pool.id]))
    assert response.status_code == 400
    assert "alias_cbu" in response.data


def test_publicar_solo_el_creador_y_solo_borradores(api_client, user, otro, categoria, pool):
    borrador = borrador_completo(user, categoria)
    autenticar(api_client, otro)
    assert api_client.post(reverse("pool-publicar", args=[borrador.id])).status_code == 404
    autenticar(api_client, user)
    assert api_client.post(reverse("pool-publicar", args=[pool.id])).status_code == 400


def test_publicar_borrador_con_fecha_vencida_pide_editar(api_client, user, categoria):
    pool = borrador_completo(
        user, categoria, fecha_caducidad=timezone.localdate() - timedelta(days=1)
    )
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
            "detalle": "Córdoba",
            "etiqueta": "Avenida Colón 100, Córdoba",
            "con_altura": True,
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


def test_el_monto_de_cada_integrante_incluye_su_parte_del_envio(api_client, user, otro, categoria):
    """El envío se reparte por unidades: 10 unidades, $1.000 de envío → $100 por unidad."""
    pool = crear_pool(
        user, categoria, cantidad_total=10, cantidad_creador=2, precio_envio="1000.00"
    )
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3, telefono=TELEFONO)
    pool.refresh_from_db()  # crear_pool deja los importes como texto hasta releer
    assert str(pool.monto_de(3)) == "600.00"  # 3 × $100 + 3 × $100 de envío
    autenticar(api_client, user)
    detalle = api_client.get(reverse("pool-detail", args=[pool.id])).data
    assert detalle["miembros"][0]["monto"] == "600.00"
    assert detalle["precio_total"] == "1000.00"
    assert detalle["costo_total"] == "2000.00"
    assert detalle["envio_por_unidad"] == "100.00"


def test_sin_envio_el_monto_sigue_siendo_unidades_por_precio(categoria, user):
    pool = crear_pool(user, categoria)
    pool.refresh_from_db()
    assert str(pool.monto_de(3)) == "300.00"
    assert str(pool.parte_envio(3)) == "0.00"


def test_la_baja_y_la_cancelacion_devuelven_lo_que_se_pago_con_el_envio(
    api_client, user, otro, categoria
):
    from .models import crear_devolucion

    pool = crear_pool(
        user, categoria, cantidad_total=10, cantidad_creador=2, precio_envio="1000.00"
    )
    membership = Membership.objects.create(pool=pool, usuario=otro, cantidad=3, telefono=TELEFONO)
    pool.refresh_from_db()
    assert str(crear_devolucion(pool, membership, "Prueba").monto) == "600.00"


def _direccion_georef(calle, altura, localidad, departamento, provincia, lat=None):
    item = {
        "calle": {"nombre": calle},
        "altura": {"valor": altura},
        "localidad_censal": {"nombre": localidad},
        "departamento": {"id": departamento, "nombre": localidad},
        "provincia": {"id": provincia[0], "nombre": provincia[1]},
    }
    if lat:
        item["ubicacion"] = {"lat": lat, "lon": -58.8}
    return item


CORRIENTES = ("18", "Corrientes")


class GeorefFalso:
    """Responde como Georef según el endpoint y los filtros; anota cada pedido."""

    def __init__(self, direcciones=None, calles=None, falla=False):
        self.direcciones = direcciones or []
        self.calles = calles or []
        self.falla = falla
        self.pedidos = []

    def __call__(self, url, parametros):
        self.pedidos.append((url, parametros))
        if "datos.gob.ar" not in url:
            return NOMINATIM
        if self.falla:
            return None
        if url.endswith("/localidades"):
            return {
                "localidades": [
                    {
                        "nombre": "CORRIENTES",
                        "departamento": {"id": "18021"},
                        "provincia": {"id": "18", "nombre": "Corrientes"},
                    }
                ]
            }
        if url.endswith("/ubicacion"):
            return {
                "ubicacion": {
                    "departamento": {"id": "18021", "nombre": "Capital"},
                    "municipio": {"nombre": "Corrientes"},
                    "provincia": {"id": "18", "nombre": "Corrientes"},
                }
            }
        clave = "direcciones" if url.endswith("/direcciones") else "calles"
        items = self.direcciones if clave == "direcciones" else self.calles
        filtrados = [
            item
            for item in items
            if all(
                item.get(campo, {}).get("id") == parametros[campo]
                for campo in ("provincia", "departamento")
                if campo in parametros
            )
        ]
        return {clave: filtrados}

    def urls(self):
        return [url for url, _ in self.pedidos]


def test_con_ciudad_sugiere_primero_las_direcciones_de_esa_ciudad(api_client, user):
    """Regresión del cliente: «Belgrano» traía calles de pueblos de cualquier provincia."""
    georef = GeorefFalso(
        direcciones=[
            _direccion_georef("BELGRANO", 740, "MONTE CASEROS", "18091", CORRIENTES, -30.2),
            _direccion_georef("BELGRANO", 740, "CORRIENTES", "18021", CORRIENTES, -27.47),
        ]
    )
    autenticar(api_client, user)
    with mock.patch("pools.geocoding._pedir_json", side_effect=georef):
        response = api_client.get(
            reverse("pool-buscar-direccion"),
            {"q": "belgrano 740", "ciudad": "Corrientes"},
        )
    assert response.data[0] == {
        "direccion": "Belgrano 740",
        "ciudad": "Corrientes",
        "detalle": "Corrientes",
        "etiqueta": "Belgrano 740, Corrientes",
        "con_altura": True,
        "latitud": "-27.470000",
        "longitud": "-58.800000",
    }
    assert response.data[1]["detalle"] == "Monte Caseros, Corrientes"
    # Se busca solo dentro de la provincia de la ciudad, nunca en todo el país.
    filtros = [p for url, p in georef.pedidos if url.endswith("/direcciones")]
    assert all(p.get("provincia") == "18" for p in filtros)


def test_con_coordenadas_usa_la_zona_del_navegador(api_client, user):
    georef = GeorefFalso(
        calles=[_direccion_georef("BELGRANO", None, "CORRIENTES", "18021", CORRIENTES)]
    )
    autenticar(api_client, user)
    with mock.patch("pools.geocoding._pedir_json", side_effect=georef):
        response = api_client.get(
            reverse("pool-buscar-direccion"),
            {"q": "belgrano", "lat": "-27.47", "lon": "-58.83"},
        )
    assert any(url.endswith("/ubicacion") for url in georef.urls())
    assert response.data[0]["direccion"] == "Belgrano"
    assert response.data[0]["con_altura"] is False


def test_sin_ciudad_en_el_formulario_usa_la_del_perfil(api_client, user):
    user.ciudad = "Corrientes"
    user.save(update_fields=["ciudad"])
    georef = GeorefFalso(
        calles=[_direccion_georef("BELGRANO", None, "CORRIENTES", "18021", CORRIENTES)]
    )
    autenticar(api_client, user)
    with mock.patch("pools.geocoding._pedir_json", side_effect=georef):
        response = api_client.get(reverse("pool-buscar-direccion"), {"q": "belgrano"})
    assert ("https://apis.datos.gob.ar/georef/api/localidades") in georef.urls()
    assert response.data[0]["detalle"] == "Corrientes"


def test_si_falta_la_altura_sugiere_la_calle_de_la_zona_con_el_numero(api_client, user):
    georef = GeorefFalso(
        calles=[_direccion_georef("BELGRANO", None, "CORRIENTES", "18021", CORRIENTES)]
    )
    autenticar(api_client, user)
    with mock.patch("pools.geocoding._pedir_json", side_effect=georef):
        response = api_client.get(
            reverse("pool-buscar-direccion"),
            {"q": "belgrano 1212", "ciudad": "Corrientes"},
        )
    assert response.data[0]["direccion"] == "Belgrano 1212"
    assert response.data[0]["con_altura"] is True


def test_sin_zona_se_usa_nominatim_y_no_georef(api_client, user):
    georef = GeorefFalso()
    autenticar(api_client, user)
    with (
        mock.patch("pools.geocoding._pedir_json", side_effect=georef),
        mock.patch("pools.geocoding._respetar_cuota"),
    ):
        response = api_client.get(reverse("pool-buscar-direccion"), {"q": "colon 100"})
    assert not any(url.endswith(("/calles", "/direcciones")) for url in georef.urls())
    assert response.data[0]["direccion"] == "Avenida Colón 100"


def test_si_georef_falla_se_usa_nominatim(api_client, user):
    georef = GeorefFalso(falla=True)
    autenticar(api_client, user)
    with (
        mock.patch("pools.geocoding._pedir_json", side_effect=georef),
        mock.patch("pools.geocoding._respetar_cuota"),
    ):
        response = api_client.get(
            reverse("pool-buscar-direccion"), {"q": "colon 100", "ciudad": "Córdoba"}
        )
    assert any("datos.gob.ar" in url for url in georef.urls())
    assert response.data[0]["direccion"] == "Avenida Colón 100"


def test_nominatim_descarta_lugares_que_no_son_de_esa_calle(api_client, user):
    estacion = {
        "lat": "-34.56",
        "lon": "-58.45",
        "address": {"road": "Juramento", "city": "Buenos Aires", "state": "CABA"},
    }
    autenticar(api_client, user)
    with (
        mock.patch("pools.geocoding._pedir_json", side_effect=[[estacion]]),
        mock.patch("pools.geocoding._respetar_cuota"),
    ):
        response = api_client.get(reverse("pool-buscar-direccion"), {"q": "belgrano 100"})
    assert response.data == []


def test_calzado_es_categoria_con_zapatilla_sandalias_y_zapato(api_client, db):
    """Corrección del cliente: Calzado deja de ser un tipo de Ropa."""
    from .models import Category

    calzado = Category.objects.get(nombre="Calzado")
    assert calzado.padre_id is None
    assert set(calzado.subcategorias.values_list("nombre", flat=True)) == {
        "Zapatilla",
        "Sandalias",
        "Zapato",
    }
    zapatilla = Category.objects.get(nombre="Zapatilla")
    assert [a.nombre for a in zapatilla.atributos_efectivos()] == ["Talle", "Color"]
    assert "Calzado" not in Category.objects.get(nombre="Ropa").subcategorias.values_list(
        "nombre", flat=True
    )
    response = api_client.get(reverse("category-list"))
    assert {"Calzado", "Zapatilla", "Sandalias", "Zapato"} <= {c["nombre"] for c in response.data}


def test_revertir_calzado_no_pierde_pools(db, user):
    import importlib

    from django.apps import apps

    from .models import Category

    migracion = importlib.import_module("pools.migrations.0022_calzado_categoria")
    zapatilla = Category.objects.get(nombre="Zapatilla")
    pool_zapatilla = crear_pool(user, zapatilla)

    migracion.volver(apps, None)

    pool_zapatilla.refresh_from_db()
    calzado = Category.objects.get(nombre="Calzado")
    assert pool_zapatilla.categoria_id == calzado.pk
    assert calzado.padre.nombre == "Ropa"
    assert not Category.objects.filter(nombre="Zapatilla").exists()

    migracion.separar(apps, None)
    calzado.refresh_from_db()
    assert calzado.padre_id is None
    assert Category.objects.filter(nombre="Zapatilla", padre=calzado).exists()
