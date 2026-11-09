"""Contador de intentos de login fallidos por cuenta.

Se cuentan solo los fallos: una contraseña correcta nunca queda bloqueada por
los intentos de otra persona. El email y el nombre de usuario de una misma
cuenta comparten el contador; un identificador inexistente también se cuenta
(por su hash) para no revelar qué cuentas existen.
"""

import hashlib

from django.core.cache import cache

from .identificadores import usuario_por_identificador

LIMITE_FALLOS = 20
VENTANA_SEGUNDOS = 60 * 60


def _clave(identificador):
    identificador = (identificador or "").strip().lower()
    usuario = usuario_por_identificador(identificador)
    ident = (
        f"u{usuario.pk}"
        if usuario is not None
        else hashlib.sha256(identificador.encode()).hexdigest()
    )
    return f"login_fallos_{ident}"


def login_bloqueado(identificador):
    """Solo se consulta después de un fallo; una clave correcta entra igual."""
    return cache.get(_clave(identificador), 0) > LIMITE_FALLOS


def registrar_fallo_login(identificador):
    clave = _clave(identificador)
    try:
        cache.incr(clave)
    except ValueError:
        # La clave no existía (o venció): arranca la ventana de una hora.
        cache.set(clave, 1, VENTANA_SEGUNDOS)


def limpiar_fallos_login(identificador):
    cache.delete(_clave(identificador))
