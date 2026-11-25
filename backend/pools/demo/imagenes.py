"""Imágenes de la demo, dibujadas con Pillow (sin red ni archivos externos).

- `portada`: la "foto" del producto de un pool (un paquete con el nombre y un
  ícono según la categoría) y una segunda vista de "compra por bulto".
- `avatar`: foto de perfil con las iniciales.
- `comprobante`: comprobante de transferencia en PNG (lo que sube un integrante).

Usa un subconjunto de Inter que viaja con el código (`fuentes/`): la imagen slim de
producción no tiene fuentes del sistema y la de Pillow no trae tildes.
"""

import hashlib
from functools import cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LADO = 900
FUENTES = Path(__file__).resolve().parent / "fuentes"

# Color base por categoría (y por su padre para las subcategorías).
COLORES = {
    "Limpieza": (46, 134, 193),
    "Higiene personal": (142, 68, 173),
    "Perfume": (192, 57, 139),
    "Bebidas": (146, 43, 33),
    "Hogar": (211, 84, 0),
    "Electrónica": (44, 62, 80),
    "Accesorios": (22, 160, 133),
    "Ropa": (39, 174, 96),
    "Remera": (39, 174, 96),
    "Buzo": (30, 132, 73),
    "Pantalón": (31, 97, 141),
    "Calzado": (120, 66, 18),
    "Zapatilla": (120, 66, 18),
    "Sandalias": (160, 90, 30),
    "Zapato": (90, 50, 20),
    "Otros": (183, 149, 11),
}
ICONOS = {
    "Limpieza": "botella",
    "Higiene personal": "tubo",
    "Perfume": "frasco",
    "Bebidas": "vino",
    "Hogar": "casa",
    "Electrónica": "rayo",
    "Accesorios": "celular",
    "Ropa": "remera",
    "Remera": "remera",
    "Buzo": "remera",
    "Pantalón": "pantalon",
    "Calzado": "zapatilla",
    "Zapatilla": "zapatilla",
    "Sandalias": "zapatilla",
    "Zapato": "zapatilla",
    "Otros": "caja",
}
AVATARES = [
    (231, 76, 60),
    (230, 126, 34),
    (241, 196, 15),
    (46, 204, 113),
    (26, 188, 156),
    (52, 152, 219),
    (155, 89, 182),
    (52, 73, 94),
]


@cache
def _fuente(tamano, negrita=False):
    nombre = "Inter-SemiBold.otf" if negrita else "Inter-Regular.otf"
    return ImageFont.truetype(str(FUENTES / nombre), tamano)


def _aclarar(color, factor):
    return tuple(int(c + (255 - c) * factor) for c in color)


def _oscurecer(color, factor):
    return tuple(int(c * (1 - factor)) for c in color)


def _degradado(color):
    arriba, abajo = _aclarar(color, 0.35), _oscurecer(color, 0.25)
    imagen = Image.new("RGB", (LADO, LADO), arriba)
    dibujo = ImageDraw.Draw(imagen)
    for y in range(LADO):
        t = y / (LADO - 1)
        dibujo.line(
            [(0, y), (LADO, y)],
            fill=tuple(int(a + (b - a) * t) for a, b in zip(arriba, abajo, strict=True)),
        )
    return imagen


def _partir(dibujo, texto, fuente, ancho):
    """Corta el texto en renglones que entran en `ancho` píxeles."""
    renglones, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if dibujo.textlength(prueba, font=fuente) <= ancho:
            actual = prueba
        else:
            if actual:
                renglones.append(actual)
            actual = palabra
    if actual:
        renglones.append(actual)
    return renglones


def _centrado(dibujo, y, texto, fuente, color):
    ancho = dibujo.textlength(texto, font=fuente)
    dibujo.text(((LADO - ancho) / 2, y), texto, font=fuente, fill=color)


def _icono(dibujo, tipo, cx, cy, color):
    """Ícono simple de la categoría, centrado en (cx, cy), de unos 220 px."""
    if tipo in ("botella", "vino"):
        cuello = 30 if tipo == "botella" else 22
        dibujo.rounded_rectangle([cx - 70, cy - 40, cx + 70, cy + 130], 30, fill=color)
        dibujo.rectangle([cx - cuello, cy - 120, cx + cuello, cy - 30], fill=color)
        dibujo.rectangle([cx - cuello - 6, cy - 135, cx + cuello + 6, cy - 115], fill=color)
        dibujo.rectangle([cx - 50, cy + 10, cx + 50, cy + 80], fill="white")
    elif tipo == "tubo":
        dibujo.polygon(
            [(cx - 80, cy - 110), (cx + 80, cy - 110), (cx + 55, cy + 100), (cx - 55, cy + 100)],
            fill=color,
        )
        dibujo.rectangle([cx - 25, cy + 100, cx + 25, cy + 135], fill=color)
        dibujo.rectangle([cx - 80, cy - 125, cx + 80, cy - 110], fill=_oscurecer(color, 0.3))
    elif tipo == "frasco":
        dibujo.rounded_rectangle([cx - 85, cy - 50, cx + 85, cy + 130], 25, fill=color)
        dibujo.rectangle([cx - 25, cy - 90, cx + 25, cy - 50], fill=color)
        dibujo.ellipse([cx - 45, cy - 150, cx + 45, cy - 85], fill=_oscurecer(color, 0.3))
    elif tipo == "casa":
        dibujo.polygon([(cx - 130, cy - 10), (cx, cy - 130), (cx + 130, cy - 10)], fill=color)
        dibujo.rectangle([cx - 95, cy - 10, cx + 95, cy + 130], fill=color)
        dibujo.rectangle([cx - 30, cy + 40, cx + 30, cy + 130], fill="white")
    elif tipo == "rayo":
        dibujo.polygon(
            [
                (cx + 20, cy - 140),
                (cx - 80, cy + 15),
                (cx - 5, cy + 15),
                (cx - 30, cy + 140),
                (cx + 80, cy - 20),
                (cx + 5, cy - 20),
            ],
            fill=color,
        )
    elif tipo == "celular":
        dibujo.rounded_rectangle([cx - 70, cy - 135, cx + 70, cy + 135], 25, fill=color)
        dibujo.rounded_rectangle([cx - 55, cy - 110, cx + 55, cy + 100], 10, fill="white")
        dibujo.ellipse([cx - 10, cy + 110, cx + 10, cy + 128], fill="white")
    elif tipo == "remera":
        dibujo.polygon(
            [
                (cx - 50, cy - 120),
                (cx - 140, cy - 70),
                (cx - 105, cy - 10),
                (cx - 75, cy - 30),
                (cx - 75, cy + 130),
                (cx + 75, cy + 130),
                (cx + 75, cy - 30),
                (cx + 105, cy - 10),
                (cx + 140, cy - 70),
                (cx + 50, cy - 120),
                (cx + 25, cy - 95),
                (cx - 25, cy - 95),
            ],
            fill=color,
        )
    elif tipo == "pantalon":
        dibujo.polygon(
            [
                (cx - 85, cy - 130),
                (cx + 85, cy - 130),
                (cx + 105, cy + 135),
                (cx + 20, cy + 135),
                (cx, cy - 20),
                (cx - 20, cy + 135),
                (cx - 105, cy + 135),
            ],
            fill=color,
        )
    elif tipo == "zapatilla":
        dibujo.polygon(
            [
                (cx - 140, cy + 60),
                (cx - 130, cy - 70),
                (cx - 50, cy - 70),
                (cx - 20, cy - 10),
                (cx + 110, cy + 20),
                (cx + 145, cy + 60),
            ],
            fill=color,
        )
        dibujo.rectangle([cx - 145, cy + 60, cx + 150, cy + 90], fill=_oscurecer(color, 0.4))
    else:  # caja
        dibujo.polygon([(cx - 120, cy - 60), (cx, cy - 120), (cx + 120, cy - 60), (cx, cy)],
                       fill=_aclarar(color, 0.3))
        dibujo.polygon([(cx - 120, cy - 60), (cx, cy), (cx, cy + 130), (cx - 120, cy + 70)],
                       fill=color)
        dibujo.polygon([(cx + 120, cy - 60), (cx, cy), (cx, cy + 130), (cx + 120, cy + 70)],
                       fill=_oscurecer(color, 0.25))


def _jpeg(imagen):
    salida = BytesIO()
    imagen.save(salida, format="JPEG", quality=85, optimize=True)
    return salida.getvalue()


def portada(nombre_producto, categoria, padre=None, presentacion="", vista=0):
    """JPEG del producto. `vista=1` es la segunda imagen (cajas apiladas, "por bulto")."""
    base = COLORES.get(categoria) or COLORES.get(padre) or COLORES["Otros"]
    icono = ICONOS.get(categoria) or ICONOS.get(padre) or "caja"
    imagen = _degradado(base if vista == 0 else _oscurecer(base, 0.15))
    dibujo = ImageDraw.Draw(imagen)
    oscuro = _oscurecer(base, 0.55)

    # Tarjeta blanca central, como el frente de un paquete.
    dibujo.rounded_rectangle([90, 90, LADO - 90, LADO - 90], 48, fill=(255, 255, 255))
    etiqueta = (padre + " · " + categoria) if padre else categoria
    fuente_etiqueta = _fuente(28, negrita=True)
    ancho = dibujo.textlength(etiqueta.upper(), font=fuente_etiqueta) + 48
    dibujo.rounded_rectangle(
        [(LADO - ancho) / 2, 130, (LADO + ancho) / 2, 182], 26, fill=_aclarar(base, 0.75)
    )
    _centrado(dibujo, 140, etiqueta.upper(), fuente_etiqueta, oscuro)

    if vista == 0:
        _icono(dibujo, icono, LADO // 2, 360, base)
    else:
        # Bulto: tres paquetes apilados con el ícono chico.
        for dx, dy in ((-150, 60), (150, 60), (0, -40)):
            x, y = LADO // 2 + dx, 360 + dy
            dibujo.rounded_rectangle([x - 110, y - 90, x + 110, y + 90], 18,
                                     fill=_aclarar(base, 0.6), outline=base, width=6)
            dibujo.line([x - 110, y - 20, x + 110, y - 20], fill=base, width=6)

    # Angosto: la ficha del pool recorta los costados de la imagen (formato vertical).
    fuente_nombre = _fuente(42, negrita=True)
    renglones = _partir(dibujo, nombre_producto, fuente_nombre, 500)[:3]
    y = 560
    for renglon in renglones:
        _centrado(dibujo, y, renglon, fuente_nombre, oscuro)
        y += 54
    if presentacion:
        _centrado(dibujo, y + 14, presentacion, _fuente(32), base)
    pie = "Compra mayorista en grupo" if vista == 0 else "Precio por volumen · PoolShop"
    _centrado(dibujo, LADO - 150, pie, _fuente(28), (130, 130, 130))
    return _jpeg(imagen)


def _color_de(texto):
    indice = int(hashlib.sha256(texto.encode()).hexdigest(), 16) % len(AVATARES)
    return AVATARES[indice]


def avatar(nombre, apellido):
    """JPEG cuadrado con las iniciales sobre un color fijo por persona."""
    lado = 400
    color = _color_de(nombre + apellido)
    imagen = Image.new("RGB", (lado, lado), _aclarar(color, 0.15))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.ellipse([-80, 220, lado + 80, lado + 300], fill=_oscurecer(color, 0.15))
    iniciales = (nombre[:1] + apellido[:1]).upper()
    fuente = _fuente(170, negrita=True)
    ancho = dibujo.textlength(iniciales, font=fuente)
    dibujo.text(((lado - ancho) / 2, 90), iniciales, font=fuente, fill="white")
    return _jpeg(imagen)


def comprobante(monto, origen, destino_alias, titular, fecha, operacion):
    """PNG de un comprobante de transferencia bancaria."""
    ancho, alto = 720, 1080
    imagen = Image.new("RGB", (ancho, alto), (246, 247, 249))
    dibujo = ImageDraw.Draw(imagen)
    verde = (0, 150, 110)
    dibujo.rectangle([0, 0, ancho, 170], fill=verde)
    dibujo.ellipse([ancho / 2 - 45, 40, ancho / 2 + 45, 130], fill="white")
    dibujo.line([(ancho / 2 - 22, 85), (ancho / 2 - 5, 105), (ancho / 2 + 25, 65)],
                fill=verde, width=10)

    def centro(y, texto, tamano, color=(40, 40, 40), negrita=False):
        fuente = _fuente(tamano, negrita)
        dibujo.text(((ancho - dibujo.textlength(texto, font=fuente)) / 2, y), texto,
                    font=fuente, fill=color)

    centro(200, "Transferencia enviada", 40, negrita=True)
    centro(260, monto, 64, verde, negrita=True)
    filas = [
        ("De", origen),
        ("Para", titular),
        ("Alias", destino_alias),
        ("Fecha", fecha),
        ("N.º de operación", operacion),
        ("Concepto", "Varios"),
    ]
    y = 380
    for etiqueta, valor in filas:
        dibujo.text((60, y), etiqueta, font=_fuente(26), fill=(120, 120, 120))
        dibujo.text((60, y + 34), valor, font=_fuente(32), fill=(30, 30, 30))
        dibujo.line([(60, y + 88), (ancho - 60, y + 88)], fill=(220, 220, 220), width=2)
        y += 100
    centro(alto - 70, "Comprobante generado para la demo de PoolShop", 22, (150, 150, 150))
    salida = BytesIO()
    imagen.save(salida, format="PNG", optimize=True)
    return salida.getvalue()
