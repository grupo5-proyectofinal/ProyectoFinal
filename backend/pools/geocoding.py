"""Geocodificación server-side con Nominatim (fail-soft, sin reintentos)."""

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
