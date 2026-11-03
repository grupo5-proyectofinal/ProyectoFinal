"""Check de arranque: las carpetas de media tienen que existir y ser escribibles.

Si no, subir una foto o una imagen de pool falla con un 500 ("Error al cargar la
foto") y lo único que se ve es el error en el navegador. Con este check, `runserver`
y `manage.py check --deploy` lo dicen claro al arrancar, con la solución.
"""

import os
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Warning, register

CARPETAS = (
    ("MEDIA_ROOT", "fotos de perfil e imágenes de pools"),
    ("PRIVATE_MEDIA_ROOT", "comprobantes de pago"),
)


def preparar_carpeta(ruta):
    """Crea la carpeta si falta. Devuelve un mensaje de error o None."""
    try:
        Path(ruta).mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return f"no se pudo crear ({error.strerror})"
    if not os.access(ruta, os.W_OK | os.X_OK):
        return "existe pero el usuario que corre Django no puede escribir en ella"
    return None


@register()
def carpetas_de_media(app_configs=None, **kwargs):
    errores = []
    for nombre, uso in CARPETAS:
        ruta = getattr(settings, nombre, None)
        if not ruta:
            continue
        problema = preparar_carpeta(ruta)
        if problema:
            errores.append(
                Error(
                    f"{nombre} ({ruta}) {problema}: fallan las subidas de {uso}.",
                    hint=(
                        "Dale permisos al usuario del proceso (por ejemplo "
                        f"`sudo chown -R $USER {ruta}`) o apuntá {nombre} a otra carpeta "
                        "en .env. No hace falta chmod 777."
                    ),
                    id="pools.E001",
                )
            )
    return errores


@register(deploy=True)
def correo_en_produccion(app_configs=None, **kwargs):
    """Sin EMAIL_HOST los mails van a la consola: en producción nadie puede
    confirmar su email (el login lo exige) ni recuperar la contraseña."""
    mailers = getattr(settings, "MAILERS", {})
    backend = mailers.get("default", {}).get("BACKEND", "")
    if settings.DEBUG or not backend.endswith("console.EmailBackend"):
        return []
    return [
        Warning(
            "Los correos se imprimen en el log en vez de enviarse (falta EMAIL_HOST).",
            hint=(
                "Configurá EMAIL_HOST, EMAIL_HOST_USER y EMAIL_HOST_PASSWORD (contraseña de "
                "aplicación de Gmail). Probalo con `python manage.py probar_correo <email>`."
            ),
            id="pools.W001",
        )
    ]
