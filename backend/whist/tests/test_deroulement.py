from django.test import SimpleTestCase

from parties import deroulement
from tapis.vue import valider_vue
from whist.jeu import Whist
from whist.tests.aides import partie

SIEGES = [{"type": "humain", "joueur": "a" * 32}] + [{"type": "machine"}] * 3


class DeroulementTests(SimpleTestCase):
    def test_une_partie_jouee_par_le_serveur(self):
        """Le joueur humain joue le coup de la machine ; le serveur fait jouer les autres."""
        whist = Whist()
        e, etapes = deroulement.avancer(whist, partie(graine=11, donnes=4), SIEGES, pour=0)
        coups = 0
        while whist.joueur_actif(e) is not None:
            self.assertEqual(whist.joueur_actif(e), 0)
            e, etapes = deroulement.jouer(whist, e, SIEGES, 0, whist.adversaire(e, 0))
            for etape in etapes:
                self.assertTrue(etape["message"])
                valider_vue(etape["vue"])
            coups += 1
            self.assertLess(coups, 500)
        self.assertEqual(len(e["scores"]), 4)
