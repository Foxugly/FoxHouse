from django.core.management.base import BaseCommand

from parties.retention import purger


class Command(BaseCommand):
    help = "Efface les parties inactives (RETENTION_PARTIES_JOURS) et les sessions expirées."

    def handle(self, *args, **options):
        nombre = purger()
        self.stdout.write(f"{nombre} partie(s) effacée(s).")
