"""Resolución del identificador de login (email o nombre de usuario)."""

from django.contrib.auth import get_user_model

User = get_user_model()


def usuario_por_identificador(identificador, **filtros):
    """Busca por email (prioridad) o por nombre de usuario, sin distinguir mayúsculas.

    El login acepta cualquiera de los dos; el email sigue siendo el USERNAME_FIELD.
    `order_by("pk")` hace determinista el resultado si ya existen duplicados por
    mayúsculas de datos viejos.
    """
    identificador = (identificador or "").strip()
    if not identificador:
        return None
    usuario = (
        User.objects.filter(email__iexact=identificador, **filtros)
        .order_by("pk")
        .first()
    )
    if usuario is None:
        usuario = (
            User.objects.filter(username__iexact=identificador, **filtros)
            .order_by("pk")
            .first()
        )
    return usuario
