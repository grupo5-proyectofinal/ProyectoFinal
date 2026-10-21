"""Envío de correos de PoolShop: HTML con el diseño de la marca + texto plano.

Un solo camino para todos los mails (verificación, bienvenida, contraseña,
notificaciones). Cada correo es un par de plantillas `correos/<nombre>.html` y
`correos/<nombre>.txt`; el HTML extiende `correos/base.html`.

Hay dos clases de correo:
- Transaccionales (verificar email, bienvenida, restablecer y contraseña
  cambiada): salen siempre, no dependen de las preferencias.
- Opcionales (notificaciones, confirmación de unión): solo si el usuario tiene
  `notificar_por_email`, y llevan un enlace de baja que funciona sin sesión.

El envío es fail-soft: un SMTP caído se loguea y nunca tumba el endpoint.
"""

import logging
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail, signing
from django.db import transaction
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

SALT_BAJA = "poolshop.baja-emails"


def moneda(valor):
    """Pesos en es-AR como en el front: 1500 -> "$ 1.500", 4599.9 -> "$ 4.599,90"."""
    entero, _, centavos = f"{Decimal(valor):,.2f}".partition(".")
    entero = entero.replace(",", ".")
    return f"$ {entero}" if centavos == "00" else f"$ {entero},{centavos}"


def enlace_baja(usuario):
    """Link firmado para dejar de recibir notificaciones por mail (sin login)."""
    token = signing.dumps({"u": usuario.pk}, salt=SALT_BAJA)
    return f"{settings.FRONTEND_URL}/baja-emails?token={token}"


def usuario_de_baja(token):
    """El usuario dueño del token de baja, o None si el token no es válido."""
    try:
        datos = signing.loads(token, salt=SALT_BAJA)
    except (signing.BadSignature, TypeError):
        return None
    pk = datos.get("u") if isinstance(datos, dict) else None
    return get_user_model().objects.filter(pk=pk).first()


def armar(usuario, asunto, plantilla, contexto=None, opcional=False):
    """Arma el correo para `usuario` con la plantilla `correos/<plantilla>`.

    `opcional=True` agrega el enlace de baja (en el cuerpo y como header
    List-Unsubscribe, que Gmail muestra como "Anular suscripción").
    """
    datos = {
        "usuario": usuario,
        "nombre": usuario.first_name or usuario.username,
        "frontend_url": settings.FRONTEND_URL,
        "asunto": asunto,
        **(contexto or {}),
    }
    headers = {}
    if opcional:
        datos["enlace_baja"] = enlace_baja(usuario)
        datos["enlace_preferencias"] = f"{settings.FRONTEND_URL}/notificaciones"
        headers["List-Unsubscribe"] = f"<{datos['enlace_baja']}>"
    texto = render_to_string(f"correos/{plantilla}.txt", datos).strip()
    html = render_to_string(f"correos/{plantilla}.html", datos)
    mensaje = mail.EmailMultiAlternatives(
        asunto, texto, None, [usuario.email], headers=headers
    )
    mensaje.attach_alternative(html, "text/html")
    return mensaje


def _mandar(mensajes):
    try:
        mail.mailers.default.send_messages(mensajes)
    except Exception:
        # El catch no queda vacío: logger.exception registra el traceback.
        logger.exception("No se pudieron enviar %s correo(s).", len(mensajes))


def enviar(mensajes, al_confirmar=False):
    """Manda los correos. `al_confirmar=True` espera a que cierre la transacción
    (para no avisar de algo que después se revierte)."""
    mensajes = [m for m in mensajes if m is not None]
    if not mensajes:
        return
    if al_confirmar:
        transaction.on_commit(lambda: _mandar(mensajes))
    else:
        _mandar(mensajes)


def quiere_mails(usuario):
    """¿El usuario acepta correos opcionales?"""
    return bool(usuario.email) and usuario.notificar_por_email
