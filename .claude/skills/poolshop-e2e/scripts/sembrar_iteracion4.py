"""Datos para los recorridos de la Iteración 4 (idempotente; reinicia los pools de prueba).

Uso: cd backend && .venv/bin/python manage.py shell < ../.claude/skills/poolshop-e2e/scripts/sembrar_iteracion4.py

Crea admin@, ana@ y beto@poolshop.test (clave Clave-segura-123) y estos pools, todos del admin:
- "E2E caducado": Caducado, con ana y beto (para extender el plazo y reconfirmar).
- "E2E baja": Listo, ana con el pago enviado (para pedir y resolver la baja con devolución).
- "E2E finalizado": Finalizado, con ana y un mensaje en el chat.
"""

from datetime import timedelta

from django.utils import timezone

from pools.models import Category, EventoPool, Mensaje, Membership, Pool, SolicitudBaja
from users.models import User

CLAVE = "Clave-segura-123"
usuarios = {}
for i, (email, staff) in enumerate(
    (("admin@poolshop.test", True), ("ana@poolshop.test", False), ("beto@poolshop.test", False))
):
    u, _ = User.objects.get_or_create(
        email=email, defaults={"username": email.split("@")[0], "dni": f"9100000{i}"}
    )
    u.set_password(CLAVE)
    u.email_verificado = True
    u.is_staff = u.is_superuser = staff
    u.save()
    usuarios[email.split("@")[0]] = u

admin, ana, beto = usuarios["admin"], usuarios["ana"], usuarios["beto"]
categoria = Category.objects.get(nombre="Ropa")
hoy = timezone.localdate()


def pool(titulo, estado, **extra):
    Pool.objects.filter(titulo=titulo).delete()
    datos = {
        "titulo": titulo,
        "nombre_producto": "Remera algodón",
        "categoria": categoria,
        "enlace": "https://tienda.example.com/remera",
        "precio_unitario": "8500.00",
        "cantidad_total": 10,
        "cantidad_creador": 1,
        "fecha_caducidad": hoy + timedelta(days=10),
        "direccion": "Belgrano 1200",
        "ciudad": "Corrientes",
        "creador": admin,
        "alias_cbu": "poolshop.admin.mp",
        "titular_cuenta": "Admin PoolShop",
        "tipo_pago": "transferencia",
        "estado": estado,
    }
    datos.update(extra)
    return Pool.objects.create(**datos)


caducado = pool("E2E caducado", Pool.Estado.CADUCADO, fecha_caducidad=hoy - timedelta(days=1))
Membership.objects.create(pool=caducado, usuario=ana, cantidad=2, telefono="3511111111")
Membership.objects.create(pool=caducado, usuario=beto, cantidad=2, telefono="3512222222")

baja = pool("E2E baja", Pool.Estado.LISTO, cantidad_total=3)
Membership.objects.create(
    pool=baja, usuario=ana, cantidad=2, telefono="3511111111",
    pago_estado=Membership.PagoEstado.ENVIADO,
)

final = pool("E2E finalizado", Pool.Estado.FINALIZADO, cantidad_total=3)
Membership.objects.create(pool=final, usuario=ana, cantidad=2, telefono="3511111111")
Mensaje.objects.create(pool=final, autor=ana, texto="Gracias por todo")
print("IDS", caducado.id, baja.id, final.id)
