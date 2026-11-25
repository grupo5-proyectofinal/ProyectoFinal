"""Recuerda a los integrantes que confirmen que recibieron el producto.

El pool no se puede cerrar hasta que confirman todos (Iteración 3: "El pool no se
debería cerrar hasta que los participantes confirmen la recepción"). Si alguien se
olvida, el pool queda trabado: cada DIAS días, mientras el pedido siga en curso,
le llega un aviso (en la app y por mail según sus preferencias).
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from notificaciones.models import Notificacion
from notificaciones.servicio import recordar_recepcion

from ...models import EventoPool, Pool

DIAS = 3


def pendientes_de_recordar(ahora=None):
    """[(pool, [usuarios])] a recordar ahora: pedidos en curso hace DIAS días o más,
    integrantes sin confirmar y sin un recordatorio en los últimos DIAS días."""
    ahora = ahora or timezone.now()
    limite = ahora - timedelta(days=DIAS)
    en_curso_hace_dias = EventoPool.objects.filter(
        tipo=EventoPool.Tipo.ESTADO, datos__estado=Pool.Estado.EN_CURSO, creado__lte=limite
    ).values("pool_id")
    pools = Pool.objects.filter(estado=Pool.Estado.EN_CURSO, pk__in=en_curso_hace_dias)
    resultado = []
    for pool in pools.prefetch_related("memberships__usuario"):
        recordados = set(
            Notificacion.objects.filter(
                pool=pool,
                tipo=Notificacion.Tipo.RECEPCION,
                datos__recordatorio=True,
                creado__gt=limite,
            ).values_list("usuario_id", flat=True)
        )
        usuarios = [
            m.usuario
            for m in pool.memberships.all()
            if m.recepcion_confirmada is None and m.usuario_id not in recordados
        ]
        if usuarios:
            resultado.append((pool, usuarios))
    return resultado


class Command(BaseCommand):
    help = "Recuerda confirmar la recepción a los integrantes de pedidos en curso."

    def handle(self, *args, **options):
        avisos = 0
        for pool, usuarios in pendientes_de_recordar():
            avisos += len(recordar_recepcion(pool, usuarios))
        self.stdout.write(f"Recordatorios de recepción: {avisos}.")
