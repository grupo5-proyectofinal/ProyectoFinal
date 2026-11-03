"""Genera fotos de prueba en varios formatos (JPG, PNG, HEIC de iPhone, WEBP).

Uso: backend/.venv/bin/python .claude/skills/poolshop-e2e/scripts/generar_imagenes.py <carpeta>
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw
from pillow_heif import register_heif_opener

register_heif_opener()

destino = Path(sys.argv[1] if len(sys.argv) > 1 else "e2e-imagenes")
destino.mkdir(parents=True, exist_ok=True)

for nombre, formato, color in (
    ("foto.jpg", "JPEG", "#de3535"),
    ("foto.png", "PNG", "#ea6a1f"),
    ("IMG_0001.HEIC", "HEIF", "#2f7d6d"),
    ("imagen_de_whatsapp.webp", "WEBP", "#3b5bdb"),
):
    imagen = Image.new("RGB", (640, 480), color)
    ImageDraw.Draw(imagen).text((20, 20), f"PoolShop e2e · {formato}", fill="white")
    imagen.save(destino / nombre, format=formato)
    print(destino / nombre)
