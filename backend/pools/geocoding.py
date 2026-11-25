"""Geocodificación server-side con Nominatim (fail-soft, sin reintentos)."""

import hashlib
import http.client
import json
import logging
import threading
import time
import unicodedata
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


MAX_SUGERENCIAS = 6
# Cuánto se recuerda una búsqueda: tipear la misma calle no vuelve a consultar el servicio.
CACHE_SEGUNDOS = 60 * 60
# La zona de una ciudad o de unas coordenadas cambia poco: se recuerda un día.
CACHE_ZONA_SEGUNDOS = 24 * 60 * 60
# Georef: API oficial de normalización de direcciones de Argentina (datos.gob.ar).
GEOREF_URL = "https://apis.datos.gob.ar/georef/api"
MINUSCULAS = {"de", "del", "la", "las", "los", "el", "y", "e"}


def _titulo(texto):
    """'AVENIDA SANTA FE' → 'Avenida Santa Fe' (Georef devuelve todo en mayúsculas)."""
    palabras = str(texto or "").lower().split()
    return " ".join(
        p if (i and p in MINUSCULAS) else p[:1].upper() + p[1:] for i, p in enumerate(palabras)
    )


def _normalizar(texto):
    """'Avenida Belgrano' → 'avenida belgrano', sin acentos, para comparar nombres."""
    sin_acentos = unicodedata.normalize("NFKD", str(texto or ""))
    return " ".join("".join(c for c in sin_acentos if not unicodedata.combining(c)).lower().split())


def _pedir_json(url, parametros):
    """GET con timeout que devuelve el JSON, o None si algo falla (fail-soft)."""
    try:
        pedido = Request(f"{url}?{urlencode(parametros)}", headers={"User-Agent": USER_AGENT})
        with urlopen(pedido, timeout=TIMEOUT) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except (OSError, ValueError, http.client.HTTPException) as error:
        logger.warning("Falló la consulta a %s: %s", url, error)
        return None


def _cacheado(clave, segundos, calcular):
    """Valor de la caché o, si no está, lo calcula y lo guarda (salvo que sea None)."""
    from django.core.cache import cache

    clave = "geo-" + hashlib.sha1(clave.encode()).hexdigest()
    guardado = cache.get(clave)
    if guardado is not None:
        return guardado
    valor = calcular()
    if valor is not None:
        cache.set(clave, valor, segundos)
    return valor


def _nombre(item, clave):
    valor = item.get(clave) if isinstance(item, dict) else None
    return (valor or {}).get("nombre") if isinstance(valor, dict) else None


def _id(item, clave):
    valor = item.get(clave) if isinstance(item, dict) else None
    return (valor or {}).get("id") if isinstance(valor, dict) else None


def _detalle(ciudad, provincia):
    """'Bahía Blanca, Buenos Aires'; si ciudad y provincia se llaman igual, una sola vez."""
    partes = []
    for parte in (ciudad, provincia):
        if parte and _normalizar(parte) not in {_normalizar(p) for p in partes}:
            partes.append(parte)
    return ", ".join(partes)


# --- Zona de quien busca --------------------------------------------------------------------
# Como en un buscador de mapas, las sugerencias cercanas van primero. La zona sale de las
# coordenadas del navegador (si la persona ya dio permiso) o de la ciudad que escribió o
# tiene en su perfil. Es {"provincia": id, "departamento": id | None}.


def _zona_por_coordenadas(latitud, longitud):
    datos = _pedir_json(f"{GEOREF_URL}/ubicacion", {"lat": latitud, "lon": longitud})
    ubicacion = datos.get("ubicacion") if isinstance(datos, dict) else None
    provincia = _id(ubicacion, "provincia")
    if not provincia:
        return None
    localidad = _titulo(_nombre(ubicacion, "municipio") or _nombre(ubicacion, "departamento") or "")
    return {
        "provincia": provincia,
        "departamento": _id(ubicacion, "departamento"),
        "localidad": localidad,
        "nombre": _detalle(localidad, _titulo(_nombre(ubicacion, "provincia") or "")),
    }


def _zona_por_ciudad(ciudad):
    datos = _pedir_json(
        f"{GEOREF_URL}/localidades",
        {
            "nombre": ciudad,
            "max": 1,
            "campos": "id,nombre,provincia.id,provincia.nombre,departamento.id",
        },
    )
    localidades = datos.get("localidades") if isinstance(datos, dict) else None
    if not localidades:
        # Una provincia escrita como ciudad ("Corrientes", "Tucumán") también sirve de zona.
        datos = _pedir_json(f"{GEOREF_URL}/provincias", {"nombre": ciudad, "max": 1})
        provincias = datos.get("provincias") if isinstance(datos, dict) else None
        if provincias and isinstance(provincias[0], dict) and provincias[0].get("id"):
            nombre = _titulo(provincias[0].get("nombre") or ciudad)
            return {
                "provincia": provincias[0]["id"],
                "departamento": None,
                "localidad": "",
                "nombre": nombre,
            }
        return None
    localidad = localidades[0]
    provincia = _id(localidad, "provincia")
    if not provincia:
        return None
    nombre_localidad = _titulo(localidad.get("nombre") or "")
    return {
        "provincia": provincia,
        "departamento": _id(localidad, "departamento"),
        "localidad": nombre_localidad,
        "nombre": _detalle(nombre_localidad, _titulo(_nombre(localidad, "provincia") or "")),
    }


def _coordenadas_validas(latitud, longitud):
    coords = _coordenadas({"lat": latitud, "lon": longitud}) if latitud and longitud else None
    # Argentina continental e insular, con margen: lo demás no sirve para acotar.
    if coords and -56 <= coords[0] <= -21 and -74 <= coords[1] <= -52:
        return coords
    return None


def zona_de(latitud=None, longitud=None, ciudad=""):
    """Zona para priorizar sugerencias, o None si no se pudo saber (fail-soft)."""
    coords = _coordenadas_validas(latitud, longitud)
    if coords:
        # Redondeado a ~1 km: alcanza para la zona y la caché se reutiliza.
        lat, lon = (round(float(c), 2) for c in coords)
        zona = _cacheado(
            f"zona-coords-{lat},{lon}",
            CACHE_ZONA_SEGUNDOS,
            lambda: _zona_por_coordenadas(lat, lon),
        )
        if zona:
            return zona
    ciudad = " ".join(str(ciudad or "").split())[:100]
    if len(ciudad) >= 3:
        return _cacheado(
            f"zona-ciudad-{_normalizar(ciudad)}",
            CACHE_ZONA_SEGUNDOS,
            lambda: _zona_por_ciudad(ciudad),
        )
    return None


# --- Georef ---------------------------------------------------------------------------------


def _sugerencia_georef(item):
    """Una dirección (con altura y coordenadas) o una calle de Georef como sugerencia."""
    if not isinstance(item, dict):
        return None
    calle = _nombre(item, "calle") or item.get("nombre")
    if not calle:
        return None
    altura = (
        (item.get("altura") or {}).get("valor") if isinstance(item.get("altura"), dict) else None
    )
    direccion = f"{_titulo(calle)} {altura}" if altura else _titulo(calle)
    ciudad = _titulo(
        _nombre(item, "localidad_censal") or _nombre(item, "departamento") or ""
    ) or _titulo(_nombre(item, "provincia") or "")
    provincia = _titulo(_nombre(item, "provincia") or "")
    detalle = _detalle(ciudad, provincia)
    ubicacion = item.get("ubicacion") or {}
    coords = _coordenadas({"lat": ubicacion.get("lat"), "lon": ubicacion.get("lon")})
    return {
        "direccion": direccion,
        "ciudad": ciudad,
        "detalle": detalle,
        "etiqueta": ", ".join(p for p in (direccion, detalle) if p),
        "con_altura": bool(altura),
        "latitud": str(coords[0]) if coords else None,
        "longitud": str(coords[1]) if coords else None,
        "_departamento": _id(item, "departamento"),
        "_localidad": _normalizar(ciudad),
        "_calle": _normalizar(calle),
    }


def _pedir_georef(calle, con_altura, filtros):
    if con_altura:
        datos = _pedir_json(f"{GEOREF_URL}/direcciones", {"direccion": calle, "max": 10, **filtros})
        items = datos.get("direcciones") if isinstance(datos, dict) else None
    else:
        datos = _pedir_json(f"{GEOREF_URL}/calles", {"nombre": calle, "max": 10, **filtros})
        items = datos.get("calles") if isinstance(datos, dict) else None
    if not isinstance(items, list):
        return None
    return [s for s in (_sugerencia_georef(item) for item in items) if s]


def _buscar_georef(calle, zona):
    """Sugerencias de Georef en la zona: primero el departamento, después la provincia.

    Sin zona no se usa: Georef no ordena por relevancia y devuelve calles homónimas de
    pueblos de todo el país. Devuelve None si el servicio falló y [] si no encontró.
    """
    con_altura = any(caracter.isdigit() for caracter in calle)
    nombre_calle = " ".join("".join(c for c in calle if not c.isdigit()).split())
    altura = "".join(c for c in calle if c.isdigit())
    pedidos = []
    if zona.get("departamento"):
        pedidos.append({"provincia": zona["provincia"], "departamento": zona["departamento"]})
    pedidos.append({"provincia": zona["provincia"]})
    sugerencias = None
    for filtros in pedidos:
        encontradas = _pedir_georef(calle, con_altura, filtros)
        if encontradas is None:
            continue
        sugerencias = sugerencias or []
        for sugerencia in encontradas:
            if sugerencia["etiqueta"] not in {s["etiqueta"] for s in sugerencias}:
                sugerencias.append(sugerencia)
        if len(sugerencias) >= MAX_SUGERENCIAS:
            break
    if sugerencias is None:
        return None
    if con_altura and not sugerencias and nombre_calle:
        # A Georef le faltan alturas de muchas calles: se sugiere la calle de la zona con el
        # número que escribió (las coordenadas se buscan al guardar el pool).
        for filtros in pedidos:
            calles = _pedir_georef(nombre_calle, False, filtros) or []
            for sugerencia in calles:
                sugerencia["direccion"] = f"{sugerencia['direccion']} {altura}"
                sugerencia["etiqueta"] = ", ".join(
                    p for p in (sugerencia["direccion"], sugerencia["detalle"]) if p
                )
                sugerencia["con_altura"] = True
                if sugerencia["etiqueta"] not in {s["etiqueta"] for s in sugerencias}:
                    sugerencias.append(sugerencia)
            if len(sugerencias) >= MAX_SUGERENCIAS:
                break
    # Georef también trae parecidas ("Beltrán" para "belgrano"): primero las que coinciden
    # con lo escrito y, entre ellas, las del mismo departamento.
    buscado = _normalizar(nombre_calle)
    localidad = _normalizar(zona.get("localidad"))
    sugerencias.sort(
        key=lambda s: (
            buscado not in s["_calle"],
            s["_departamento"] != zona.get("departamento"),
            bool(localidad) and s["_localidad"] != localidad,
            not s["_calle"].startswith(buscado),
        )
    )
    return sugerencias


# --- Nominatim (OpenStreetMap) --------------------------------------------------------------


def _sugerencia(resultado):
    """Arma la sugerencia desde un resultado de Nominatim."""
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
    direccion = f"{calle} {numero}".strip()
    detalle = _detalle(ciudad, partes.get("state") or "")
    coords = _coordenadas(resultado)
    return {
        "direccion": direccion,
        "ciudad": ciudad,
        "detalle": detalle,
        "etiqueta": ", ".join(p for p in (direccion, detalle) if p),
        "con_altura": bool(numero),
        "latitud": str(coords[0]) if coords else None,
        "longitud": str(coords[1]) if coords else None,
        "_departamento": None,
        "_localidad": _normalizar(ciudad),
        "_calle": _normalizar(calle),
    }


def _buscar_nominatim(calle, lugar=""):
    """Nominatim ordena por relevancia (las ciudades grandes primero): sirve sin zona."""
    _respetar_cuota()
    parametros = {
        "format": "json",
        "addressdetails": 1,
        "countrycodes": "ar",
        "limit": 10,
        "accept-language": "es",
    }
    if lugar:
        parametros["q"] = f"{calle}, {lugar}"
    elif any(c.isdigit() for c in calle):
        parametros["q"] = calle
    else:
        # Solo el nombre: la búsqueda por calle evita estaciones, barrios y comercios homónimos.
        parametros["street"] = calle
    resultados = _pedir_json(URL, parametros)
    if not isinstance(resultados, list):
        return None
    # Descarta lugares que coinciden por otro motivo (una estación "Belgrano" sobre otra calle).
    palabras = _normalizar("".join(c for c in calle if not c.isdigit())).split()
    sugerencias = []
    for resultado in resultados:
        sugerencia = _sugerencia(resultado) if isinstance(resultado, dict) else None
        # Alcanza con una palabra: a veces se escribe también la ciudad ("colon 100 cordoba").
        if not sugerencia or not any(p in sugerencia["_calle"] for p in palabras if len(p) > 2):
            continue
        if sugerencia["etiqueta"] not in {s["etiqueta"] for s in sugerencias}:
            sugerencias.append(sugerencia)
    return sugerencias


def _publicas(sugerencias):
    return [
        {clave: valor for clave, valor in s.items() if not clave.startswith("_")}
        for s in sugerencias[:MAX_SUGERENCIAS]
    ]


def sugerir_direcciones(consulta, ciudad="", latitud=None, longitud=None):
    """Direcciones de Argentina que coinciden con lo tipeado, las más cercanas primero.

    Con zona (coordenadas o ciudad) se busca en Georef dentro de esa zona; sin zona, o si
    Georef no encuentra nada, en Nominatim. Fail-soft: si ningún servicio responde devuelve
    una lista vacía y el formulario sigue funcionando con la dirección escrita a mano.
    """
    calle, _, ciudad_en_texto = consulta.partition(",")
    calle = " ".join(calle.split())
    ciudad = " ".join(str(ciudad or ciudad_en_texto).split())
    zona = zona_de(latitud, longitud, ciudad)

    def buscar():
        sugerencias = _buscar_georef(calle, zona) if zona else None
        if not sugerencias:
            lugar = zona["nombre"] if zona and zona.get("nombre") else ciudad
            sugerencias = _buscar_nominatim(calle, lugar)
        return None if sugerencias is None else _publicas(sugerencias)

    clave_zona = f"{zona['provincia']}-{zona.get('departamento')}" if zona else _normalizar(ciudad)
    resultado = _cacheado(
        f"sugerir-direcciones-{_normalizar(calle)}|{clave_zona}", CACHE_SEGUNDOS, buscar
    )
    return resultado or []
