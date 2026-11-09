from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from notificaciones.models import Notificacion
from pools.models import Category, Membership, Mensaje, Pool
from proveedores.models import Comparacion

User = get_user_model()
CLAVE = "Zq7!mN2pLxD"


@pytest.fixture
def cliente():
    return APIClient()


def _usuario(n):
    return User.objects.create_user(
        email=f"u{n}@example.com", username=f"u{n}", dni=f"3000000{n}", password=CLAVE,
        first_name="Ana", telefono="351555", ciudad="Córdoba",
    )


def _pool(creador, estado=Pool.Estado.ABIERTO):
    return Pool.objects.create(
        creador=creador, categoria=Category.objects.get_or_create(nombre="Prueba")[0],
        titulo="Yerba", nombre_producto="Yerba", precio_unitario="100.00",
        cantidad_total=10, fecha_caducidad=timezone.localdate() + timedelta(days=7),
        direccion="Calle 1", ciudad="Córdoba", estado=estado,
    )


def _login(cliente, usuario):
    r = cliente.post(reverse("login"), {"email": usuario.email, "password": CLAVE}, format="json")
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return r.data


def _baja(cliente, clave=CLAVE):
    return cliente.post(reverse("baja_cuenta"), {"password": clave}, format="json")


def test_baja_requiere_sesion(cliente, db):
    assert _baja(cliente).status_code == 401


def test_baja_con_clave_incorrecta(cliente, db):
    ana = _usuario(1)
    _login(cliente, ana)
    r = _baja(cliente, "otra")
    assert r.status_code == 400
    assert "password" in r.data
    ana.refresh_from_db()
    assert ana.is_active


@pytest.mark.parametrize("estado", [Pool.Estado.ABIERTO, Pool.Estado.LISTO, Pool.Estado.EN_CURSO])
def test_baja_bloqueada_con_pool_activo_propio_o_ajeno(cliente, db, estado):
    ana, bea = _usuario(1), _usuario(2)
    propio = _pool(ana, estado)
    ajeno = _pool(bea, estado)
    Membership.objects.create(pool=ajeno, usuario=ana, cantidad=1)
    _login(cliente, ana)
    r = _baja(cliente)
    assert r.status_code == 409
    por_id = {p["id"]: p for p in r.data["pools"]}
    assert por_id[propio.id]["organizador"] is True
    assert por_id[ajeno.id]["organizador"] is False
    ana.refresh_from_db()
    assert ana.is_active


def test_baja_anonimiza_y_conserva_el_historial_de_los_demas(cliente, db):
    ana, bea = _usuario(1), _usuario(2)
    terminado = _pool(bea, Pool.Estado.FINALIZADO)
    union = Membership.objects.create(
        pool=terminado, usuario=ana, cantidad=1, telefono="351555", mensaje="Hola"
    )
    Mensaje.objects.create(pool=terminado, autor=ana, texto="¡Gracias!")
    propio = _pool(ana, Pool.Estado.CANCELADO)
    Notificacion.objects.create(usuario=ana, tipo=Notificacion.Tipo.ESTADO, pool=terminado)
    Comparacion.objects.create(titulo="Suelta", creador=ana)
    del_pool = Comparacion.objects.create(titulo="Del pool", creador=ana, pool=propio)
    tokens = _login(cliente, ana)

    assert _baja(cliente).status_code == 204

    ana.refresh_from_db()
    assert not ana.is_active
    assert not ana.has_usable_password()
    assert ana.email == f"baja-{ana.pk}@poolshop.invalid"
    assert ana.username == f"eliminado-{ana.pk}"
    assert (ana.dni, ana.first_name, ana.telefono, ana.ciudad) == (
        f"baja-{ana.pk}", "Usuario eliminado", "", "",
    )
    union.refresh_from_db()
    assert (union.telefono, union.mensaje) == ("", "")
    assert Mensaje.objects.filter(pool=terminado).count() == 1
    assert Pool.objects.filter(pk=propio.pk).exists()
    assert not Notificacion.objects.filter(usuario=ana).exists()
    assert list(Comparacion.objects.filter(creador=ana)) == [del_pool]

    # Sesión cerrada: el access ya no sirve, el refresh tampoco y no puede volver a entrar.
    assert cliente.get(reverse("me")).status_code == 401
    otro = APIClient()
    r = otro.post(reverse("token_refresh"), {"refresh": tokens["refresh"]}, format="json")
    assert r.status_code == 401
    r = otro.post(reverse("login"), {"email": "u1@example.com", "password": CLAVE}, format="json")
    assert r.status_code == 401
    # Sin perfil público y fuera de la búsqueda.
    assert otro.get(reverse("usuario_perfil", args=[ana.pk])).status_code == 404
    assert otro.get(reverse("usuario_busqueda"), {"q": "u1"}).data["results"] == []


def test_el_email_y_dni_quedan_libres_para_registrarse_de_nuevo(cliente, db):
    ana = _usuario(1)
    _login(cliente, ana)
    assert _baja(cliente).status_code == 204
    nueva = _usuario(1)  # mismo email, usuario y DNI
    assert nueva.pk != ana.pk
