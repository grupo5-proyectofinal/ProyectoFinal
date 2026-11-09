"""Autocompletado desde el enlace de la tienda (Iteración 3: "el servicio de
autocompletar datos del link falla"). Todo offline: fixtures en fixtures_producto/."""
# ruff: noqa: F811 — los fixtures importados de tests.py se reciben como parámetros

import json
import socket
from pathlib import Path
from urllib.error import HTTPError

import pytest

from . import producto
from .tests import api_client, categoria, user  # noqa: F401 — fixtures compartidos

FIXTURES = Path(__file__).parent / "fixtures_producto"


def fixture(nombre):
    return (FIXTURES / nombre).read_bytes()


def servir(monkeypatch, respuestas):
    """Reemplaza la descarga: {fragmento de URL: (bytes, content-type) | excepción}."""
    pedidas = []

    def descargar(url, limite, acepta="*/*", truncar=False):
        pedidas.append(url)
        for fragmento, respuesta in respuestas.items():
            if fragmento in url:
                if isinstance(respuesta, Exception):
                    raise respuesta
                contenido, tipo = respuesta
                return contenido, tipo, "utf-8", url
        raise HTTPError(url, 404, "no encontrado", {}, None)

    monkeypatch.setattr(producto, "_descargar", descargar)
    return pedidas


# --- Limpieza del enlace -------------------------------------------------------


def test_limpiar_enlace_saca_tracking_y_fragmento():
    largo = (
        "https://articulo.mercadolibre.com.ar/MLA-1234567890-yerba-_JM"
        "?searchVariation=123&utm_source=ig&tracking_id=abc-def#polycard_client=search"
    )
    assert producto.limpiar_enlace(largo) == (
        "https://articulo.mercadolibre.com.ar/MLA-1234567890-yerba-_JM?searchVariation=123"
    )
    assert producto.limpiar_enlace("https://tienda.com/p?id=5") == "https://tienda.com/p?id=5"


def test_enlace_largo_de_mercadolibre_se_acepta(api_client, user, monkeypatch):
    # Regresión: con max_length=200 los links reales daban 400 y ni siquiera se
    # podía guardar el pool con el enlace.
    from django.urls import reverse

    from . import views
    from .tests import autenticar

    monkeypatch.setattr(
        views, "leer_enlace", lambda url: {"datos": None, "motivo": "sin_datos", "aviso": None}
    )
    autenticar(api_client, user)
    enlace = "https://articulo.mercadolibre.com.ar/MLA-1-x-_JM?" + "&".join(
        f"utm_p{i}=valor-largo-de-seguimiento-{i}" for i in range(20)
    )
    assert len(enlace) > 400
    response = api_client.post(
        reverse("pool-previsualizar-enlace"), {"enlace": enlace}, format="json"
    )
    assert response.status_code == 200, response.data
    assert response.data["enlace"] == "https://articulo.mercadolibre.com.ar/MLA-1-x-_JM"


# --- Extractores ---------------------------------------------------------------


def test_mercadolibre_usa_la_api_publica(monkeypatch):
    pedidas = servir(
        monkeypatch,
        {"api.mercadolibre.com/items/MLA1234567890": (fixture("mercadolibre_item.json"), "application/json")},
    )
    lectura = producto.leer_enlace(
        "https://articulo.mercadolibre.com.ar/MLA-1234567890-yerba-mate-_JM#reco"
    )
    assert lectura["motivo"] is None
    assert lectura["datos"]["nombre_producto"] == "Yerba Mate Playadito 1 Kg Pack x 10"
    assert lectura["datos"]["precio_unitario"] == "45990.00"
    assert lectura["datos"]["imagen"].startswith("https://http2.mlstatic.com/")
    assert pedidas == ["https://api.mercadolibre.com/items/MLA1234567890"]


def test_mercadolibre_sin_api_sigue_con_el_html(monkeypatch):
    html = b'<meta property="og:title" content="Yerba"><meta property="product:price:amount" content="4599">'
    servir(
        monkeypatch,
        {
            "api.mercadolibre.com": HTTPError("x", 403, "forbidden", {}, None),
            "articulo.mercadolibre.com.ar": (html, "text/html"),
        },
    )
    lectura = producto.leer_enlace("https://articulo.mercadolibre.com.ar/MLA-99999999-yerba-_JM")
    assert lectura["datos"]["nombre_producto"] == "Yerba"
    assert lectura["datos"]["precio_unitario"] == "4599.00"


def test_vtex_lee_vtex_events():
    datos = producto.extraer_datos(fixture("vtex.html").decode("latin-1"), "https://tienda-vtex.com.ar/p")
    assert datos["nombre_producto"] == "Zapatilla Running Mujer"
    assert datos["precio_unitario"] == "79999.00"
    assert datos["moneda"] == "ARS"
    assert datos["imagen"].endswith("zapatilla.jpg")


def test_tiendanube_lee_ls_variants():
    datos = producto.extraer_datos(fixture("tiendanube.html").decode(), "https://mitienda.com.ar/remera")
    assert datos["nombre_producto"] == "Remera oversize algodón"
    assert datos["precio_unitario"] == "12500.00"
    assert datos["imagen"] == "https://acdn.mitiendanube.com/stores/001/products/remera-640.jpg"


def test_amazon_lee_titulo_y_precio_en_dolares(monkeypatch):
    servir(monkeypatch, {"amazon.com": (fixture("amazon.html"), "text/html")})
    lectura = producto.leer_enlace("https://www.amazon.com/dp/B0TEST")
    datos = lectura["datos"]
    assert datos["nombre_producto"] == "Auriculares inalámbricos con cancelación de ruido"
    # El precio está en dólares: no se autocompleta y se avisa (no es "45,99 pesos").
    assert datos["precio_unitario"] is None
    assert datos["precio_moneda"] == "45.99"  # el comparador lo convierte
    assert datos["moneda"] == "USD"
    assert "USD" in lectura["aviso"]


def test_microdatos_itemprop():
    datos = producto.extraer_datos(fixture("microdatos.html").decode(), "https://super.com/p")
    assert datos["precio_unitario"] == "4599.90"
    assert datos["moneda"] == "ARS"


def test_json_ld_en_dolares_avisa(monkeypatch):
    servir(monkeypatch, {"shop.example": (fixture("json_ld_usd.html"), "text/html")})
    lectura = producto.leer_enlace("https://shop.example/monitor")
    assert lectura["datos"]["nombre_producto"] == "Monitor 27 pulgadas"
    assert lectura["datos"]["precio_unitario"] is None
    assert lectura["aviso"] == "La tienda publica el precio en USD: cargalo en pesos."


# --- Motivos ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("respuesta", "motivo"),
    [
        (HTTPError("x", 403, "forbidden", {}, None), "bloqueado"),
        (HTTPError("x", 503, "unavailable", {}, None), "bloqueado"),
        (TimeoutError("timed out"), "no_disponible"),
        (producto.EnlaceNoPermitido("IP no pública"), "no_permitido"),
        (producto.HostInexistente("no resuelve"), "no_disponible"),
        ((b"{}", "application/json"), "no_html"),
        ((b"<html><body>sin nada</body></html>", "text/html"), "sin_datos"),
        ((fixture("captcha.html"), "text/html"), "bloqueado"),
    ],
)
def test_motivo_cuando_no_hay_datos(monkeypatch, respuesta, motivo):
    servir(monkeypatch, {"tienda.com": respuesta})
    lectura = producto.leer_enlace("https://tienda.com/p")
    assert lectura == {"datos": None, "motivo": motivo, "aviso": None}
    assert motivo in producto.MENSAJES_MOTIVO


def test_recaptcha_en_una_pagina_normal_no_es_bloqueo(monkeypatch):
    html = b'<script src="https://www.google.com/recaptcha/api.js"></script><meta property="og:title" content="Silla">'
    servir(monkeypatch, {"tienda.com": (html, "text/html")})
    assert producto.leer_enlace("https://tienda.com/silla")["datos"]["nombre_producto"] == "Silla"


def test_vista_previa_devuelve_motivo_y_mensaje(api_client, user, monkeypatch):
    from django.urls import reverse

    from .tests import autenticar

    servir(monkeypatch, {"tienda.com": HTTPError("x", 403, "forbidden", {}, None)})
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-previsualizar-enlace"), {"enlace": "https://tienda.com/p"}, format="json"
    )
    assert response.data["encontrado"] is False
    assert response.data["motivo"] == "bloqueado"
    assert "no deja leer" in response.data["detail"]


# --- Descarga: truncar, charset y anti-SSRF ------------------------------------


def test_html_grande_se_trunca_en_vez_de_fallar(monkeypatch):
    class Respuesta:
        def __init__(self):
            self.headers = __import__("email.message", fromlist=["Message"]).Message()
            self.headers["Content-Type"] = "text/html"

        def read(self, n):
            return b'<meta property="og:title" content="Grande">' + b" " * (n + 10)

        def geturl(self):
            return "https://tienda.com/p"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class Opener:
        def open(self, pedido, timeout):
            return Respuesta()

    monkeypatch.setattr(producto, "_validar_destino", lambda url: None)
    monkeypatch.setattr(producto, "build_opener", lambda *handlers: Opener())
    contenido, *_ = producto._descargar("https://tienda.com/p", 1000, truncar=True)
    assert len(contenido) == 1000
    with pytest.raises(ValueError):
        producto._descargar("https://tienda.com/p", 1000)


def test_charset_desde_meta():
    assert producto._charset_meta(b'<html><head><meta charset="iso-8859-1">') == "iso-8859-1"
    assert producto._charset_meta(
        b'<meta http-equiv="Content-Type" content="text/html; charset=windows-1252">'
    ) == "windows-1252"
    assert producto._charset_meta(b"<html>") is None


def test_conexion_a_ip_privada_se_corta_aunque_el_dns_haya_dado_publica():
    # DNS rebinding: la validación previa vio una IP pública, pero la conexión
    # quedó abierta contra 127.0.0.1. El chequeo sobre el socket la corta.
    class Socket:
        def getpeername(self):
            return ("127.0.0.1", 80)

        def close(self):
            self.cerrado = True

    class Base:
        def connect(self):
            self.sock = Socket()

    class Conexion(producto._Verificada, Base):
        _tunnel_host = None

    conexion = Conexion()
    with pytest.raises(producto.EnlaceNoPermitido):
        conexion.connect()
    assert conexion.sock.cerrado


def test_conexion_a_ip_publica_pasa():
    class Socket:
        def getpeername(self):
            return ("8.8.8.8", 443)

    class Base:
        def connect(self):
            self.sock = Socket()

    class Conexion(producto._Verificada, Base):
        _tunnel_host = None

    Conexion().connect()


def test_guardar_pool_limpia_el_enlace(api_client, user, categoria, monkeypatch):
    from django.urls import reverse

    from . import views
    from .tests import autenticar, payload

    monkeypatch.setattr(views, "geocodificar", lambda direccion, ciudad: None)
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-list"),
        payload(categoria, enlace="https://tienda.com/p?id=5&utm_source=wa#foto"),
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["enlace"] == "https://tienda.com/p?id=5"


@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    """Ningún test de este archivo sale a internet."""

    def prohibido(*args, **kwargs):
        raise AssertionError("un test intentó resolver DNS")

    monkeypatch.setattr(socket, "getaddrinfo", prohibido)


# --- Regresiones de la revisión de la Fase 2 -------------------------------------


def test_limpiar_enlace_no_rompe_links_de_otras_tiendas():
    # `ref` puede elegir el producto fuera de Amazon; las rutas de SPA van en el hash.
    assert producto.limpiar_enlace("https://tienda.com/p?ref=SKU123&utm_medium=x") == (
        "https://tienda.com/p?ref=SKU123"
    )
    assert producto.limpiar_enlace("https://tienda.com/#/producto/123") == (
        "https://tienda.com/#/producto/123"
    )
    assert producto.limpiar_enlace("https://tienda.com/p?flag&q=a%20b") == (
        "https://tienda.com/p?flag&q=a%20b"
    )
    assert producto.limpiar_enlace("https://www.amazon.com/dp/B0X?ref=sr_1&qid=9&th=1") == (
        "https://www.amazon.com/dp/B0X?th=1"
    )


def test_amazon_con_signo_peso_a_secas_no_es_en_pesos(monkeypatch):
    html = b'<span id="productTitle">Mouse</span><span class="a-offscreen">$45.99</span>'
    servir(monkeypatch, {"amazon.com": (html, "text/html")})
    lectura = producto.leer_enlace("https://www.amazon.com/dp/B0MOUSE")
    assert lectura["datos"]["moneda"] == "USD"
    assert lectura["datos"]["precio_unitario"] is None
    assert "USD" in lectura["aviso"]


def test_captura_de_amazon_respeta_el_elemento():
    html = (
        '<span class="a-offscreen"> </span><span aria-hidden="true">'
        '<span class="a-price-symbol">$</span></span>'
        '<span id="productTitle">Silla <b>gamer</b> negra</span>'
    )
    parser = producto._Metadatos()
    parser.feed(html)
    assert "a-offscreen" not in parser.texto_por_clase  # vacío: no se lleva el "$" de al lado
    assert parser.texto_por_id["productTitle"] == "Silla gamer negra"


def test_mercadolibre_catalogo_usa_item_id(monkeypatch):
    pedidas = servir(
        monkeypatch,
        {"api.mercadolibre.com/items/MLA1234567890": (fixture("mercadolibre_item.json"), "application/json")},
    )
    producto.leer_enlace(
        "https://www.mercadolibre.com.ar/yerba/p/MLA19876543?item_id=MLA1234567890&pdp_filters=x"
    )
    assert pedidas[0] == "https://api.mercadolibre.com/items/MLA1234567890"


def test_mercadolibre_catalogo_sin_item_no_usa_la_api(monkeypatch):
    pedidas = servir(monkeypatch, {"mercadolibre.com.ar": (b"<title>x</title>", "text/html")})
    producto.leer_enlace("https://www.mercadolibre.com.ar/yerba/p/MLA19876543")
    assert not any("api.mercadolibre.com" in url for url in pedidas)


def test_mercadolibre_con_json_raro_no_rompe(monkeypatch):
    raro = json.dumps({"title": "Yerba", "pictures": "no-es-lista", "price": "abc"}).encode()
    servir(monkeypatch, {"api.mercadolibre.com": (raro, "application/json")})
    lectura = producto.leer_enlace("https://articulo.mercadolibre.com.ar/MLA-1234567890-x-_JM")
    assert lectura["datos"]["nombre_producto"] == "Yerba"
    assert lectura["datos"]["imagen"] is None


def test_leer_enlace_nunca_lanza(monkeypatch):
    servir(monkeypatch, {"tienda.com": (b"<title>x</title>", "text/html")})

    def explota(html, url):
        raise KeyError("inesperado")

    monkeypatch.setattr(producto, "extraer_datos", explota)
    assert producto.leer_enlace("https://tienda.com/p")["motivo"] == "sin_datos"


def test_con_proxy_http_no_se_chequea_la_ip_del_proxy():
    from urllib.request import Request

    capturada = {}

    class Handler(producto._HandlerHTTP):
        def do_open(self, clase, req, **kwargs):
            capturada["clase"] = clase

    pedido = Request("http://tienda.com/p")
    pedido.set_proxy("127.0.0.1:3128", "http")
    Handler().http_open(pedido)
    assert capturada["clase"] is producto.http.client.HTTPConnection
    Handler().http_open(Request("http://tienda.com/p"))
    assert capturada["clase"] is producto._HTTPVerificada
