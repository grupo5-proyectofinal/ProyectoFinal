"""Almacenamiento de archivos en Postgres (`ARCHIVOS_EN_DB=true`).

Los servicios sin disco persistente (el plan free de Render) borran todo lo que
se escribe en el filesystem en cada deploy: se perdían las fotos de perfil, las
imágenes de los pools y los comprobantes de pago. Con este almacenamiento los
archivos viven en la base, que sí persiste, y la app no cambia: los modelos
siguen usando `ImageField`/`FileField`.

Hay dos espacios separados, igual que con las carpetas `MEDIA_ROOT` y
`PRIVATE_MEDIA_ROOT`: el público (se sirve en `/media/`) y el privado
(comprobantes: solo se entregan desde endpoints con permisos).
"""

import posixpath
from urllib.parse import urljoin

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.http import Http404, HttpResponse, HttpResponseNotModified
from django.utils.deconstruct import deconstructible
from django.utils.encoding import filepath_to_uri
from django.views.decorators.http import require_safe

# Solo se sirven como imagen estas extensiones: el resto baja como descarga, así
# un archivo con nombre `.html` nunca se interpreta como página.
TIPOS_IMAGEN = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
CACHE_SEGUNDOS = 3600


def _archivos():
    # Import diferido: el modelo vive en pools.models, que importa este módulo.
    from pools.models import ArchivoAlmacenado

    return ArchivoAlmacenado.objects


@deconstructible
class AlmacenDB(Storage):
    """`Storage` de Django que guarda cada archivo como una fila de Postgres."""

    def __init__(self, privado=False):
        self.privado = privado

    def _filas(self):
        return _archivos().filter(privado=self.privado)

    def _open(self, name, mode="rb"):
        fila = self._filas().filter(nombre=name).first()
        if fila is None:
            raise FileNotFoundError(name)
        return ContentFile(bytes(fila.contenido), name=name)

    def _save(self, name, content):
        datos = b"".join(content.chunks())
        _archivos().create(
            nombre=name, privado=self.privado, contenido=datos, tamano=len(datos)
        )
        return name

    def exists(self, name):
        return self._filas().filter(nombre=name).exists()

    def delete(self, name):
        if name:
            self._filas().filter(nombre=name).delete()

    def size(self, name):
        tamano = (
            self._filas().filter(nombre=name).values_list("tamano", flat=True).first()
        )
        if tamano is None:
            raise FileNotFoundError(name)
        return tamano

    def url(self, name):
        return urljoin(settings.MEDIA_URL, filepath_to_uri(name))

    def path(self, name):
        raise NotImplementedError(
            "Los archivos viven en la base de datos, no en el disco."
        )


@require_safe
def servir_media(request, path):
    """Entrega un archivo público (`/media/<path>`) desde la base.

    Reemplaza a `django.views.static.serve` cuando los archivos viven en Postgres.
    Nunca entrega el espacio privado. Responde 304 si el navegador ya lo tiene.
    """
    nombre = posixpath.normpath(path)
    fila = _archivos().defer("contenido").filter(privado=False, nombre=nombre).first()
    if fila is None:
        raise Http404("No existe el archivo.")

    etag = f'"{fila.pk}-{fila.tamano}"'
    cabeceras = {
        "ETag": etag,
        "Cache-Control": f"public, max-age={CACHE_SEGUNDOS}",
    }
    if request.headers.get("If-None-Match") == etag:
        respuesta = HttpResponseNotModified()
    else:
        extension = posixpath.splitext(nombre)[1].lower()
        tipo = TIPOS_IMAGEN.get(extension)
        contenido = _archivos().values_list("contenido", flat=True).get(pk=fila.pk)
        respuesta = HttpResponse(
            bytes(contenido), content_type=tipo or "application/octet-stream"
        )
        if tipo is None:
            respuesta["Content-Disposition"] = "attachment"
    for clave, valor in cabeceras.items():
        respuesta[clave] = valor
    return respuesta
