"""Archivos en Postgres (ARCHIVOS_EN_DB): almacenamiento, vista de /media/ y wiring."""
# ruff: noqa: F811 — los fixtures importados de tests.py se reciben como parámetros

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.test import RequestFactory

from .almacen import AlmacenDB, servir_media
from .models import AlmacenPrivado, ArchivoAlmacenado, almacen_privado
from .tests import imagen_bytes, user  # noqa: F401 — fixtures compartidos

pytestmark = pytest.mark.django_db


def pedir(path, **extra):
    return servir_media(RequestFactory().get(f"/media/{path}", **extra), path)


def test_guardar_y_leer_devuelve_los_mismos_bytes():
    almacen = AlmacenDB()
    nombre = almacen.save("pools/foto.jpg", ContentFile(b"contenido"))
    assert nombre == "pools/foto.jpg"
    assert almacen.exists(nombre)
    assert almacen.size(nombre) == len(b"contenido")
    with almacen.open(nombre) as archivo:
        assert archivo.read() == b"contenido"


def test_url_es_relativa_a_media():
    assert AlmacenDB().url("pools/foto.jpg") == "/media/pools/foto.jpg"


def test_mismo_nombre_no_pisa_el_archivo_anterior():
    almacen = AlmacenDB()
    primero = almacen.save("pools/foto.jpg", ContentFile(b"uno"))
    segundo = almacen.save("pools/foto.jpg", ContentFile(b"dos"))
    assert primero != segundo
    assert almacen.open(primero).read() == b"uno"
    assert almacen.open(segundo).read() == b"dos"


def test_borrar_quita_el_archivo_y_tolera_inexistentes():
    almacen = AlmacenDB()
    nombre = almacen.save("pools/foto.jpg", ContentFile(b"x"))
    almacen.delete(nombre)
    almacen.delete(nombre)  # no falla si ya no está
    almacen.delete("")
    assert not almacen.exists(nombre)


def test_archivo_inexistente_falla_como_un_filesystem():
    almacen = AlmacenDB()
    with pytest.raises(FileNotFoundError):
        almacen.open("pools/no-esta.jpg")
    with pytest.raises(FileNotFoundError):
        almacen.size("pools/no-esta.jpg")


def test_espacio_privado_y_publico_estan_separados():
    publico, privado = AlmacenDB(), AlmacenDB(privado=True)
    privado.save("comprobantes/c.pdf", ContentFile(b"%PDF-"))
    assert not publico.exists("comprobantes/c.pdf")
    assert privado.exists("comprobantes/c.pdf")


def test_media_sirve_la_imagen_con_su_tipo_y_cache():
    AlmacenDB().save("pools/foto.png", ContentFile(imagen_bytes("PNG")))
    respuesta = pedir("pools/foto.png")
    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "image/png"
    assert respuesta["Cache-Control"].startswith("public")
    assert respuesta.content == imagen_bytes("PNG")


def test_media_responde_304_si_el_navegador_ya_lo_tiene():
    AlmacenDB().save("pools/foto.png", ContentFile(imagen_bytes("PNG")))
    etag = pedir("pools/foto.png")["ETag"]
    respuesta = pedir("pools/foto.png", HTTP_IF_NONE_MATCH=etag)
    assert respuesta.status_code == 304
    assert not respuesta.content


def test_media_404_si_no_existe():
    from django.http import Http404

    with pytest.raises(Http404):
        pedir("pools/no-esta.png")


def test_media_nunca_entrega_comprobantes_privados():
    from django.http import Http404

    AlmacenDB(privado=True).save("comprobantes/c.png", ContentFile(b"secreto"))
    with pytest.raises(Http404):
        pedir("comprobantes/c.png")


def test_media_no_interpreta_como_pagina_un_archivo_que_no_es_imagen():
    # Regresión preventiva: un nombre .html con contenido de imagen no debe
    # servirse como text/html (XSS), solo como descarga.
    AlmacenDB().save("pools/x.html", ContentFile(b"<script>alert(1)</script>"))
    respuesta = pedir("pools/x.html")
    assert respuesta["Content-Type"] == "application/octet-stream"
    assert respuesta["Content-Disposition"] == "attachment"


def test_media_rechaza_metodos_que_no_son_de_lectura():
    respuesta = servir_media(
        RequestFactory().post("/media/pools/foto.png"), "pools/foto.png"
    )
    assert respuesta.status_code == 405


def test_imagefield_guarda_en_la_base_con_el_storage_por_defecto(settings, user):
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "pools.almacen.AlmacenDB"},
    }
    user.foto.save("perfil.jpg", ContentFile(imagen_bytes("JPEG")))
    assert ArchivoAlmacenado.objects.filter(
        nombre=user.foto.name, privado=False
    ).exists()
    assert user.foto.url.startswith("/media/users/perfil")
    user.foto.delete(save=False)
    assert not ArchivoAlmacenado.objects.exists()


def test_comprobantes_eligen_el_almacen_segun_el_entorno(settings):
    settings.ARCHIVOS_EN_DB = True
    en_db = almacen_privado()
    assert isinstance(en_db, AlmacenDB) and en_db.privado
    settings.ARCHIVOS_EN_DB = False
    en_disco = almacen_privado()
    assert isinstance(en_disco, AlmacenPrivado) and isinstance(
        en_disco, FileSystemStorage
    )
