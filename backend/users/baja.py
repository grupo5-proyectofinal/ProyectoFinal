"""Baja de cuenta por el propio usuario.

No se borra la fila: `User` es FK con CASCADE de pools, uniones, mensajes y
reseñas, y borrarla se llevaría puesto el historial de los demás. En cambio se
anonimiza (sin PII, sin foto, sin contraseña usable, inactiva) y se cierran
todas sus sesiones. Lo que solo era suyo (notificaciones, comparaciones
sueltas) sí se borra.
"""

from django.db import transaction
from django.db.models import Q
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from pools.models import Pool, SolicitudBaja

# Pools que todavía comprometen al usuario con otros: no puede irse en el medio.
ESTADOS_ACTIVOS = (
    Pool.Estado.ABIERTO,
    Pool.Estado.CADUCADO,
    Pool.Estado.RECONFIRMACION,
    Pool.Estado.LISTO,
    Pool.Estado.EN_CURSO,
)
# Bajas con devolución sin terminar: quien debe la plata (el creador) no se puede ir sin
# devolverla, y quien la espera tampoco sin recibirla o confirmarla.
BAJAS_SIN_CERRAR_CREADOR = (SolicitudBaja.Estado.PENDIENTE, SolicitudBaja.Estado.APROBADA)
BAJAS_SIN_CERRAR_INTEGRANTE = (
    SolicitudBaja.Estado.PENDIENTE,
    SolicitudBaja.Estado.APROBADA,
    SolicitudBaja.Estado.DEVUELTA,
)

NOMBRE_BAJA = "Usuario eliminado"


def pools_que_impiden_baja(usuario):
    """Pools que organiza o a los que está unido y que todavía lo comprometen: activos o con
    una devolución sin cerrar. Se le muestran para que sepa cuáles resolver."""
    activo = Q(estado__in=ESTADOS_ACTIVOS) & (Q(creador=usuario) | Q(memberships__usuario=usuario))
    debe = Q(creador=usuario, solicitudes_baja__estado__in=BAJAS_SIN_CERRAR_CREADOR)
    espera = Q(
        solicitudes_baja__usuario=usuario,
        solicitudes_baja__estado__in=BAJAS_SIN_CERRAR_INTEGRANTE,
    )
    pools = list(
        Pool.objects.filter(activo | debe | espera)
        .distinct()
        .order_by("-creado")
        .values("id", "titulo", "estado", "creador_id")
    )
    con_devolucion = set(
        Pool.objects.filter(debe | espera).values_list("id", flat=True)
    )
    for pool in pools:
        pool["devolucion_pendiente"] = pool["id"] in con_devolucion
    return pools


@transaction.atomic
def dar_de_baja(usuario):
    """Anonimiza la cuenta. Quien llama ya validó la contraseña y los pools activos."""
    pk = usuario.pk
    if usuario.foto:
        usuario.foto.delete(save=False)
    usuario.email = f"baja-{pk}@poolshop.invalid"
    usuario.username = f"eliminado-{pk}"
    usuario.dni = f"baja-{pk}"
    usuario.first_name = NOMBRE_BAJA
    usuario.last_name = ""
    usuario.telefono = usuario.genero = usuario.direccion = usuario.ciudad = ""
    usuario.is_active = False
    usuario.is_staff = usuario.is_superuser = False
    usuario.notificar_por_email = False
    usuario.set_unusable_password()
    usuario.save()
    usuario.groups.clear()
    usuario.user_permissions.clear()

    usuario.notificaciones.all().delete()
    # Las comparaciones sueltas eran privadas; la de un pool la siguen viendo sus integrantes.
    usuario.comparaciones.filter(pool__isnull=True).delete()
    # Los datos de contacto que dejó al unirse a pools ya terminados tampoco quedan.
    usuario.memberships.update(telefono="", mensaje="")

    pendientes = OutstandingToken.objects.filter(user=usuario).exclude(
        blacklistedtoken__isnull=False
    )
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=t) for t in pendientes], ignore_conflicts=True
    )
