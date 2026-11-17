"""Comando `poblar_demo`: carga la demo por los endpoints reales, una sola vez."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from notificaciones.models import Notificacion
from pools.demo import datos
from pools.models import Category, Membership, Pool, Resena, SolicitudBaja
from users.models import User


@pytest.fixture
def demo(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.PRIVATE_MEDIA_ROOT = tmp_path / "privado"
    # Un pool "real" (de alguien que no es de la demo) abierto: la demo se suma.
    real = User.objects.create_user(
        username="real", email="real@example.com", password="x", dni="99999999"
    )
    pool_real = Pool.objects.create(
        titulo="Pool real",
        nombre_producto="Algo",
        categoria=Category.objects.get(nombre="Limpieza"),
        precio_unitario=100,
        cantidad_total=20,
        fecha_caducidad=timezone.localdate() + timedelta(days=10),
        direccion="Junín 1",
        ciudad="Corrientes",
        creador=real,
    )
    call_command("poblar_demo", stdout=StringIO())
    return pool_real


def _demo_pools():
    return Pool.objects.filter(creador__email__endswith="@" + datos.DOMINIO_EMAIL)


@pytest.mark.django_db
def test_poblar_demo_cubre_todos_los_estados_una_sola_vez(demo):
    assert User.objects.filter(email__endswith="@" + datos.DOMINIO_EMAIL).count() == 21
    admin = User.objects.get(username=datos.ADMIN["username"])
    assert admin.is_staff and admin.is_superuser
    assert admin.check_password(datos.CLAVE_DEMO)

    estados = set(_demo_pools().values_list("estado", flat=True))
    assert estados == set(Pool.Estado.values)
    pagos = set(Membership.objects.values_list("pago_estado", flat=True))
    assert pagos == set(Membership.PagoEstado.values)
    bajas = set(SolicitudBaja.objects.values_list("estado", flat=True))
    assert bajas == set(SolicitudBaja.Estado.values)

    for pool in _demo_pools().filter(estado=Pool.Estado.FINALIZADO):
        assert pool.resenas.exists()
    for pool in _demo_pools().prefetch_related("memberships"):
        assert pool.imagenes.exists()
        assert pool.latitud is not None
        if pool.estado == Pool.Estado.ABIERTO:
            assert pool.disponible > 0
            assert pool.fecha_caducidad > timezone.localdate()
        if pool.estado == Pool.Estado.LISTO:
            assert pool.disponible == 0
    assert Notificacion.objects.filter(leida=False).exists()
    assert Notificacion.objects.filter(leida=True).exists()
    # Se sumaron al pool real, sin completarlo.
    demo.refresh_from_db()
    assert demo.memberships.exists()
    assert demo.estado == Pool.Estado.ABIERTO

    # Correrlo de nuevo (cada arranque del servicio) no duplica nada.
    pools, resenas = _demo_pools().count(), Resena.objects.count()
    salida = StringIO()
    call_command("poblar_demo", stdout=salida)
    assert "ya está cargada" in salida.getvalue()
    assert _demo_pools().count() == pools
    assert Resena.objects.count() == resenas


@pytest.mark.django_db
def test_poblar_demo_borrar_deja_los_datos_reales(demo):
    call_command("poblar_demo", "--borrar", stdout=StringIO())
    assert not User.objects.filter(email__endswith="@" + datos.DOMINIO_EMAIL).exists()
    assert not _demo_pools().exists()
    demo.refresh_from_db()
    assert not demo.memberships.exists()
    assert User.objects.filter(username="real").exists()
