from django.core.management.base import BaseCommand

from ...models import expirar_vencidos


class Command(BaseCommand):
    help = "Cancela los pools abiertos cuya fecha de caducidad ya pasó."

    def handle(self, *args, **options):
        cancelados = expirar_vencidos()
        self.stdout.write(f"Pools cancelados: {len(cancelados)}.")
