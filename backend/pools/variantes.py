"""Variantes de un pool (Ropa > Remera > Talle/Color).

Reglas puras (sin vistas ni requests) para que serializers y vistas compartan
un solo criterio:

- La categoría define los atributos posibles y sus opciones (`AtributoCategoria`,
  heredados del padre).
- El creador elige qué opciones ofrece en su pool: `Pool.atributos =
  {"Talle": ["S", "M"], "Color": ["Negro"]}`. Vacío = el pool no tiene variantes.
- Cada integrante reparte su cantidad entre variantes: `Membership.detalle =
  [{"atributos": {"Talle": "M", "Color": "Negro"}, "cantidad": 2}, ...]`.

El stock sigue siendo el total del pool (no hay stock por variante): el creador
pide al proveedor lo que suma el resumen.
"""

from collections import Counter

from rest_framework.exceptions import ValidationError

MAX_FILAS_DETALLE = 20


def validar_atributos_pool(categoria, atributos):
    """Normaliza y valida lo que ofrece el creador contra la categoría.

    Devuelve `{nombre: [opciones en el orden de la categoría]}` sin atributos
    vacíos. Lanza ValidationError con mensajes es-AR.
    """
    if not atributos:
        return {}
    if not isinstance(atributos, dict):
        raise ValidationError({"atributos": "Formato inválido."})
    definidos = {a.nombre: a.opciones for a in categoria.atributos_efectivos()} if categoria else {}
    limpio = {}
    for nombre, elegidas in atributos.items():
        if nombre not in definidos:
            raise ValidationError(
                {"atributos": f"La categoría {categoria} no tiene el atributo «{nombre}»."}
            )
        if not isinstance(elegidas, list) or not all(isinstance(v, str) for v in elegidas):
            raise ValidationError({"atributos": f"Elegí las opciones de {nombre} de la lista."})
        invalidas = [v for v in elegidas if v not in definidos[nombre]]
        if invalidas:
            raise ValidationError(
                {"atributos": f"«{invalidas[0]}» no es una opción de {nombre}."}
            )
        ordenadas = [v for v in definidos[nombre] if v in set(elegidas)]
        if ordenadas:
            limpio[nombre] = ordenadas
    return limpio


def variantes_vigentes(pool):
    """Lo que el pool ofrece hoy, ordenado como la categoría: `{nombre: [opciones]}`.

    Si una migración de catálogo sacó un atributo u opción, deja de ofrecerse acá
    y en la API a la vez: el front y la validación nunca piden algo distinto.
    """
    if not pool.atributos:
        return {}
    vigentes = {}
    for atributo in pool.categoria.atributos_efectivos():
        ofrecidas = pool.atributos.get(atributo.nombre) or []
        opciones = [v for v in atributo.opciones if v in ofrecidas]
        if opciones:
            vigentes[atributo.nombre] = opciones
    return vigentes


def mismo_detalle(a, b):
    """True si dos detalles piden lo mismo (sin importar el orden de las filas)."""

    def normal(detalle):
        return sorted(
            (tuple(sorted(f["atributos"].items())), f["cantidad"]) for f in detalle or []
        )

    return normal(a) == normal(b)


def validar_detalle(atributos_pool, detalle, cantidad):
    """Valida el reparto de `cantidad` entre variantes y devuelve el detalle limpio.

    Sin variantes en el pool el detalle se ignora (lista vacía). Con variantes es
    obligatorio, cada fila elige una opción ofrecida por atributo y las cantidades
    suman `cantidad`. Filas repetidas se agrupan.
    """
    if not atributos_pool:
        return []
    if not detalle:
        nombres = " y ".join(atributos_pool)
        raise ValidationError({"detalle": f"Elegí {nombres.lower()} de lo que vas a pedir."})
    if not isinstance(detalle, list) or len(detalle) > MAX_FILAS_DETALLE:
        raise ValidationError({"detalle": "Formato inválido."})
    totales = Counter()
    for fila in detalle:
        if not isinstance(fila, dict) or not isinstance(fila.get("atributos"), dict):
            raise ValidationError({"detalle": "Formato inválido."})
        try:
            unidades = int(fila.get("cantidad"))
        except (TypeError, ValueError):
            raise ValidationError({"detalle": "Cada variante necesita una cantidad."}) from None
        if unidades < 1:
            raise ValidationError({"detalle": "Cada variante necesita al menos 1 unidad."})
        elegidos = fila["atributos"]
        clave = []
        for nombre, opciones in atributos_pool.items():
            valor = elegidos.get(nombre)
            if valor not in opciones:
                raise ValidationError({"detalle": f"Elegí {nombre.lower()} de las opciones del pool."})
            clave.append((nombre, valor))
        totales[tuple(clave)] += unidades
    suma = sum(totales.values())
    if suma != cantidad:
        raise ValidationError(
            {"detalle": f"Las variantes suman {suma} y tu reserva es de {cantidad}."}
        )
    return [{"atributos": dict(clave), "cantidad": n} for clave, n in totales.items()]


def resumen(detalles):
    """Suma por variante de varias membresías: [(atributos, cantidad)], de más a menos."""
    totales = Counter()
    for detalle in detalles:
        for fila in detalle or []:
            totales[tuple(sorted(fila["atributos"].items()))] += fila["cantidad"]
    return [(dict(clave), n) for clave, n in totales.most_common()]
