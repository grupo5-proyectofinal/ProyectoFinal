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


def _clave(atributos):
    """Clave estable de una combinación de variantes."""
    return tuple(sorted((str(nombre), str(valor)) for nombre, valor in (atributos or {}).items()))


def normalizar_reparto(atributos_pool, reparto, cantidad_total):
    """Valida el objetivo opcional por combinación y lo devuelve normalizado.

    `reparto` es `[{"atributos": {"Talle": "S"}, "cantidad": 6}]`. Puede asignar
    menos unidades que el total (el resto queda sin cupo por variante), pero no
    más. Sin variantes en el pool el reparto tiene que venir vacío.
    """
    if not reparto:
        return []
    if not atributos_pool:
        raise ValidationError({"reparto": "Este pool no tiene variantes para repartir."})
    if not isinstance(reparto, list) or len(reparto) > MAX_FILAS_DETALLE:
        raise ValidationError({"reparto": "Formato inválido."})
    totales = Counter()
    for fila in reparto:
        if not isinstance(fila, dict) or not isinstance(fila.get("atributos"), dict):
            raise ValidationError({"reparto": "Formato inválido."})
        try:
            unidades = int(fila.get("cantidad"))
        except (TypeError, ValueError):
            raise ValidationError({"reparto": "Cada variante necesita una cantidad."}) from None
        if unidades < 1:
            raise ValidationError({"reparto": "Cada variante necesita al menos 1 unidad."})
        clave = []
        for nombre, opciones in atributos_pool.items():
            valor = fila["atributos"].get(nombre)
            if valor not in opciones:
                raise ValidationError(
                    {"reparto": f"Elegí {nombre.lower()} de las opciones del pool."}
                )
            clave.append((nombre, valor))
        totales[tuple(clave)] += unidades
    suma = sum(totales.values())
    if cantidad_total is not None and suma > cantidad_total:
        raise ValidationError(
            {"reparto": f"El reparto suma {suma} y la cantidad total es {cantidad_total}."}
        )
    return [{"atributos": dict(clave), "cantidad": n} for clave, n in totales.items()]


def validar_cupo_variantes(pool, detalle, excluir=None):
    """Rechaza una reserva que supera el objetivo de su combinación.

    Solo aplica a las combinaciones con objetivo; las demás no tienen cupo
    propio y se controlan con el total del pool.
    """
    objetivos = {
        _clave(fila.get("atributos")): int(fila.get("cantidad") or 0)
        for fila in (pool.reparto or [])
    }
    if not objetivos or not detalle:
        return
    membresias = pool.memberships.all()
    if excluir is not None:
        membresias = membresias.exclude(pk=excluir.pk)
    reservado = Counter()
    for membresia in membresias:
        for fila in membresia.detalle or []:
            reservado[_clave(fila.get("atributos"))] += int(fila.get("cantidad") or 0)
    for fila in detalle:
        clave = _clave(fila.get("atributos"))
        if clave not in objetivos:
            continue
        disponible = objetivos[clave] - reservado[clave]
        if int(fila.get("cantidad") or 0) > disponible:
            orden = list(variantes_vigentes(pool))
            etiqueta = (
                " · ".join(
                    str(fila["atributos"].get(nombre) or "") for nombre in orden
                ).strip(" ·")
                or "esa variante"
            )
            restantes = max(disponible, 0)
            unidad = "unidad" if restantes == 1 else "unidades"
            raise ValidationError(
                {"detalle": f"Quedan {restantes} {unidad} de {etiqueta}."}
            )


def resumen(detalles):
    """Suma por variante de varias membresías: [(atributos, cantidad)], de más a menos."""
    totales = Counter()
    for detalle in detalles:
        for fila in detalle or []:
            totales[tuple(sorted(fila["atributos"].items()))] += fila["cantidad"]
    return [(dict(clave), n) for clave, n in totales.most_common()]
