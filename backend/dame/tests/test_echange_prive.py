from django.test import SimpleTestCase

from dame.jeu import Dame
from dame.tests.test_jeu import partie
from parties import deroulement

SIEGES = [{"type": "humain", "joueur": "a" * 32}] + [{"type": "machine"}] * 3


class EchangePriveTests(SimpleTestCase):
    def test_les_dons_de_la_machine_ne_font_pas_d_etape(self):
        e = partie(nb=4)
        etat, etapes = deroulement.avancer(Dame(), e, SIEGES, pour=0)
        self.assertEqual(etapes, [])
        self.assertEqual((etat["phase"], etat["actif"]), ("echange", 0))
        self.assertTrue(all(etat["dons"][s] for s in (1, 2, 3)))
        self.assertEqual(etat["mains"][0], e["mains"][0])  # rien reçu avant son propre choix

    def test_le_don_de_l_humain_fait_son_etape(self):
        dame = Dame()
        etat, _ = deroulement.avancer(dame, partie(nb=4), SIEGES, pour=0)
        donnees = etat["mains"][0][:3]
        fin, etapes = deroulement.jouer(
            dame, etat, SIEGES, 0, {"action": "donner", "cartes": donnees}
        )
        premiere = etapes[0]
        self.assertTrue(premiere["message"].startswith("Tu donnes "), premiere["message"])
        self.assertIn("Tu reçois", premiere["message"])
        main = [c["id"] for c in premiere["vue"]["zones"][0]["cartes"]]
        self.assertEqual(len(main), 13)
        self.assertFalse(set(donnees) & set(main))
        for etape in etapes[1:]:
            self.assertNotIn("donne", etape["message"])
            self.assertNotIn("reçoi", etape["message"])
        self.assertEqual(fin["phase"], "plis")
