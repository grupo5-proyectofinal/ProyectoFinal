from django.apps import AppConfig


class PoolsConfig(AppConfig):
    name = 'pools'

    def ready(self):
        from config.imagenes import registrar_formatos, usar_campo_imagen

        registrar_formatos()
        usar_campo_imagen()
        from . import checks  # noqa: F401  (registra el check de carpetas de media)
