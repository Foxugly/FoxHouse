from django.test import SimpleTestCase

from parties import deroulement
from rami.jeu import Rami
from rami.tests.test_jeu import SUITE, etat_jouer, partie

HUMAIN_MACHINE = [{"type": "humain", "joueur": "a" * 32}, {"type": "machine"}]


class BrouillonRamiTests(SimpleTestCase):
    def test_brouillon_de_la_machine_jamais_rejoue(self):
        rami = Rami()
        for graine in range(1, 6):
            with self.subTest(graine=graine):
                e = partie(nb=3, graine=graine, manches=1)
                # La même partie, coup par coup : combien de coups publics, combien de privés ?
                publics = prives = 0
                rejouee = e
                while (j := rami.joueur_actif(rejouee)) is not None:
                    rejouee, message = rami.appliquer(rejouee, j, rami.adversaire(rejouee, j))
                    publics, prives = publics + (message is not None), prives + (message is None)
                self.assertGreater(prives, 0, "aucun brouillon : le test ne prouve rien")
                sieges = [{"type": "machine"}] * 3
                fin, etapes = deroulement.avancer(rami, e, sieges, pour=0)
                self.assertEqual(fin, rejouee)
                self.assertEqual(len(etapes), publics)
                for etape in etapes:
                    self.assertNotIn("attente", etape["message"])
                    self.assertNotIn("reprend", etape["message"])

    def test_le_brouillon_de_l_humain_fait_son_etape(self):
        e = etat_jouer(SUITE + ["2S-2", "3D-1"])
        etat, etapes = deroulement.jouer(
            Rami(), e, HUMAIN_MACHINE, 0, {"action": "poser", "cartes": SUITE}
        )
        self.assertEqual([x["message"] for x in etapes], ["Tu mets une suite en attente."])
        self.assertEqual(len(etat["brouillon"]), 1)
        etat, etapes = deroulement.jouer(Rami(), etat, HUMAIN_MACHINE, 0, {"action": "annuler"})
        self.assertEqual([x["message"] for x in etapes], ["Tu reprends les cartes en attente."])
