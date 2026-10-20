"""Datos del producto a partir del enlace de la tienda (fail-soft).

Al crear un pool el usuario pega el enlace y el front pide estos datos para
autocompletar nombre, precio e imagen. El servidor descarga la página y lee los
metadatos estándar que publican las tiendas: JSON-LD `Product`, Open Graph
(`og:title`, `og:image`, `product:price:amount`) y `<title>` como último recurso.

Es una descarga hacia una URL que elige el usuario, así que se limita a lo
mínimo (anti-SSRF): solo http/https a puertos estándar, el host tiene que
resolver a IPs públicas (se revalida en cada redirección), timeout corto y
tope de bytes. Cualquier falla devuelve None: nunca tumba el endpoint.
"""

import http.client
import ipaddress
import json
import logging
import socket
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; PoolShop/1.0; +vista previa de producto)"
TIMEOUT = 8
MAX_HTML = 2 * 1024 * 1024
MAX_IMAGEN = 5 * 1024 * 1024
MAX_REDIRECCIONES = 3
PUERTOS = {"http": 80, "https": 443}
PRECIO_MAX = Decimal("99999999.99")  # tope de Pool.precio_unitario (10 dígitos, 2 decimales)
LARGO_NOMBRE = 200  # Pool.nombre_producto


class EnlaceNoPermitido(Exception):
    """La URL apunta a un destino que no se descarga (esquema, puerto o IP privada)."""


def _validar_destino(url):
    """Corta si la URL no es http(s) a un host público en un puerto estándar."""
    partes = urlsplit(url)
    esquema = partes.scheme.lower()
    if esquema not in PUERTOS:
        raise EnlaceNoPermitido(f"esquema {esquema!r}")
    host = partes.hostname
    if not host:
        raise EnlaceNoPermitido("sin host")
    try:
        puerto = partes.port or PUERTOS[esquema]
    except ValueError as error:
        raise EnlaceNoPermitido("puerto inválido") from error
    if puerto != PUERTOS[esquema]:
        raise EnlaceNoPermitido(f"puerto {puerto}")
    try:
        direcciones = {info[4][0] for info in socket.getaddrinfo(host, puerto)}
    except (socket.gaierror, UnicodeError) as error:
        raise EnlaceNoPermitido(f"no resuelve: {error}") from error
    for direccion in direcciones:
        if not ipaddress.ip_address(direccion.split("%")[0]).is_global:
            raise EnlaceNoPermitido(f"IP no pública {direccion}")


class _RedireccionSegura(HTTPRedirectHandler):
    max_redirections = MAX_REDIRECCIONES

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validar_destino(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _descargar(url, limite, acepta="*/*"):
    """(bytes, content-type, charset, url final) de `url`, sin pasar de `limite` bytes."""
    _validar_destino(url)
    opener = build_opener(_RedireccionSegura)
    pedido = Request(url, headers={"User-Agent": USER_AGENT, "Accept": acepta})
    with opener.open(pedido, timeout=TIMEOUT) as respuesta:
        contenido = respuesta.read(limite + 1)
        if len(contenido) > limite:
            raise ValueError("la respuesta supera el tamaño permitido")
        tipo = respuesta.headers.get("Content-Type", "")
        charset = respuesta.headers.get_content_charset() or "utf-8"
        return contenido, tipo, charset, respuesta.geturl()


class _Metadatos(HTMLParser):
    """Junta `<meta>`, `<title>` y los bloques JSON-LD de la página."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.titulo = ""
        self.json_ld = []
        self._en_titulo = False
        self._en_json_ld = False
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        atributos = {clave.lower(): valor for clave, valor in attrs if valor is not None}
        if tag == "meta":
            clave = (
                atributos.get("property") or atributos.get("name") or atributos.get("itemprop")
            )
            if clave and "content" in atributos:
                self.meta.setdefault(clave.lower(), atributos["content"].strip())
        elif tag == "title":
            self._en_titulo = True
        elif tag == "script" and atributos.get("type", "").lower() == "application/ld+json":
            self._en_json_ld = True
            self._buffer = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._en_titulo = False
        elif tag == "script" and self._en_json_ld:
            self._en_json_ld = False
            self.json_ld.append("".join(self._buffer))

    def handle_data(self, data):
        if self._en_titulo and not self.titulo:
            self.titulo = data.strip()
        elif self._en_json_ld:
            self._buffer.append(data)


def _productos_json_ld(bloques):
    """Los nodos `Product` de los bloques JSON-LD (sueltos, en lista o en @graph)."""
    pendientes = []
    for bloque in bloques:
        try:
            pendientes.append(json.loads(bloque))
        except ValueError:
            continue
    productos = []
    while pendientes:
        nodo = pendientes.pop(0)
        if isinstance(nodo, list):
            pendientes.extend(nodo)
        elif isinstance(nodo, dict):
            tipo = nodo.get("@type")
            tipos = tipo if isinstance(tipo, list) else [tipo]
            if "Product" in tipos:
                productos.append(nodo)
            if isinstance(nodo.get("@graph"), list):
                pendientes.extend(nodo["@graph"])
    return productos


def _url_imagen(valor):
    if isinstance(valor, str):
        return valor
    if isinstance(valor, list) and valor:
        return _url_imagen(valor[0])
    if isinstance(valor, dict):
        return _url_imagen(valor.get("url") or valor.get("contentUrl"))
    return None


def _precio_oferta(ofertas):
    if isinstance(ofertas, list):
        for oferta in ofertas:
            precio = _precio_oferta(oferta)
            if precio is not None:
                return precio
        return None
    if isinstance(ofertas, dict):
        for clave in ("price", "lowPrice", "highPrice"):
            precio = normalizar_precio(ofertas.get(clave))
            if precio is not None:
                return precio
        return _precio_oferta(ofertas.get("priceSpecification"))
    return None


def normalizar_precio(valor):
    """Decimal con 2 decimales a partir de `1234.5`, "1.234,56", "$ 1,234.56"…; o None.

    Con punto y coma, el último separador es el decimal. Con uno solo, se toma
    como separador de miles si agrupa de a tres dígitos ("1.234", "12,500").
    """
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float, Decimal)):
        texto = str(valor)
    elif isinstance(valor, str):
        texto = "".join(c for c in valor if c.isdigit() or c in ".,")
        if "." in texto and "," in texto:
            decimal = "." if texto.rfind(".") > texto.rfind(",") else ","
            miles = "," if decimal == "." else "."
            texto = texto.replace(miles, "").replace(decimal, ".")
        elif "," in texto or "." in texto:
            separador = "," if "," in texto else "."
            grupos = texto.split(separador)
            if len(grupos) > 2 or (len(grupos[-1]) == 3 and grupos[0] not in ("", "0")):
                texto = texto.replace(separador, "")
            else:
                texto = texto.replace(separador, ".")
    else:
        return None
    try:
        precio = Decimal(texto).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
    if not precio.is_finite() or precio <= 0 or precio > PRECIO_MAX:
        return None
    return precio


def extraer_datos(html, url_base):
    """`{nombre_producto, precio_unitario, imagen, descripcion}` desde el HTML.

    Cada clave es None cuando la página no la publica. JSON-LD manda sobre Open
    Graph porque trae el precio y el nombre del producto, no el de la página.
    """
    parser = _Metadatos()
    try:
        parser.feed(html)
        parser.close()
    except (AssertionError, ValueError) as error:  # HTML muy roto: se usa lo leído
        logger.warning("HTML ilegible en %s: %s", url_base, error)
    meta = parser.meta
    producto = next(iter(_productos_json_ld(parser.json_ld)), {})

    nombre = (
        producto.get("name")
        or meta.get("og:title")
        or meta.get("twitter:title")
        or parser.titulo
        or None
    )
    precio = _precio_oferta(producto.get("offers"))
    if precio is None:
        for clave in ("product:price:amount", "og:price:amount", "price", "twitter:data1"):
            precio = normalizar_precio(meta.get(clave))
            if precio is not None:
                break
    imagen = (
        _url_imagen(producto.get("image"))
        or meta.get("og:image:secure_url")
        or meta.get("og:image")
        or meta.get("twitter:image")
    )
    descripcion = producto.get("description") or meta.get("og:description") or meta.get(
        "description"
    )
    return {
        "nombre_producto": nombre.strip()[:LARGO_NOMBRE] if isinstance(nombre, str) else None,
        "precio_unitario": str(precio) if precio is not None else None,
        "imagen": urljoin(url_base, imagen) if isinstance(imagen, str) and imagen else None,
        "descripcion": descripcion.strip()[:1000] if isinstance(descripcion, str) else None,
    }


def datos_de_enlace(url):
    """Datos del producto publicados en `url`, o None si no se pudo leer (fail-soft)."""
    try:
        contenido, tipo, charset, final = _descargar(
            url, MAX_HTML, "text/html,application/xhtml+xml"
        )
    except (EnlaceNoPermitido, OSError, ValueError, http.client.HTTPException) as error:
        logger.warning("No se pudo leer el enlace %r: %s", url, error)
        return None
    if tipo and "html" not in tipo.lower():
        logger.warning("El enlace %r no es una página HTML (%s)", url, tipo)
        return None
    try:
        html = contenido.decode(charset, errors="replace")
    except LookupError:
        html = contenido.decode("utf-8", errors="replace")
    return extraer_datos(html, final)


def imagen_de_url(url):
    """La imagen de `url` lista para un `PoolImage` (JPEG/PNG), o None (fail-soft).

    Otros formatos (WEBP, GIF, AVIF…) se convierten a JPEG: el resto de la API
    solo acepta JPEG o PNG.
    """
    try:
        contenido, _tipo, _charset, _final = _descargar(url, MAX_IMAGEN, "image/*")
        imagen = Image.open(BytesIO(contenido))
        imagen.load()
    except (
        EnlaceNoPermitido,
        OSError,
        ValueError,
        http.client.HTTPException,
        UnidentifiedImageError,
        Image.DecompressionBombError,
    ) as error:
        logger.warning("No se pudo descargar la imagen %r: %s", url, error)
        return None
    if imagen.format in ("JPEG", "PNG"):
        extension = "jpg" if imagen.format == "JPEG" else "png"
        return ContentFile(contenido, name=f"producto.{extension}")
    salida = BytesIO()
    imagen.convert("RGB").save(salida, format="JPEG", quality=88)
    return ContentFile(salida.getvalue(), name="producto.jpg")
