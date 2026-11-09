"""Datos de prueba para los recorridos e2e (idempotente).

Uso: cd backend && .venv/bin/python manage.py shell < ../.claude/skills/poolshop-e2e/scripts/sembrar.py

Crea admin@poolshop.test (staff) y ana@poolshop.test con clave Clave-segura-123,
y un pool "Pool e2e de pagos" listo para pagar: lo organiza admin y ana reservó 2.
"""

from datetime import timedelta

from django.utils import timezone

from pools.models import Category, Membership, Pool
from users.models import User

CLAVE = "Clave-segura-123"
usuarios = {}
for i, (email, staff) in enumerate((("admin@poolshop.test", True), ("ana@poolshop.test", False))):
    u, _ = User.objects.get_or_create(
        email=email, defaults={"username": email.split("@")[0], "dni": f"9000000{i}"}
    )
    u.set_password(CLAVE)
    u.email_verificado = True
    u.is_staff = u.is_superuser = staff
    u.save()
    usuarios[email] = u

admin, ana = usuarios["admin@poolshop.test"], usuarios["ana@poolshop.test"]
pool, _ = Pool.objects.get_or_create(
    titulo="Pool e2e de pagos",
    defaults={
        "nombre_producto": "Remera algodón",
        "categoria": Category.objects.get(nombre="Ropa"),
        "precio_unitario": "8500.00",
        "cantidad_total": 3,
        "cantidad_creador": 1,
        "fecha_caducidad": timezone.localdate() + timedelta(days=10),
        "direccion": "Belgrano 1200",
        "ciudad": "Corrientes",
        "creador": admin,
        "alias_cbu": "poolshop.admin.mp",
        "titular_cuenta": "Admin PoolShop",
    },
)
Membership.objects.get_or_create(pool=pool, usuario=ana, defaults={"cantidad": 2})
Membership.objects.filter(pool=pool, usuario=ana).update(
    pago_estado=Membership.PagoEstado.PENDIENTE, comprobante=""
)
pool.estado = Pool.Estado.LISTO
pool.save(update_fields=["estado"])
# Comparador (Fase 3): tipo de cambio cargado para poder comparar importaciones.
from proveedores.models import ParametroCosto  # noqa: E402

ParametroCosto.objects.filter(clave="tipo_cambio_usd").update(valor=1000)

print(f"POOL_PAGOS={pool.pk}")
