from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from parties.models import Partie
from parties.retention import purger


def _partie(jours):
    partie = Partie.objects.create(jeu="factice", joueur="a" * 32, sieges=[], etat={})
    Partie.objects.filter(pk=partie.pk).update(
        modifie_le=timezone.now() - timedelta(days=jours)
    )
    return partie


class PurgeTests(TestCase):
    def test_purge_les_parties_inactives(self):
        vieille, recente = _partie(31), _partie(29)
        self.assertEqual(purger(), 1)
        self.assertFalse(Partie.objects.filter(pk=vieille.pk).exists())
        self.assertTrue(Partie.objects.filter(pk=recente.pk).exists())

    def test_commande(self):
        _partie(31)
        sortie = StringIO()
        call_command("purger_parties", stdout=sortie)
        self.assertIn("1 partie(s) effacée(s).", sortie.getvalue())
        self.assertFalse(Partie.objects.exists())

    def test_purge_les_sessions_expirees(self):
        from django.contrib.sessions.models import Session

        Session.objects.create(
            session_key="x" * 32, session_data="", expire_date=timezone.now() - timedelta(days=1)
        )
        purger()
        self.assertFalse(Session.objects.exists())
