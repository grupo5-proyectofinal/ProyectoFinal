"""Datos del producto a partir del enlace de la tienda (fail-soft).

Al crear un pool el usuario pega el enlace y el front pide estos datos para
autocompletar nombre, precio e imagen. Primero se prueban las APIs públicas
que conocemos (MercadoLibre); si no, se descarga la página y se leen los
metadatos que publican las tiendas: JSON-LD `Product`, microdatos `itemprop`,
Open Graph, los datos embebidos de VTEX y Tiendanube, el precio de Amazon y,
como último recurso, `<title>`. Ver la skill `extractor-producto`.

Es una descarga hacia una URL que elige el usuario, así que se limita a lo
mínimo (anti-SSRF): solo http/https a puertos estándar, el host tiene que
resolver a IPs públicas (se revalida en cada redirección y sobre la IP a la que
realmente se conecta), timeout corto y tope de bytes. Nada de esto lanza hacia
la vista: `leer_enlace` siempre devuelve un resultado con su `motivo`.
"""

import http.client
import ipaddress
import json
import logging
import re
import socket
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit
from urllib.request import (
    HTTPHandler,
    HTTPRedirectHandler,
    HTTPSHandler,
    Request,
    build_opener,
)

from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

from config.imagenes import normalizar_imagen

logger = logging.getLogger(__name__)

# Headers de navegador: varias tiendas (Amazon, MercadoLibre, Cloudflare) cortan
# a los clientes que se anuncian como bots y la vista previa fallaba siempre.
HEADERS_NAVEGADOR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.5",
}
TIMEOUT = 8
MAX_HTML = 2 * 1024 * 1024  # se trunca: los metadatos están al principio
MAX_IMAGEN = 5 * 1024 * 1024  # se rechaza: una imagen cortada no sirve
MAX_JSON = 512 * 1024
MAX_REDIRECCIONES = 5  # acortadores (meli.la, amzn.to) encadenan varias
PUERTOS = {"http": 80, "https": 443}
PRECIO_MAX = Decimal("99999999.99")  # tope de Pool.precio_unitario (10 dígitos, 2 decimales)
LARGO_NOMBRE = 200  # Pool.nombre_producto
MONEDA_LOCAL = "ARS"

# Parámetros de seguimiento que no cambian el producto (y alargan el link). Solo
# los que son de tracking en cualquier sitio; `ref`, `sr`, `qid` y los `pd_rd_*`
# se sacan solo en Amazon (en otras tiendas `ref` puede elegir el producto).
PARAMETROS_TRACKING = {
    "tracking_id",
    "fbclid",
    "gclid",
    "gbraid",
    "wbraid",
    "mc_cid",
    "mc_eid",
}
PARAMETROS_TRACKING_AMAZON = {
    "ref",
    "ref_",
    "pf_rd_p",
    "pf_rd_r",
    "pd_rd_r",
    "pd_rd_w",
    "pd_rd_wg",
    "content-id",
    "sr",
    "qid",
}
PARAMETROS_TRACKING_MELI = {
    "c_id",
    "c_uid",
    "c_campaign",
    "c_element_order",
    "c_global_position",
    "c_tracking_id",
    "c_container_id",
}

MENSAJES_MOTIVO = {
    "bloqueado": (
        "La tienda no deja leer esa página desde PoolShop. Completá los datos a mano."
    ),
    "no_disponible": "No pudimos abrir el enlace. Probá de nuevo o completá los datos a mano.",
    "no_permitido": "Ese enlace no se puede leer. Revisá que sea la página pública del producto.",
    "no_html": "El enlace no es una página de producto. Completá los datos a mano.",
    "sin_datos": "No pudimos leer los datos de ese enlace. Completalos a mano.",
}
CODIGOS_BLOQUEO = {401, 403, 429, 503}


class EnlaceNoPermitido(Exception):
    """La URL apunta a un destino que no se descarga (esquema, puerto o IP privada)."""


class HostInexistente(EnlaceNoPermitido):
    """El dominio no resuelve: no es un destino prohibido, es un link roto."""


def _es_tracking(clave, amazon):
    clave = clave.lower()
    return (
        clave.startswith("utm_")
        or clave in PARAMETROS_TRACKING
        or clave in PARAMETROS_TRACKING_MELI
        or (amazon and clave in PARAMETROS_TRACKING_AMAZON)
    )


def limpiar_enlace(url):
    """El enlace sin parámetros de seguimiento (utm_*, tracking_id, fbclid…).

    El resto de la query queda tal cual (sin re-encodear) y el fragmento se saca
    salvo que sea una ruta de una SPA (`#/producto/1`, `#!/…`).
    """
    if not isinstance(url, str) or not url.strip():
        return url
    partes = urlsplit(url.strip())
    if partes.scheme.lower() not in PUERTOS:
        return url.strip()
    amazon = "amazon." in (partes.hostname or "")
    query = "&".join(
        parte
        for parte in partes.query.split("&")
        if parte and not _es_tracking(parte.split("=", 1)[0], amazon)
    )
    fragmento = partes.fragment if partes.fragment.startswith(("/", "!")) else ""
    return urlunsplit((partes.scheme, partes.netloc, partes.path, query, fragmento))


def _ip_publica(direccion):
    return ipaddress.ip_address(direccion.split("%")[0]).is_global


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
        raise HostInexistente(f"no resuelve: {error}") from error
    for direccion in direcciones:
        if not _ip_publica(direccion):
            raise EnlaceNoPermitido(f"IP no pública {direccion}")


class _Verificada:
    """Revisa la IP a la que la conexión realmente quedó abierta.

    `_validar_destino` resuelve el host antes de conectar, pero urllib vuelve a
    resolverlo: un DNS que contesta una IP pública la primera vez y 127.0.0.1 la
    segunda (DNS rebinding) pasaría el control. Mirando el par de la conexión ya
    abierta no hay ventana. Con un proxy HTTP en el medio el par es el proxy: ahí
    resuelve y conecta el proxy, no este proceso.
    """

    def connect(self):
        super().connect()
        if getattr(self, "_tunnel_host", None):
            return
        direccion = self.sock.getpeername()[0]
        if not _ip_publica(direccion):
            self.sock.close()
            raise EnlaceNoPermitido(f"conectó a una IP no pública {direccion}")


class _HTTPVerificada(_Verificada, http.client.HTTPConnection):
    pass


class _HTTPSVerificada(_Verificada, http.client.HTTPSConnection):
    pass


class _HandlerHTTP(HTTPHandler):
    def http_open(self, req):
        # Por un proxy HTTP la conexión es al proxy (suele tener IP privada): ahí el
        # que resuelve y conecta al destino es el proxy.
        clase = http.client.HTTPConnection if req.has_proxy() else _HTTPVerificada
        return self.do_open(clase, req)


class _HandlerHTTPS(HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_HTTPSVerificada, req, context=self._context)


class _RedireccionSegura(HTTPRedirectHandler):
    max_redirections = MAX_REDIRECCIONES

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validar_destino(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _charset_meta(contenido):
    """Charset declarado en `<meta charset>` / http-equiv dentro de los primeros 4 KB."""
    encontrado = re.search(rb"<meta[^>]+charset=[\"']?([A-Za-z0-9_\-]+)", contenido[:4096], re.IGNORECASE)
    return encontrado.group(1).decode("ascii").lower() if encontrado else None


def _descargar(url, limite, acepta="*/*", truncar=False):
    """(bytes, content-type, charset, url final) de `url`.

    Con `truncar` devuelve los primeros `limite` bytes; si no, una respuesta más
    grande es un error (sirve para imágenes, que cortadas no se pueden abrir).
    """
    _validar_destino(url)
    opener = build_opener(_HandlerHTTP, _HandlerHTTPS, _RedireccionSegura)
    pedido = Request(url, headers={**HEADERS_NAVEGADOR, "Accept": acepta})
    with opener.open(pedido, timeout=TIMEOUT) as respuesta:
        contenido = respuesta.read(limite + 1)
        if len(contenido) > limite:
            if not truncar:
                raise ValueError("la respuesta supera el tamaño permitido")
            contenido = contenido[:limite]
        tipo = respuesta.headers.get("Content-Type", "")
        charset = respuesta.headers.get_content_charset() or _charset_meta(contenido) or "utf-8"
        return contenido, tipo, charset, respuesta.geturl()


VACIOS = {"br", "img", "meta", "link", "input", "hr", "source", "wbr", "col", "area", "base"}


class _Metadatos(HTMLParser):
    """Junta `<meta>`, microdatos, `<title>`, JSON-LD, los `<script>` con datos
    embebidos y el precio/título de Amazon."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.titulo = ""
        self.json_ld = []
        self.scripts = []
        self.texto_por_id = {}
        self.texto_por_clase = {}
        self._en_titulo = False
        self._script = None  # "ld" | "otro"
        self._buffer = []
        self._capturando = None  # ("id"|"clase", clave)
        self._profundidad = 0  # tags abiertos dentro del elemento capturado
        self._texto = []

    IDS = ("productTitle",)  # Amazon
    CLASES = ("a-offscreen",)  # Amazon: precio legible ("$ 12.345,00")

    def handle_starttag(self, tag, attrs):
        atributos = {clave.lower(): valor for clave, valor in attrs if valor is not None}
        clave = atributos.get("property") or atributos.get("name") or atributos.get("itemprop")
        if clave and "content" in atributos:
            # <meta> y microdatos (<span itemprop="price" content="1234.50">).
            self.meta.setdefault(clave.lower(), atributos["content"].strip())
        if tag == "title":
            self._en_titulo = True
        elif tag == "script":
            tipo = atributos.get("type", "").lower()
            self._script = "ld" if tipo == "application/ld+json" else "otro"
            self._buffer = []
        elif self._capturando is not None:
            if tag not in VACIOS:
                self._profundidad += 1
        else:
            ident = atributos.get("id")
            clases = atributos.get("class", "").split()
            if ident in self.IDS and ident not in self.texto_por_id:
                self._capturando, self._texto, self._profundidad = ("id", ident), [], 0
            else:
                for clase in self.CLASES:
                    if clase in clases and clase not in self.texto_por_clase:
                        self._capturando, self._texto, self._profundidad = ("clase", clase), [], 0
                        break

    def handle_endtag(self, tag):
        if tag == "title":
            self._en_titulo = False
        elif tag == "script" and self._script:
            contenido = "".join(self._buffer)
            (self.json_ld if self._script == "ld" else self.scripts).append(contenido)
            self._script = None
        elif self._capturando is not None:
            if self._profundidad:
                self._profundidad -= 1
                return
            # Cierre del elemento capturado (con o sin texto: uno vacío no se guarda,
            # y así no se lleva el texto de los hermanos que siguen).
            tipo, clave = self._capturando
            texto = " ".join("".join(self._texto).split())
            if texto:
                destino = self.texto_por_id if tipo == "id" else self.texto_por_clase
                destino[clave] = texto
            self._capturando = None

    def handle_data(self, data):
        if self._en_titulo and not self.titulo:
            self.titulo = data.strip()
        elif self._script:
            self._buffer.append(data)
        elif self._capturando is not None:
            self._texto.append(data)


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
            if "Product" in tipos or "ProductGroup" in tipos:
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


def _oferta(ofertas):
    """(precio, moneda) de la primera oferta con precio (Offer, AggregateOffer, lista)."""
    if isinstance(ofertas, list):
        for oferta in ofertas:
            precio, moneda = _oferta(oferta)
            if precio is not None:
                return precio, moneda
        return None, None
    if isinstance(ofertas, dict):
        moneda = ofertas.get("priceCurrency")
        for clave in ("price", "lowPrice", "highPrice"):
            precio = normalizar_precio(ofertas.get(clave))
            if precio is not None:
                return precio, moneda
        precio, moneda_spec = _oferta(ofertas.get("priceSpecification"))
        return precio, moneda_spec or moneda
    return None, None


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


def _objeto_tras(texto, marcador):
    """El primer objeto/lista JSON que aparece después de `marcador` en `texto`."""
    inicio = texto.find(marcador)
    if inicio < 0:
        return None
    resto = texto[inicio + len(marcador) :].lstrip(" =(\n\t")
    try:
        valor, _fin = json.JSONDecoder().raw_decode(resto)
    except ValueError:
        return None
    return valor


def _datos_embebidos(scripts):
    """Datos de tiendas que no publican JSON-LD: VTEX y Tiendanube."""
    for script in scripts:
        # VTEX: vtex.events.addData({"productName": …, "productPriceTo": …})
        vtex = _objeto_tras(script, "vtex.events.addData")
        if isinstance(vtex, dict) and vtex.get("productName"):
            return {
                "nombre": vtex.get("productName"),
                "precio": normalizar_precio(
                    vtex.get("productPriceTo") or vtex.get("productPriceFrom")
                ),
                "moneda": vtex.get("currency") or vtex.get("productCurrency"),
                "imagen": None,
            }
        # Tiendanube: LS.variants = [{"price_number": …, "image_url": …}]
        variantes = _objeto_tras(script, "LS.variants")
        if isinstance(variantes, list) and variantes and isinstance(variantes[0], dict):
            variante = variantes[0]
            return {
                "nombre": None,
                "precio": normalizar_precio(variante.get("price_number")),
                "moneda": None,
                "imagen": variante.get("image_url"),
            }
    return {}


def _moneda_de_texto(texto):
    """Moneda de un precio escrito ("US$45,99" → USD); None si parece en pesos."""
    if not isinstance(texto, str):
        return None
    compacto = texto.upper().replace(" ", "")
    if any(marca in compacto for marca in ("US$", "U$S", "USD")):
        return "USD"
    if "€" in compacto or "EUR" in compacto:
        return "EUR"
    return None


def extraer_datos(html, url_base):
    """`{nombre_producto, precio_unitario, moneda, imagen, descripcion}` desde el HTML.

    Cada clave es None cuando la página no la publica. Para cada dato se toma la
    fuente más confiable: JSON-LD, microdatos y meta de producto, datos embebidos
    (VTEX/Tiendanube), Amazon, Open Graph y por último `<title>`.
    """
    parser = _Metadatos()
    try:
        parser.feed(html)
        parser.close()
    except (AssertionError, ValueError) as error:  # HTML muy roto: se usa lo leído
        logger.warning("HTML ilegible en %s: %s", url_base, error)
    meta = parser.meta
    producto = next(iter(_productos_json_ld(parser.json_ld)), {})
    embebidos = _datos_embebidos(parser.scripts)

    nombre = (
        producto.get("name")
        or embebidos.get("nombre")
        or parser.texto_por_id.get("productTitle")
        or meta.get("og:title")
        or meta.get("twitter:title")
        or parser.titulo
        or None
    )

    precio, moneda = _oferta(producto.get("offers"))
    if precio is None:
        for clave in ("product:price:amount", "og:price:amount", "price", "twitter:data1"):
            precio = normalizar_precio(meta.get(clave))
            if precio is not None:
                moneda = (
                    meta.get("product:price:currency")
                    or meta.get("og:price:currency")
                    or meta.get("pricecurrency")
                )
                break
    if precio is None and embebidos.get("precio") is not None:
        precio, moneda = embebidos["precio"], embebidos.get("moneda")
    if precio is None:
        texto_precio = parser.texto_por_clase.get("a-offscreen")
        precio = normalizar_precio(texto_precio)
        moneda = _moneda_de_texto(texto_precio) if precio is not None else moneda

    imagen = (
        _url_imagen(producto.get("image"))
        or embebidos.get("imagen")
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
        "moneda": moneda.strip().upper() if isinstance(moneda, str) and moneda.strip() else None,
        "imagen": urljoin(url_base, imagen) if isinstance(imagen, str) and imagen else None,
        "descripcion": descripcion.strip()[:1000] if isinstance(descripcion, str) else None,
    }


# --- MercadoLibre ------------------------------------------------------------

_ID_MELI = re.compile(r"\b(ML[A-Z])-?(\d{6,})\b")
API_MELI = "https://api.mercadolibre.com/items/{}"


def _datos_mercadolibre(url):
    """Datos del ítem por la API pública de MercadoLibre, o None.

    Las páginas de MercadoLibre arman casi todo con JavaScript y suelen cortar a
    los servidores: la API devuelve título, precio y fotos sin leer el HTML.
    """
    partes = urlsplit(url)
    if "mercadolibre" not in (partes.hostname or "") and "mercadolivre" not in (
        partes.hostname or ""
    ):
        return None
    # Links de catálogo (/p/MLA…) traen el ítem real en ?item_id=; el id del path
    # es del producto de catálogo y en /items/ sería otra publicación.
    item_id = (parse_qs(partes.query).get("item_id") or [""])[0]
    encontrado = _ID_MELI.search(item_id)
    if not encontrado:
        if re.search(r"/p/ML[A-Z]\d", partes.path):
            return None
        encontrado = _ID_MELI.search(partes.path)
    if not encontrado:
        return None
    item = f"{encontrado.group(1)}{encontrado.group(2)}"
    try:
        contenido, _tipo, _charset, _final = _descargar(
            API_MELI.format(item), MAX_JSON, "application/json"
        )
        datos = json.loads(contenido)
    except (EnlaceNoPermitido, OSError, ValueError, http.client.HTTPException) as error:
        logger.info("La API de MercadoLibre no respondió para %s: %s", item, error)
        return None
    if not isinstance(datos, dict) or not isinstance(datos.get("title"), str):
        return None
    fotos = datos.get("pictures")
    primera = fotos[0] if isinstance(fotos, list) and fotos and isinstance(fotos[0], dict) else {}
    imagen = primera.get("secure_url") or primera.get("url")
    imagen = imagen or datos.get("secure_thumbnail") or datos.get("thumbnail")
    precio = normalizar_precio(datos.get("price"))
    moneda = datos.get("currency_id")
    return {
        "nombre_producto": datos["title"].strip()[:LARGO_NOMBRE],
        "precio_unitario": str(precio) if precio is not None else None,
        "moneda": moneda if isinstance(moneda, str) else None,
        "imagen": imagen if isinstance(imagen, str) else None,
        "descripcion": None,
    }


# --- Punto de entrada --------------------------------------------------------


def _resultado(datos=None, motivo=None):
    """Arma la respuesta: sin datos útiles → motivo; precio en otra moneda → aviso."""
    if datos is None or not any(
        datos.get(clave) for clave in ("nombre_producto", "precio_unitario", "imagen")
    ):
        return {"datos": None, "motivo": motivo or "sin_datos", "aviso": None}
    aviso = None
    moneda = datos.get("moneda")
    if moneda and moneda != MONEDA_LOCAL and datos.get("precio_unitario"):
        # El pool es en pesos: no se completa. El comparador sí lo convierte, así
        # que el precio original viaja aparte en `precio_moneda`.
        datos = {**datos, "precio_unitario": None, "precio_moneda": datos["precio_unitario"]}
        aviso = f"La tienda publica el precio en {moneda}: cargalo en pesos."
    return {"datos": datos, "motivo": None, "aviso": aviso}


def _motivo_de(error):
    if isinstance(error, HostInexistente):
        return "no_disponible"
    if isinstance(error, EnlaceNoPermitido):
        return "no_permitido"
    if isinstance(error, HTTPError) and error.code in CODIGOS_BLOQUEO:
        return "bloqueado"
    return "no_disponible"


# Amazon no tiene tienda argentina: "$" a secas es la moneda del sitio.
MONEDAS_AMAZON = {
    "amazon.com.mx": "MXN",
    "amazon.com.br": "BRL",
    "amazon.ca": "CAD",
    "amazon.co.uk": "GBP",
    "amazon.es": "EUR",
    "amazon.de": "EUR",
    "amazon.fr": "EUR",
    "amazon.it": "EUR",
}


def _moneda_amazon(url):
    host = (urlsplit(url).hostname or "").removeprefix("www.")
    if not host.startswith("amazon."):
        return None
    return MONEDAS_AMAZON.get(host, "USD")


def leer_enlace(url):
    """`{"datos", "motivo", "aviso"}` del producto publicado en `url`. Nunca lanza."""
    try:
        return _leer_enlace(url)
    except Exception:  # red de seguridad: un HTML o JSON raro nunca es un 500
        logger.exception("Error inesperado leyendo el enlace %r", url)
        return _resultado(motivo="sin_datos")


def _leer_enlace(url):
    url = limpiar_enlace(url)
    datos_api = _datos_mercadolibre(url)
    if datos_api is not None:
        return _resultado(datos_api)
    try:
        contenido, tipo, charset, final = _descargar(
            url, MAX_HTML, "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8", truncar=True
        )
    except (EnlaceNoPermitido, OSError, ValueError, http.client.HTTPException) as error:
        logger.warning("No se pudo leer el enlace %r: %s", url, error)
        return _resultado(motivo=_motivo_de(error))
    if tipo and "html" not in tipo.lower():
        logger.warning("El enlace %r no es una página HTML (%s)", url, tipo)
        return _resultado(motivo="no_html")
    try:
        html = contenido.decode(charset, errors="replace")
    except LookupError:
        html = contenido.decode("utf-8", errors="replace")
    datos = extraer_datos(html, final)
    # Sin precio ni imagen y con pinta de captcha: la tienda nos frenó y lo único
    # leído es el <title> de la página de verificación. Muchas páginas normales
    # cargan reCAPTCHA, por eso no alcanza con encontrar la palabra.
    sin_producto = not datos["precio_unitario"] and not datos["imagen"]
    if sin_producto and re.search(
        r"robot check|validatecaptcha|captcha-delivery|cf-chl-|/captcha/|are you a human"
        r"|verifica que eres|no soy un robot",
        html[:50000],
        re.IGNORECASE,
    ):
        return _resultado(motivo="bloqueado")
    if datos["precio_unitario"] and not datos["moneda"]:
        datos["moneda"] = _moneda_amazon(final)
    return _resultado(datos)


def datos_de_enlace(url):
    """Solo los datos (o None): atajo para quien no necesita el motivo."""
    return leer_enlace(url)["datos"]


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
    # Misma conversión que las imágenes subidas (orientación EXIF, tamaño máximo).
    return normalizar_imagen(ContentFile(contenido, name="producto"))
