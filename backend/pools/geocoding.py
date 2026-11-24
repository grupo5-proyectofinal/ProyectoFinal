"""Geocodificación server-side con Nominatim (fail-soft, sin reintentos)."""

import hashlib
import http.client
import json
import logging
import threading
import time
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "PoolShop/1.0 (compra grupal; uso interno)"
TIMEOUT = 5
INTERVALO_MINIMO = 1.0  # segundos entre pedidos (política de uso de Nominatim)
DECIMALES = Decimal("0.000001")  # precisión de Pool.latitud/longitud

_lock = threading.Lock()
_ultimo_pedido = 0.0


def _respetar_cuota():
    """Espera lo necesario para no superar la cuota de 1 pedido por segundo."""
    global _ultimo_pedido
    with _lock:
        espera = _ultimo_pedido + INTERVALO_MINIMO - time.monotonic()
        if espera > 0:
            time.sleep(espera)
        _ultimo_pedido = time.monotonic()


def _coordenadas(resultado):
    """Convierte un resultado de Nominatim a Decimales válidos, o None."""
    try:
        latitud = Decimal(str(resultado["lat"]))
        longitud = Decimal(str(resultado["lon"]))
    except (KeyError, InvalidOperation, TypeError):
        return None
    if not (latitud.is_finite() and longitud.is_finite()):
        return None
    if not (-90 <= latitud <= 90 and -180 <= longitud <= 180):
        return None
    return latitud.quantize(DECIMALES), longitud.quantize(DECIMALES)


def geocodificar(direccion, ciudad):
    """Geocodifica ``direccion`` + ``ciudad``.

    Devuelve ``(latitud, longitud)`` como ``Decimal`` o ``None`` si no hay
    resultado, la respuesta es inválida o el servicio falla (fail-soft).
    """
    consulta = f"{direccion or ''}, {ciudad or ''}".strip(", ")
    if not consulta:
        return None
    url = f"{URL}?{urlencode({'q': consulta, 'format': 'json', 'limit': 1})}"
    _respetar_cuota()
    try:
        pedido = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(pedido, timeout=TIMEOUT) as respuesta:
            resultados = json.loads(respuesta.read().decode("utf-8"))
    except (OSError, ValueError, http.client.HTTPException) as error:
        # fail-soft: red, timeout, HTTP o JSON roto
        logger.warning("No se pudo geocodificar %r: %s", consulta, error)
        return None
    if not isinstance(resultados, list):
        logger.warning("Respuesta de geocodificación inesperada para %r", consulta)
        return None
    if not resultados:
        return None
    coords = _coordenadas(resultados[0])
    if coords is None:
        logger.warning("Coordenadas inválidas o fuera de rango para %r", consulta)
    return coords


MAX_SUGERENCIAS = 5
# Cuánto se recuerda una búsqueda: tipear la misma calle no vuelve a consultar el servicio.
CACHE_SEGUNDOS = 60 * 60
# Georef: API oficial de normalización de direcciones de Argentina (datos.gob.ar).
GEOREF_URL = "https://apis.datos.gob.ar/georef/api"
MINUSCULAS = {"de", "del", "la", "las", "los", "el", "y", "e"}


def _titulo(texto):
    """'AVENIDA SANTA FE' → 'Avenida Santa Fe' (Georef devuelve todo en mayúsculas)."""
    palabras = str(texto or "").lower().split()
    return " ".join(
        p if (i and p in MINUSCULAS) else p[:1].upper() + p[1:] for i, p in enumerate(palabras)
    )


def _pedir_json(url, parametros):
    """GET con timeout que devuelve el JSON, o None si algo falla (fail-soft)."""
    try:
        pedido = Request(f"{url}?{urlencode(parametros)}", headers={"User-Agent": USER_AGENT})
        with urlopen(pedido, timeout=TIMEOUT) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except (OSError, ValueError, http.client.HTTPException) as error:
        logger.warning("Falló la consulta a %s: %s", url, error)
        return None


def _ciudad_georef(item):
    for clave in ("localidad_censal", "departamento", "provincia"):
        nombre = (item.get(clave) or {}).get("nombre")
        if nombre:
            return _titulo(nombre)
    return ""


def _sugerencia_georef(item):
    """Una dirección (con altura y coordenadas) o una calle de Georef como sugerencia."""
    if not isinstance(item, dict):
        return None
    calle = (item.get("calle") or item).get("nombre") if isinstance(item, dict) else None
    if not calle:
        return None
    altura = (item.get("altura") or {}).get("valor")
    direccion = f"{_titulo(calle)} {altura}" if altura else _titulo(calle)
    ciudad = _ciudad_georef(item)
    provincia = _titulo((item.get("provincia") or {}).get("nombre"))
    ubicacion = item.get("ubicacion") or {}
    coords = _coordenadas({"lat": ubicacion.get("lat"), "lon": ubicacion.get("lon")})
    return {
        "direccion": direccion,
        "ciudad": ciudad,
        "etiqueta": ", ".join(p for p in (direccion, ciudad, provincia) if p),
        "latitud": str(coords[0]) if coords else None,
        "longitud": str(coords[1]) if coords else None,
    }


def _buscar_georef(consulta):
    """Sugerencias de Georef: direcciones si lo tipeado trae altura, calles si no.

    Devuelve None si el servicio falló (para probar con el respaldo) y [] si respondió
    sin resultados.
    """
    calle, _, ciudad = consulta.partition(",")
    calle = calle.strip()
    con_altura = any(caracter.isdigit() for caracter in calle)
    if con_altura:
        datos = _pedir_json(
            f"{GEOREF_URL}/direcciones", {"direccion": calle, "max": MAX_SUGERENCIAS}
        )
        items = datos.get("direcciones") if isinstance(datos, dict) else None
    else:
        datos = _pedir_json(f"{GEOREF_URL}/calles", {"nombre": calle, "max": MAX_SUGERENCIAS})
        items = datos.get("calles") if isinstance(datos, dict) else None
    if not isinstance(items, list):
        return None
    sugerencias = []
    for item in items:
        sugerencia = _sugerencia_georef(item)
        if sugerencia and sugerencia not in sugerencias:
            sugerencias.append(sugerencia)
    pista = ciudad.strip().lower()
    if pista:
        # Primero las de la ciudad que ya escribió, sin descartar las otras.
        sugerencias.sort(key=lambda s: pista not in s["etiqueta"].lower())
    return sugerencias


def _sugerencia(resultado):
    """Arma `{direccion, ciudad, etiqueta, latitud, longitud}` desde un resultado de Nominatim."""
    partes = resultado.get("address") or {}
    calle = partes.get("road") or partes.get("pedestrian") or partes.get("footway") or ""
    if not calle:
        return None
    numero = partes.get("house_number") or ""
    ciudad = (
        partes.get("city")
        or partes.get("town")
        or partes.get("village")
        or partes.get("municipality")
        or partes.get("suburb")
        or partes.get("state")
        or ""
    )
    coords = _coordenadas(resultado)
    return {
        "direccion": f"{calle} {numero}".strip(),
        "ciudad": ciudad,
        "etiqueta": str(resultado.get("display_name") or f"{calle} {numero}, {ciudad}")[:200],
        "latitud": str(coords[0]) if coords else None,
        "longitud": str(coords[1]) if coords else None,
    }


def _buscar_nominatim(consulta):
    """Respaldo: Nominatim (OpenStreetMap), con su cuota de 1 pedido por segundo."""
    _respetar_cuota()
    resultados = _pedir_json(
        URL,
        {
            "q": consulta,
            "format": "json",
            "addressdetails": 1,
            "countrycodes": "ar",
            "limit": MAX_SUGERENCIAS,
            "accept-language": "es",
        },
    )
    if not isinstance(resultados, list):
        return None
    sugerencias = []
    for resultado in resultados:
        sugerencia = _sugerencia(resultado) if isinstance(resultado, dict) else None
        if sugerencia and sugerencia not in sugerencias:
            sugerencias.append(sugerencia)
    return sugerencias


def sugerir_direcciones(consulta):
    """Direcciones de Argentina que coinciden con lo tipeado (autocompletado).

    Primero Georef (servicio oficial, sin cuota estricta); si falla o no encuentra,
    Nominatim. Fail-soft: si ninguno responde devuelve una lista vacía y el formulario
    sigue funcionando con la dirección escrita a mano.
    """
    from django.core.cache import cache

    normalizada = " ".join(consulta.lower().split())
    clave = "sugerir-direcciones-" + hashlib.sha1(normalizada.encode()).hexdigest()
    guardado = cache.get(clave)
    if guardado is not None:
        return guardado
    sugerencias = _buscar_georef(consulta)
    if not sugerencias:
        sugerencias = _buscar_nominatim(consulta)
    if sugerencias is None:
        return []
    cache.set(clave, sugerencias, CACHE_SEGUNDOS)
    return sugerencias
