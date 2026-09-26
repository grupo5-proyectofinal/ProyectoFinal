from datetime import timedelta
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from .models import Category, Membership, Pool, PoolImage

User = get_user_model()

PASSWORD = "Zq7!mN2pLxD"

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def imagen_bytes(formato):
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "red").save(buffer, format=formato)
    return buffer.getvalue()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="a@example.com", username="a", dni="10000001", password=PASSWORD
    )


@pytest.fixture
def otro(db):
    return User.objects.create_user(
        email="b@example.com", username="b", dni="10000002", password=PASSWORD
    )


@pytest.fixture
def categoria(db):
    return Category.objects.create(nombre="Prueba")


def autenticar(api_client, user):
    api_client.force_authenticate(user)


def payload(categoria, **overrides):
    data = {
        "titulo": "Pool de yerba",
        "nombre_producto": "Yerba 1kg",
        "descripcion": "Compra grupal",
        "categoria": categoria.id,
        "precio_unitario": "1500.00",
        "cantidad_total": 10,
        "cantidad_creador": 2,
        "min_por_integrante": 1,
        "fecha_caducidad": (timezone.localdate() + timedelta(days=7)).isoformat(),
        "tipo_pago": "efectivo",
        "direccion": "Calle 1",
        "ciudad": "Cordoba",
    }
    data.update(overrides)
    return data


def crear_pool(usuario, categoria, **overrides):
    datos = {
        "creador": usuario,
        "categoria": categoria,
        "titulo": "Pool",
        "nombre_producto": "Producto",
        "precio_unitario": "100.00",
        "cantidad_total": 10,
        "cantidad_creador": 2,
        "fecha_caducidad": timezone.localdate() + timedelta(days=7),
        "direccion": "Calle 1",
        "ciudad": "Cordoba",
    }
    datos.update(overrides)
    return Pool.objects.create(**datos)


def poner_estado(pool, estado):
    pool.estado = estado
    pool.save(update_fields=["estado"])
    return pool


@pytest.fixture
def pool(user, categoria):
    return crear_pool(user, categoria)


# --- Categorias ---


def test_categorias_sembradas(db):
    nombres = set(Category.objects.values_list("nombre", flat=True))
    assert {"Alimentos", "Bebidas", "Limpieza", "Hogar", "Electrónica", "Otros"} <= nombres


# --- Creacion y listado ---


def test_crear_pool_requiere_auth(api_client, categoria):
    response = api_client.post(reverse("pool-list"), payload(categoria), format="json")
    assert response.status_code == 401


def test_crear_pool_ok(api_client, user, categoria):
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-list"), payload(categoria), format="json")
    assert response.status_code == 201
    assert response.data["creador"]["id"] == user.id
    assert response.data["estado"] == "abierto"
    assert response.data["disponible"] == 8


def test_crear_pool_cantidad_creador_mayor_total(api_client, user, categoria):
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-list"), payload(categoria, cantidad_creador=11), format="json"
    )
    assert response.status_code == 400
    assert "cantidad_creador" in response.data


def test_crear_pool_fecha_pasada(api_client, user, categoria):
    autenticar(api_client, user)
    ayer = (timezone.localdate() - timedelta(days=1)).isoformat()
    response = api_client.post(
        reverse("pool-list"), payload(categoria, fecha_caducidad=ayer), format="json"
    )
    assert response.status_code == 400
    assert "fecha_caducidad" in response.data


def test_crear_pool_fecha_mas_de_30_dias(api_client, user, categoria):
    autenticar(api_client, user)
    lejos = (timezone.localdate() + timedelta(days=31)).isoformat()
    response = api_client.post(
        reverse("pool-list"), payload(categoria, fecha_caducidad=lejos), format="json"
    )
    assert response.status_code == 400
    assert "fecha_caducidad" in response.data


def test_list_publica_sin_token(api_client, pool):
    response = api_client.get(reverse("pool-list"))
    assert response.status_code == 200
    assert response.data["count"] == 1


def test_list_paginado(api_client, user, categoria):
    for i in range(13):
        crear_pool(user, categoria, titulo=f"Pool {i}")
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"))
    assert response.status_code == 200
    assert response.data["count"] == 13
    assert len(response.data["results"]) == 12


# --- Disponible ---


def test_disponible_resta_miembros(db, user, pool):
    Membership.objects.create(pool=pool, usuario=user, cantidad=3)
    assert pool.disponible == 5


def test_disponible_nunca_negativa(db, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=user, cantidad=20)
    assert pool.disponible == 0


# --- Filtros y ordering ---


def test_filtro_q(api_client, user, categoria):
    crear_pool(user, categoria, titulo="Yerba por mayor")
    crear_pool(user, categoria, titulo="Fideos")
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"), {"q": "yerba"})
    assert response.data["count"] == 1


def test_filtro_categoria(api_client, user, categoria):
    otra = Category.objects.create(nombre="Otra")
    crear_pool(user, categoria)
    crear_pool(user, otra)
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"), {"categoria": otra.id})
    assert response.data["count"] == 1


def test_filtro_precio(api_client, user, categoria):
    crear_pool(user, categoria, precio_unitario="100.00")
    crear_pool(user, categoria, precio_unitario="500.00")
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"), {"precio_min": 200, "precio_max": 600})
    assert response.data["count"] == 1


def test_filtro_ciudad(api_client, user, categoria):
    crear_pool(user, categoria, ciudad="Rosario")
    crear_pool(user, categoria, ciudad="Mendoza")
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"), {"ciudad": "rosar"})
    assert response.data["count"] == 1


def test_filtro_estado(api_client, user, categoria):
    crear_pool(user, categoria)
    poner_estado(crear_pool(user, categoria), Pool.Estado.CANCELADO)
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"), {"estado": "abierto"})
    assert response.data["count"] == 1


def test_ordering_precio(api_client, user, categoria):
    crear_pool(user, categoria, titulo="Caro", precio_unitario="900.00")
    crear_pool(user, categoria, titulo="Barato", precio_unitario="100.00")
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-list"), {"ordering": "precio_unitario"})
    titulos = [p["titulo"] for p in response.data["results"]]
    assert titulos == ["Barato", "Caro"]


# --- Detalle ---


def test_retrieve_incrementa_vistas(api_client, user, pool):
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.status_code == 200
    pool.refresh_from_db()
    assert pool.vistas == 1


def test_retrieve_devuelve_disponible_y_miembros(api_client, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.data["disponible"] == 5
    assert response.data["miembros"][0]["usuario"]["username"] == otro.username


# --- Edicion y borrado ---


def test_patch_no_creador_403(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"titulo": "Otro"}, format="json"
    )
    assert response.status_code == 403


def test_patch_creador_ok(api_client, user, pool):
    autenticar(api_client, user)
    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"titulo": "Nuevo"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["titulo"] == "Nuevo"


def test_patch_no_abierto_400(api_client, user, pool):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)
    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"titulo": "Nuevo"}, format="json"
    )
    assert response.status_code == 400


def test_patch_inmutable_con_miembros_400(api_client, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    autenticar(api_client, user)
    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"titulo": "Nuevo"}, format="json"
    )
    assert response.status_code == 400
    assert "titulo" in response.data


def test_delete_no_creador_403(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.delete(reverse("pool-detail", args=[pool.id]))
    assert response.status_code == 403


def test_delete_creador_ok(api_client, user, pool):
    autenticar(api_client, user)
    response = api_client.delete(reverse("pool-detail", args=[pool.id]))
    assert response.status_code == 204
    assert not Pool.objects.filter(pk=pool.pk).exists()


def test_delete_no_abierto_400(api_client, user, pool):
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)
    response = api_client.delete(reverse("pool-detail", args=[pool.id]))
    assert response.status_code == 400


# --- Unirse ---


def test_unirse_ok(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 3}, format="json"
    )
    assert response.status_code == 201
    assert Membership.objects.filter(pool=pool, usuario=otro, cantidad=3).exists()


def test_unirse_baja_disponible(api_client, otro, pool):
    autenticar(api_client, otro)
    api_client.post(reverse("pool-unirse", args=[pool.id]), {"cantidad": 3}, format="json")
    pool.refresh_from_db()
    assert pool.disponible == 5


def test_unirse_sobre_disponible_400(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 9}, format="json"
    )
    assert response.status_code == 400
    assert "cantidad" in response.data


def test_unirse_bajo_minimo_400(api_client, otro, categoria, user):
    pool = crear_pool(user, categoria, min_por_integrante=5)
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 2}, format="json"
    )
    assert response.status_code == 400
    assert "cantidad" in response.data


def test_unirse_creador_400(api_client, user, pool):
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1}, format="json"
    )
    assert response.status_code == 400


def test_unirse_duplicado_400(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1}, format="json"
    )
    assert response.status_code == 400


def test_unirse_no_abierto_400(api_client, otro, pool):
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 1}, format="json"
    )
    assert response.status_code == 400


def test_unirse_llena_cambia_a_listo(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.post(
        reverse("pool-unirse", args=[pool.id]), {"cantidad": 8}, format="json"
    )
    assert response.status_code == 201
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.LISTO


# --- Salir y editar membresia ---


def test_salir_ok(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, otro)
    response = api_client.delete(reverse("pool-salir", args=[pool.id]))
    assert response.status_code == 204
    pool.refresh_from_db()
    assert pool.disponible == 8


def test_salir_de_listo_vuelve_abierto(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=8)
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, otro)
    response = api_client.delete(reverse("pool-salir", args=[pool.id]))
    assert response.status_code == 204
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.ABIERTO


def test_salir_sin_membresia_400(api_client, otro, pool):
    autenticar(api_client, otro)
    response = api_client.delete(reverse("pool-salir", args=[pool.id]))
    assert response.status_code == 400


def test_mi_membresia_cambia_cantidad(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, otro)
    response = api_client.patch(
        reverse("pool-mi-membresia", args=[pool.id]), {"cantidad": 6}, format="json"
    )
    assert response.status_code == 200
    assert Membership.objects.get(pool=pool, usuario=otro).cantidad == 6
    assert response.data["disponible"] == 2


def test_mi_membresia_sobre_disponible_400(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, otro)
    response = api_client.patch(
        reverse("pool-mi-membresia", args=[pool.id]), {"cantidad": 9}, format="json"
    )
    assert response.status_code == 400
    assert "cantidad" in response.data


# --- Transiciones de estado ---


def test_confirmar_listo_a_en_curso(api_client, user, pool):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-confirmar", args=[pool.id]))
    assert response.status_code == 200
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.EN_CURSO


def test_confirmar_no_creador_403(api_client, otro, pool):
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, otro)
    response = api_client.post(reverse("pool-confirmar", args=[pool.id]))
    assert response.status_code == 403


def test_finalizar_en_curso(api_client, user, pool):
    poner_estado(pool, Pool.Estado.EN_CURSO)
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-finalizar", args=[pool.id]))
    assert response.status_code == 200
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.FINALIZADO


def test_cancelar_abierto(api_client, user, pool):
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-cancelar", args=[pool.id]))
    assert response.status_code == 200
    pool.refresh_from_db()
    assert pool.estado == Pool.Estado.CANCELADO


def test_cancelar_finalizado_400(api_client, user, pool):
    poner_estado(pool, Pool.Estado.FINALIZADO)
    autenticar(api_client, user)
    response = api_client.post(reverse("pool-cancelar", args=[pool.id]))
    assert response.status_code == 400


# --- mios / unidos ---


def test_mios(api_client, user, otro, categoria, pool):
    crear_pool(otro, categoria, titulo="De otro")
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-mios"))
    assert response.data["count"] == 1
    assert response.data["results"][0]["titulo"] == pool.titulo


def test_unidos(api_client, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    autenticar(api_client, otro)
    response = api_client.get(reverse("pool-unidos"))
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == pool.id


# --- Integrantes y mi_cantidad ---


def test_integrantes_cuenta_memberships(api_client, user, otro, categoria, pool):
    tercero = User.objects.create_user(
        email="c@example.com", username="c", dni="10000003", password=PASSWORD
    )
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    Membership.objects.create(pool=pool, usuario=tercero, cantidad=2)
    autenticar(api_client, user)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.data["integrantes"] == 2


def test_unidos_integrantes_no_se_limita_al_usuario(api_client, user, otro, categoria, pool):
    tercero = User.objects.create_user(
        email="c@example.com", username="c", dni="10000003", password=PASSWORD
    )
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    Membership.objects.create(pool=pool, usuario=tercero, cantidad=2)
    autenticar(api_client, otro)
    response = api_client.get(reverse("pool-unidos"))
    assert response.data["results"][0]["integrantes"] == 2


def test_mi_cantidad_null_y_con_valor(api_client, otro, pool):
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.data["mi_cantidad"] is None

    Membership.objects.create(pool=pool, usuario=otro, cantidad=3)
    autenticar(api_client, otro)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.data["mi_cantidad"] == 3


# --- Imagenes ---


def subir_imagen(api_client, pool):
    upload = SimpleUploadedFile("img.png", PNG_1X1, content_type="image/png")
    return api_client.post(
        reverse("pool-subir-imagen", args=[pool.id]), {"imagen": upload}, format="multipart"
    )


def test_subir_imagen_ok(api_client, user, pool, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    autenticar(api_client, user)
    response = subir_imagen(api_client, pool)
    assert response.status_code == 201
    assert pool.imagenes.count() == 1


def test_subir_imagen_limite_10(api_client, user, pool, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    for i in range(10):
        PoolImage.objects.create(pool=pool, imagen=f"pools/fake{i}.png")
    autenticar(api_client, user)
    response = subir_imagen(api_client, pool)
    assert response.status_code == 400


def test_subir_imagen_no_creador_403(api_client, otro, pool, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    autenticar(api_client, otro)
    response = subir_imagen(api_client, pool)
    assert response.status_code == 403


def test_borrar_imagen(api_client, user, pool, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    imagen = PoolImage.objects.create(pool=pool, imagen="pools/fake.png")
    autenticar(api_client, user)
    response = api_client.delete(reverse("pool-borrar-imagen", args=[pool.id, imagen.id]))
    assert response.status_code == 204
    assert pool.imagenes.count() == 0


def test_subir_imagen_formato_invalido(api_client, user, pool, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    archivo = SimpleUploadedFile("img.gif", imagen_bytes("GIF"), content_type="image/gif")
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-subir-imagen", args=[pool.id]), {"imagen": archivo}, format="multipart"
    )
    assert response.status_code == 400
    assert "imagen" in response.data


# --- Estado abierto/listo fuera de unirse ---


def test_crear_pool_lleno_queda_listo(api_client, user, categoria):
    autenticar(api_client, user)
    response = api_client.post(
        reverse("pool-list"),
        payload(categoria, cantidad_total=2, cantidad_creador=2),
        format="json",
    )
    assert response.status_code == 201
    assert response.data["disponible"] == 0
    assert response.data["estado"] == "listo"


def test_patch_creador_sobre_suscribe_400(api_client, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=5)
    autenticar(api_client, user)
    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"cantidad_creador": 6}, format="json"
    )
    assert response.status_code == 400
    assert "cantidad_creador" in response.data


def test_patch_creador_completa_queda_listo(api_client, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=5)
    autenticar(api_client, user)
    response = api_client.patch(
        reverse("pool-detail", args=[pool.id]), {"cantidad_creador": 5}, format="json"
    )
    assert response.status_code == 200
    assert response.data["disponible"] == 0
    assert response.data["estado"] == "listo"


def test_miembro_baja_cantidad_vuelve_abierto(api_client, user, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=5)
    poner_estado(pool, Pool.Estado.LISTO)
    autenticar(api_client, otro)
    response = api_client.patch(
        reverse("pool-mi-membresia", args=[pool.id]), {"cantidad": 4}, format="json"
    )
    assert response.status_code == 200
    assert response.data["disponible"] == 4
    assert response.data["estado"] == "abierto"


# --- Lecturas publicas y PII ---


def test_categorias_publicas_sin_token(api_client, categoria):
    response = api_client.get(reverse("category-list"))
    assert response.status_code == 200


def test_mios_requiere_auth(api_client):
    response = api_client.get(reverse("pool-mios"))
    assert response.status_code == 401


def test_detalle_publico_sin_email(api_client, otro, pool):
    Membership.objects.create(pool=pool, usuario=otro, cantidad=1)
    response = api_client.get(reverse("pool-detail", args=[pool.id]))
    assert response.status_code == 200
    assert "email" not in response.data["creador"]
    assert "email" not in response.data["miembros"][0]["usuario"]
