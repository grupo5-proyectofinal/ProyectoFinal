"""Imágenes subidas por usuarios (foto de perfil, imágenes de pools).

Dos problemas que esto resuelve:

- **Formatos de celular:** las fotos de iPhone vienen en HEIC y muchas de Android
  o WhatsApp en WEBP/MPO. Antes se rechazaban ("Error al cargar la foto"). Ahora
  se aceptan y se convierten a JPEG; JPEG y PNG se guardan tal cual.
- **URLs de media:** DRF arma URLs absolutas con el Host del pedido
  (`http://<host>/media/...`). Detrás del proxy de Vite, entrando por la IP de
  la red o con otro host, esas URLs quedaban apuntando a un host que el
  navegador no alcanza. Se devuelven relativas (`/media/...`): el navegador las
  resuelve contra el mismo origen que sirvió la página, que siempre proxea /media.
"""

from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import models
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers

FORMATOS_DIRECTOS = {"JPEG", "PNG"}
# Lado máximo al convertir (las fotos de celular suelen tener 4000px o más).
LADO_MAXIMO = 2560
CALIDAD_JPEG = 85

MENSAJE_INVALIDA = "Subí una imagen válida (JPG, PNG, HEIC o WEBP)."


def registrar_formatos():
    """Habilita HEIC/HEIF en Pillow (fotos de iPhone). Idempotente."""
    try:
        from pillow_heif import register_heif_opener
    except ImportError:  # sin la dependencia, HEIC sigue rechazándose con un mensaje claro
        return
    register_heif_opener()


def _a_rgb(imagen):
    if imagen.mode in ("RGBA", "LA") or (imagen.mode == "P" and "transparency" in imagen.info):
        fondo = Image.new("RGB", imagen.size, (255, 255, 255))
        fondo.paste(imagen.convert("RGBA"), mask=imagen.convert("RGBA").getchannel("A"))
        return fondo
    return imagen.convert("RGB")


def normalizar_imagen(archivo):
    """Devuelve el archivo listo para guardar.

    JPEG y PNG pasan sin recodificar. Cualquier otro formato que Pillow pueda
    abrir (HEIC, WEBP, AVIF, GIF, BMP, MPO…) se convierte a JPEG, con la
    orientación EXIF aplicada y el lado mayor limitado a LADO_MAXIMO.
    Lanza OSError/UnidentifiedImageError si no es una imagen.
    """
    archivo.seek(0)
    with Image.open(archivo) as imagen:
        if imagen.format in FORMATOS_DIRECTOS:
            archivo.seek(0)
            return archivo
        imagen.load()
        convertida = ImageOps.exif_transpose(imagen)
        convertida.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
        salida = BytesIO()
        _a_rgb(convertida).save(salida, format="JPEG", quality=CALIDAD_JPEG, optimize=True)
    nombre = f"{Path(getattr(archivo, 'name', '') or 'imagen').stem}.jpg"
    return ContentFile(salida.getvalue(), name=nombre)


class CampoImagen(serializers.ImageField):
    """ImageField de DRF que acepta formatos de celular y devuelve URL relativa."""

    default_error_messages = {
        "invalid_image": MENSAJE_INVALIDA,
    }

    def to_internal_value(self, data):
        archivo = super().to_internal_value(data)
        try:
            return normalizar_imagen(archivo)
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            self.fail("invalid_image")

    def to_representation(self, value):
        if not value:
            return None
        try:
            return value.url
        except (AttributeError, ValueError):
            return None


def usar_campo_imagen():
    """Todos los ModelSerializer usan CampoImagen para los models.ImageField.

    `serializer_field_mapping` es el punto de extensión de DRF para esto; se
    cambia en el diccionario compartido para cubrir perfiles, pools e imágenes
    sin repetir el campo en cada serializer.
    """
    serializers.ModelSerializer.serializer_field_mapping[models.ImageField] = CampoImagen
