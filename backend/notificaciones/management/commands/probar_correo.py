"""Manda un correo de prueba para verificar la cuenta de servicio (SMTP).

    python manage.py probar_correo alguien@ejemplo.com

A diferencia del envío normal (fail-soft), acá el error se muestra entero: es
justamente lo que hay que ver para arreglar la configuración.
"""

from django.conf import settings
from django.core import mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Manda un correo de prueba con la configuración actual de EMAIL_*."

    def add_arguments(self, parser):
        parser.add_argument("destinatario", help="Email que recibe la prueba.")

    def handle(self, *args, destinatario, **options):
        mailer = settings.MAILERS.get("default", {})
        backend = mailer.get("BACKEND", "")
        opciones = mailer.get("OPTIONS", {})
        self.stdout.write(f"Backend: {backend}")
        if opciones:
            self.stdout.write(
                f"Servidor: {opciones.get('host')}:{opciones.get('port')} "
                f"(usuario: {opciones.get('username') or '-'})"
            )
        self.stdout.write(f"Remitente: {settings.DEFAULT_FROM_EMAIL}")
        if backend.endswith("console.EmailBackend"):
            self.stdout.write(
                self.style.WARNING(
                    "Sin EMAIL_HOST: el correo se imprime abajo en vez de enviarse."
                )
            )

        mensaje = mail.EmailMessage(
            "Prueba de correo de PoolShop",
            "Si te llegó este correo, la cuenta de notificaciones de PoolShop está bien "
            "configurada.",
            None,
            [destinatario],
        )
        try:
            mail.mailers.default.send_messages([mensaje])
        except Exception as error:
            raise CommandError(
                f"No se pudo enviar: {error!r}. Revisá EMAIL_HOST_USER y que "
                "EMAIL_HOST_PASSWORD sea una contraseña de aplicación de Gmail."
            ) from error
        self.stdout.write(self.style.SUCCESS(f"Correo enviado a {destinatario}."))
