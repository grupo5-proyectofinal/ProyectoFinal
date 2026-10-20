"""Alta de notificaciones a partir de lo que pasa en un pool.

Los hooks de `pools.views` llaman a estas funciones después de cada cambio. La
regla de destinatarios vive acá: participantes del pool (creador + miembros),
nunca quien provocó el cambio, y solo si su preferencia lo permite. El mail es
opcional (`notificar_por_email`), sale recién al confirmar la transacción y es
fail-soft: un SMTP caído se loguea y no tumba el endpoint.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import transaction

from .models import Notificacion

logger = logging.getLogger(__name__)

# Título y cuerpo por estado de destino. `{titulo}` es el título del pool.
TEXTOS_ESTADO = {
    "abierto": (
        "{titulo} volvió a estar abierto",
        "Se liberaron unidades: el pool acepta reservas otra vez.",
    ),
    "listo": (
        "{titulo} completó su cupo",
        "Ya se abrió el chat del grupo para coordinar pago y retiro.",
    ),
    "en_curso": (
        "Pedido confirmado en {titulo}",
        "El administrador hizo la compra. Te avisamos cuando esté para retirar.",
    ),
    "finalizado": (
        "{titulo} finalizó",
        "Ya podés calificar al administrador y a los participantes.",
    ),
    "cancelado": (
        "{titulo} fue cancelado",
        "El administrador canceló el pool: la compra no se va a concretar.",
    ),
}
TEXTO_EXPIRADO = (
    "{titulo} fue cancelado",
    "No se alcanzó el total de productos dentro del plazo.",
)
VISTA_PREVIA_MENSAJE = 140


def _participantes(pool):
    """Creador + miembros del pool, sin repetidos."""
    User = get_user_model()
    ids = {pool.creador_id, *pool.memberships.values_list("usuario_id", flat=True)}
    return User.objects.filter(id__in=ids, is_active=True)


def _nombre(usuario):
    completo = f"{usuario.first_name} {usuario.last_name}".strip()
    return completo or usuario.username


def _enlace(pool):
    return f"{settings.FRONTEND_URL}/pools/{pool.pk}"


def _enviar_mails(notificaciones):
    """Manda por mail las notificaciones de quienes lo pidieron, al confirmar."""
    mensajes = [
        mail.EmailMessage(
            f"PoolShop: {n.titulo}",
            f"{n.texto}\n\nMirá el pool: {_enlace(n.pool)}\n\n"
            "Podés cambiar qué avisos recibís desde la sección Notificaciones.",
            None,
            [n.usuario.email],
        )
        for n in notificaciones
        if n.usuario.notificar_por_email and n.usuario.email
    ]
    if not mensajes:
        return

    def enviar():
        try:
            mail.mailers.default.send_messages(mensajes)
        except Exception:
            logger.exception("No se pudieron enviar las notificaciones por mail.")

    transaction.on_commit(enviar)


def _crear(destinatarios, tipo, pool, titulo, texto, datos=None):
    notificaciones = Notificacion.objects.bulk_create(
        Notificacion(
            usuario=usuario, tipo=tipo, pool=pool, titulo=titulo, texto=texto, datos=datos or {}
        )
        for usuario in destinatarios
    )
    _enviar_mails(notificaciones)
    return notificaciones


def notificar_estado(pool, estado, actor=None, expirado=False):
    """Avisa a los participantes que el pool pasó a `estado`."""
    plantilla = TEXTO_EXPIRADO if expirado else TEXTOS_ESTADO.get(estado)
    if plantilla is None:
        return []
    destinatarios = _participantes(pool).filter(notificar_estados=True)
    if actor is not None:
        destinatarios = destinatarios.exclude(id=actor.id)
    titulo, texto = plantilla
    return _crear(
        list(destinatarios),
        Notificacion.Tipo.ESTADO,
        pool,
        titulo.format(titulo=pool.titulo),
        texto,
        {"estado": estado},
    )


def notificar_union(pool, miembro, cantidad):
    """Avisa al creador que alguien se sumó a su pool."""
    creador = pool.creador
    if not creador.notificar_miembros or creador.id == miembro.id:
        return []
    unidades = "unidad" if cantidad == 1 else "unidades"
    return _crear(
        [creador],
        Notificacion.Tipo.UNION,
        pool,
        f"{_nombre(miembro)} se unió a tu pool",
        f"Reservó {cantidad} {unidades} en {pool.titulo}.",
        {"cantidad": cantidad},
    )


def notificar_mensaje(mensaje):
    """Avisa a los demás participantes que hay un mensaje nuevo en el chat.

    Si el destinatario ya tiene un aviso de mensajes sin leer de ese pool, se
    actualiza (cantidad + último texto) en lugar de crear otro; el mail sale solo
    con el primero, para no mandar uno por mensaje.
    """
    pool = mensaje.pool
    destinatarios = (
        _participantes(pool).filter(notificar_mensajes=True).exclude(id=mensaje.autor_id)
    )
    autor = _nombre(mensaje.autor)
    texto = f"{autor}: {mensaje.texto}"[:VISTA_PREVIA_MENSAJE]
    nuevos = []
    for usuario in destinatarios:
        pendiente = Notificacion.objects.filter(
            usuario=usuario, pool=pool, tipo=Notificacion.Tipo.MENSAJE, leida=False
        ).first()
        if pendiente is None:
            nuevos.append(usuario)
            continue
        pendiente.cantidad += 1
        pendiente.titulo = f"{pendiente.cantidad} mensajes nuevos en {pool.titulo}"
        pendiente.texto = texto
        pendiente.save(update_fields=["cantidad", "titulo", "texto", "actualizado"])
    return _crear(
        nuevos,
        Notificacion.Tipo.MENSAJE,
        pool,
        f"{autor} escribió en {pool.titulo}",
        texto,
    )
