"""Purge RGPD (OPERATIONS.md §3.25) : les parties sans activité depuis
`RETENTION_PARTIES_JOURS` jours sont effacées, ainsi que les sessions expirées."""

from datetime import timedelta
from importlib import import_module

from django.conf import settings
from django.utils import timezone

from parties.models import Partie


def purger(maintenant=None) -> int:
    """Efface les parties inactives et les sessions expirées ; renvoie le nombre de parties."""
    limite = (maintenant or timezone.now()) - timedelta(days=settings.RETENTION_PARTIES_JOURS)
    nombre, _ = Partie.objects.filter(modifie_le__lt=limite).delete()
    import_module(settings.SESSION_ENGINE).SessionStore.clear_expired()
    return nombre
