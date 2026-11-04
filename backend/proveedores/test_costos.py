"""Cálculo del costo final (sin base de datos)."""

from decimal import Decimal

from .costos import Parametros, comparar, costo_oferta

D = Decimal
PARAMS = Parametros(
    tipos_cambio={"USD": D("1000")},
    tasa_estadistica_pct=D("3"),
    iva_importacion_pct=D("21"),
    percepciones_pct=D("0"),
)


def oferta(**datos):
    base = {
        "precio_unitario": "100",
        "moneda": "ARS",
        "cantidad_minima": 1,
        "costo_envio": "0",
        "impuestos_pct": "0",
        "es_importacion": False,
        "derechos_pct": "0",
    }
    return {**base, **datos}


def test_local_con_envio_e_impuestos():
    costo = costo_oferta(oferta(costo_envio="500", impuestos_pct="10"), 10, PARAMS)
    assert costo["subtotal"] == D("1000.00")
    assert costo["envio"] == D("500.00")
    assert costo["impuestos"] == D("100.00")
    assert costo["aduana"] is None
    assert costo["total"] == D("1600.00")
    assert costo["por_unidad"] == D("160.00")


def test_minimo_obliga_a_comprar_de_mas():
    costo = costo_oferta(oferta(cantidad_minima=12), 10, PARAMS)
    assert costo["unidades"] == 12
    assert costo["total"] == D("1200.00")
    assert costo["por_unidad"] == D("120.00")  # 1200 / 10 que se querían


def test_importacion_estima_aduana_por_separado():
    costo = costo_oferta(
        oferta(precio_unitario="10", moneda="USD", costo_envio="20", es_importacion=True, derechos_pct="20"),
        5,
        PARAMS,
    )
    # base = (10×5 + 20) USD × 1000 = 70.000; derechos 20 % = 14.000; tasa 3 % = 2.100
    # IVA 21 % sobre 86.100 = 18.081 → aduana 34.181
    assert costo["subtotal"] == D("50000.00")
    assert costo["envio"] == D("20000.00")
    assert costo["aduana"] == {
        "derechos": D("14000.00"),
        "tasa_estadistica": D("2100.00"),
        "iva": D("18081.00"),
        "percepciones": D("0.00"),
        "total": D("34181.00"),
    }
    assert costo["total"] == D("104181.00")


def test_moneda_sin_tipo_de_cambio_no_se_inventa():
    costo = costo_oferta(oferta(moneda="EUR"), 1, PARAMS)
    assert costo["total"] is None
    assert costo["falta"] == "tipo_cambio"


def test_comparar_ordena_por_total_no_por_precio():
    barata_con_envio = oferta(precio_unitario="90", costo_envio="500")  # 900 + 500 = 1400
    cara_sin_envio = oferta(precio_unitario="110")  # 1100
    sin_cambio = oferta(moneda="EUR")
    filas, resumen = comparar([barata_con_envio, sin_cambio, cara_sin_envio], 10, PARAMS)
    assert [costo["total"] for _, costo in filas] == [D("1100.00"), D("1400.00"), None]
    assert resumen == {
        "ofertas": 3,
        "comparables": 2,
        "mejor_total": D("1100.00"),
        "promedio": D("1250.00"),
        "ahorro": D("300.00"),
    }


def test_parametros_desde_valores():
    params = Parametros.desde_valores(
        {"tipo_cambio_usd": D("1200"), "tipo_cambio_eur": D("0"), "iva_importacion_pct": D("21")}
    )
    assert params.tipos_cambio == {"USD": D("1200")}  # 0 = no cargado
    assert params.iva_importacion_pct == D("21")
