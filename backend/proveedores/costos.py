"""Costo final de una oferta (funciones puras, sin base de datos).

"Comparar el costo total, no solamente el precio publicado": por cada oferta se
calcula, para la cantidad que se quiere comprar,

    subtotal  = precio × max(cantidad, mínimo) × tipo de cambio
    envío     = costo de envío × tipo de cambio
    impuestos = subtotal × impuestos %            (impuestos locales que no estén en el precio)
    aduana    = solo importaciones: derechos + tasa estadística + IVA + percepciones,
                sobre una base aproximada (subtotal + envío)
    total     = subtotal + envío + impuestos + aduana

La aduana es una **estimación**: las alícuotas y el tipo de cambio son valores de
referencia que carga el staff (`ParametroCosto`), y el régimen real depende del
producto y del courier. La UI lo rotula así.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")
CIEN = Decimal(100)
MONEDA_LOCAL = "ARS"


def _pesos(valor):
    return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


@dataclass
class Parametros:
    tipos_cambio: dict = field(default_factory=dict)  # {"USD": Decimal("1200")}
    tasa_estadistica_pct: Decimal = Decimal(0)
    iva_importacion_pct: Decimal = Decimal(0)
    percepciones_pct: Decimal = Decimal(0)

    @classmethod
    def desde_valores(cls, valores):
        """`valores`: {clave: Decimal} de ParametroCosto (tipo_cambio_usd, iva_importacion_pct…)."""
        tipos = {
            clave.removeprefix("tipo_cambio_").upper(): valor
            for clave, valor in valores.items()
            if clave.startswith("tipo_cambio_") and valor and valor > 0
        }
        return cls(
            tipos_cambio=tipos,
            tasa_estadistica_pct=valores.get("tasa_estadistica_pct", Decimal(0)),
            iva_importacion_pct=valores.get("iva_importacion_pct", Decimal(0)),
            percepciones_pct=valores.get("percepciones_pct", Decimal(0)),
        )


def costo_oferta(oferta, cantidad, parametros):
    """Desglose del costo de `oferta` (dict o modelo) para comprar `cantidad` unidades.

    Devuelve `{"total": None, "falta": "tipo_cambio", ...}` si la oferta está en otra
    moneda y no hay tipo de cambio cargado: no se inventa una conversión.
    """
    leer = oferta.get if isinstance(oferta, dict) else lambda c, d=None: getattr(oferta, c, d)
    moneda = (leer("moneda") or MONEDA_LOCAL).upper()
    cantidad = max(int(cantidad or 1), 1)
    unidades = max(cantidad, int(leer("cantidad_minima") or 1))
    base = {"unidades": unidades, "moneda": moneda, "falta": None}

    if moneda == MONEDA_LOCAL:
        cambio = Decimal(1)
    else:
        cambio = parametros.tipos_cambio.get(moneda)
        if not cambio:
            return {**base, "falta": "tipo_cambio", "total": None, "por_unidad": None}

    precio = Decimal(leer("precio_unitario"))
    subtotal = precio * unidades * cambio
    envio = Decimal(leer("costo_envio") or 0) * cambio
    impuestos = subtotal * Decimal(leer("impuestos_pct") or 0) / CIEN

    aduana = None
    if leer("es_importacion"):
        base_aduana = subtotal + envio
        derechos = base_aduana * Decimal(leer("derechos_pct") or 0) / CIEN
        tasa = base_aduana * parametros.tasa_estadistica_pct / CIEN
        base_iva = base_aduana + derechos + tasa
        iva = base_iva * parametros.iva_importacion_pct / CIEN
        percepciones = base_iva * parametros.percepciones_pct / CIEN
        aduana = {
            "derechos": _pesos(derechos),
            "tasa_estadistica": _pesos(tasa),
            "iva": _pesos(iva),
            "percepciones": _pesos(percepciones),
            "total": _pesos(derechos + tasa + iva + percepciones),
        }

    total = subtotal + envio + impuestos + (aduana["total"] if aduana else 0)
    return {
        **base,
        "tipo_cambio": cambio if moneda != MONEDA_LOCAL else None,
        "subtotal": _pesos(subtotal),
        "envio": _pesos(envio),
        "impuestos": _pesos(impuestos),
        "aduana": aduana,
        "total": _pesos(total),
        # Lo que cuesta cada unidad que se quería (si el mínimo obliga a comprar
        # de más, el excedente se paga igual).
        "por_unidad": _pesos(total / cantidad),
    }


def comparar(ofertas, cantidad, parametros):
    """`[(oferta, costo)]` ordenado por costo total (sin total al final) y el resumen.

    Resumen: cantidad de ofertas, mejor total, promedio y ahorro de la mejor contra
    la más cara (todo en pesos, solo entre las que tienen total).
    """
    filas = [(oferta, costo_oferta(oferta, cantidad, parametros)) for oferta in ofertas]
    filas.sort(key=lambda fila: (fila[1]["total"] is None, fila[1]["total"] or 0))
    totales = [costo["total"] for _, costo in filas if costo["total"] is not None]
    resumen = {
        "ofertas": len(filas),
        "comparables": len(totales),
        "mejor_total": min(totales) if totales else None,
        "promedio": _pesos(sum(totales) / len(totales)) if totales else None,
        "ahorro": (max(totales) - min(totales)) if len(totales) > 1 else None,
    }
    return filas, resumen
