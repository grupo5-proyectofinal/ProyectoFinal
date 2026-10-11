"""Análisis propio del enlace de tienda (Plan 3, Fase 2).

Heurísticas locales sobre el texto de la URL: no se hace fetch, DNS ni
deserialización del destino (sin SSRF), por eso el módulo no es
security-sensitive. El contrato de salida es estable
(``{nivel, validaciones: [{clave, ok, detalle}]}``) para poder enchufar más
adelante un servicio externo sin tocar la UI.
"""

import re
from collections import Counter
from urllib.parse import urlsplit

from django.db.models import Q

from .models import Pool

NIVEL_ALTO = "alto"
NIVEL_MEDIO = "medio"
NIVEL_BAJO = "bajo"

# Dominio repetido (al menos dos pools lo usan) = señal positiva de uso interno.
UMBRAL_USO_ALTO = 2
# Los enlaces guardados no superan los 200 caracteres del URLField; por encima
# de este umbral el enlace es inusualmente largo para una ficha de producto.
LARGO_MAX = 150

ACORTADORES = frozenset(
    {
        "bit.ly",
        "t.co",
        "goo.gl",
        "tinyurl.com",
        "ow.ly",
        "is.gd",
        "buff.ly",
        "cutt.ly",
        "rebrand.ly",
        "shorturl.at",
        "rb.gy",
        "s.id",
        "lnkd.in",
    }
)

TLD_SOSPECHOSOS = frozenset(
    {"tk", "ml", "ga", "cf", "gq", "xyz", "top", "click", "buzz", "work", "loan", "rest", "icu"}
)

_REGEX_IPV4 = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")
_REGEX_HOST = re.compile(r"[a-z0-9.-]+")

# Claves cuyo fallo baja el nivel: graves → "bajo", medias → "medio".
_FALLAS_GRAVES = frozenset({"formato", "ip_literal", "tld"})
_FALLAS_MEDIAS = frozenset({"https", "acortador", "longitud"})


def _validacion(clave, ok, detalle_ok, detalle_falla):
    """Entrada del contrato: `{clave, ok, detalle}` con el texto del resultado."""
    return {"clave": clave, "ok": ok, "detalle": detalle_ok if ok else detalle_falla}


def _partes(url):
    """(esquema, host, texto) normalizados, o None si no hay host que analizar.

    Scheme implícito → https; esquema y host en minúsculas. Es parseo puro:
    `urlsplit` no resuelve DNS ni contacta al destino.
    """
    if not isinstance(url, str) or not url.strip():
        return None
    texto = url.strip()
    if "://" not in texto:
        texto = f"https://{texto}"
    try:
        partes = urlsplit(texto)
    except ValueError:
        return None
    host = (partes.hostname or "").lower()
    if not host:
        return None
    return partes.scheme.lower(), host, texto


def _es_ip(host):
    """IPv4 con puntos o IPv6 (`urlsplit` devuelve el host sin corchetes)."""
    return ":" in host or bool(_REGEX_IPV4.fullmatch(host))


def _host_plausible(host):
    if _es_ip(host):
        return True
    return (
        bool(_REGEX_HOST.fullmatch(host))
        and "." in host
        and not host.startswith(".")
        and not host.endswith(".")
        and ".." not in host
    )


def _validacion_tld(host):
    if host.startswith("xn--") or ".xn--" in host:
        return _validacion(
            "tld", False, "", "El dominio usa un nombre internacional codificado (xn--)."
        )
    tld = host.split(".")[-1]
    if tld in TLD_SOSPECHOSOS:
        return _validacion(
            "tld", False, "", f"El dominio usa el TLD «.{tld}», frecuente en sitios maliciosos."
        )
    if len(host.split(".")) > 4:
        return _validacion("tld", False, "", "El dominio encadena demasiados subdominios.")
    return _validacion("tld", True, "El dominio no muestra patrones sospechosos.", "")


def _validacion_uso(uso):
    if uso >= UMBRAL_USO_ALTO:
        return _validacion(
            "uso", True, f"Uso alto: {uso} pools usan este dominio en PoolShop.", ""
        )
    return _validacion("uso", False, "", "Primer uso de este dominio en PoolShop.")


def _nivel(validaciones):
    """Fallas graves → bajo; medias → medio; sin fallas → alto.

    La validación `uso` es una señal aparte (no es un riesgo) y no altera el nivel.
    """
    fallas = {v["clave"] for v in validaciones if not v["ok"]}
    if fallas & _FALLAS_GRAVES:
        return NIVEL_BAJO
    if fallas & _FALLAS_MEDIAS:
        return NIVEL_MEDIO
    return NIVEL_ALTO


def analizar_enlace(url, uso=0):
    """Analiza el enlace y devuelve el contrato `{nivel, validaciones[]}`.

    `uso` es la cantidad de pools con el mismo dominio (la cuenta el caller).
    Una URL malformada devuelve nivel bajo con el detalle, nunca una excepción.
    """
    partes = _partes(url)
    if partes is None or not _host_plausible(partes[1]):
        return {
            "nivel": NIVEL_BAJO,
            "validaciones": [
                _validacion("formato", False, "", "El enlace no tiene un formato válido.")
            ],
        }
    esquema, host, texto = partes
    es_ip = _es_ip(host)
    acortador = host in ACORTADORES
    validaciones = [
        _validacion("formato", True, "El enlace tiene un formato válido.", ""),
        _validacion(
            "https",
            esquema == "https",
            "Usa HTTPS: la conexión viaja cifrada.",
            "No usa HTTPS: la conexión no está cifrada.",
        ),
        _validacion(
            "longitud",
            len(texto) <= LARGO_MAX,
            "Longitud habitual.",
            f"El enlace es inusualmente largo ({len(texto)} caracteres).",
        ),
        _validacion(
            "ip_literal",
            not es_ip,
            "Usa un dominio con nombre.",
            "Usa una dirección IP en lugar de un dominio.",
        ),
        _validacion(
            "acortador",
            not acortador,
            "No es un acortador conocido.",
            "Es un acortador: el destino real queda oculto.",
        ),
        _validacion_tld(host),
        _validacion_uso(uso),
    ]
    return {"nivel": _nivel(validaciones), "validaciones": validaciones}


def dominio_de(url):
    """El dominio normalizado (minúsculas, sin scheme) o None si no es analizable."""
    partes = _partes(url)
    if partes is None or not _host_plausible(partes[1]):
        return None
    return partes[1]


def conteos_dominio(enlaces):
    """Cantidad de pools por dominio normalizado, en una sola consulta.

    Pensado para lotes (una página de listado): el prefiltro SQL es grueso y el
    conteo exacto se hace en Python con `dominio_de`, así `tienda.com.ar` no
    cuenta enlaces de `tienda.com.ar.evil.com`.
    """
    dominios = {dominio for dominio in map(dominio_de, enlaces) if dominio}
    if not dominios:
        return {}
    candidatos = Q()
    for dominio in dominios:
        candidatos |= Q(enlace__icontains=dominio)
    conteos = Counter()
    for enlace in Pool.objects.filter(candidatos).values_list("enlace", flat=True):
        dominio = dominio_de(enlace)
        if dominio in dominios:
            conteos[dominio] += 1
    return dict(conteos)
