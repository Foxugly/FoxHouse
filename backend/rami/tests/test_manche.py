from django.test import SimpleTestCase

from rami.manche import (
    defausser,
    fin_de_manche,
    manche_suivante,
    nom_joueur,
    nouvel_etat,
    piocher,
    prendre_defausse,
    reconstituer_pioche,
)
from rami.options import OPTIONS
from tapis.options import valider


def etat_neuf(nb=4, graine=7, **options):
    return nouvel_etat(valider(OPTIONS, options), nb, graine)


class MancheTests(SimpleTestCase):
    def test_options_par_defaut(self):
        o = valider(OPTIONS, {})
        self.assertEqual(o["as"], "bas1_haut11")
        self.assertEqual(o["penalite_joker"], 20)
        self.assertEqual(o["manches"], 5)
        self.assertEqual(len(OPTIONS), 7)

    def test_distribution(self):
        e = etat_neuf()
        self.assertTrue(all(len(m) == 13 for m in e["mains"]))
        self.assertEqual(len(e["defausse"]), 1)
        self.assertEqual(len(e["pioche"]), 108 - 52 - 1)
        tout = e["pioche"] + e["defausse"] + [c for m in e["mains"] for c in m]
        self.assertEqual(len(set(tout)), 108)
        self.assertEqual(etat_neuf()["mains"], e["mains"])
        self.assertEqual((e["phase"], e["actif"]), ("piocher", 0))

    def test_tour_piocher_defausser(self):
        e = etat_neuf()
        self.assertEqual(piocher(e, 0), "Tu pioches.")
        self.assertEqual(len(e["mains"][0]), 14)
        self.assertEqual(e["phase"], "jouer")
        defausser(e, 0, e["mains"][0][0])
        self.assertEqual(len(e["mains"][0]), 13)
        self.assertEqual((e["actif"], e["phase"]), (1, "piocher"))
        self.assertEqual(piocher(e, 1), "Ordinateur 1 pioche.")

    def test_defausser_carte_absente(self):
        e = etat_neuf()
        with self.assertRaises(ValueError):
            defausser(e, 0, "ZZ-9")

    def test_prendre_defausse(self):
        e = etat_neuf()
        dessus = e["defausse"][-1]
        message = prendre_defausse(e, 0)
        self.assertIn(dessus, e["mains"][0])
        self.assertEqual(e["prise"], dessus)
        self.assertEqual(e["defausse"], [])
        self.assertTrue(message.startswith("Tu prends le "))
        defausser(e, 0, e["mains"][0][0])
        self.assertIsNone(e["prise"])

    def test_reconstitution_pioche(self):
        e = etat_neuf()
        e["pioche"] = []
        e["defausse"] = ["2S-1", "3S-1", "4S-1", "5S-1", "6S-1"]
        piocher(e, 0)
        self.assertEqual(len(e["pioche"]), 3)  # 4 reçues, 1 piochée
        self.assertEqual(e["defausse"], ["6S-1"])
        self.assertEqual(e["reconstitutions"], 1)

    def test_pioche_vide_defausse_d_une_carte(self):
        e = etat_neuf()
        e["pioche"] = []
        piocher(e, 0)
        self.assertEqual(e["phase"], "fin_manche")
        self.assertEqual(len(e["penalites"][-1]), 4)
        self.assertTrue(all(p > 0 for p in e["penalites"][-1]))

    def test_quatrieme_epuisement_finit_la_manche(self):
        e = etat_neuf()
        e["pioche"] = []
        e["defausse"] = ["2S-1", "3S-1", "4S-1"]
        e["reconstitutions"] = 3
        self.assertFalse(reconstituer_pioche(e))
        piocher(e, 0)
        self.assertEqual(e["phase"], "fin_manche")

    def test_fin_de_manche_penalites(self):
        e = etat_neuf(nb=2)
        e["mains"][0] = ["AS-1", "JK-1", "QH-1"]
        e["mains"][1] = ["5S-1"]
        fin_de_manche(e, 1)
        self.assertEqual(e["penalites"], [[41, 0]])
        self.assertEqual(e["actif"], 0)

    def test_penalite_compte_le_brouillon(self):
        e = etat_neuf(nb=2)
        e["mains"][0] = ["2S-1"]
        e["brouillon"] = [{"type": "brelan", "cartes": ["KS-1", "KH-1", "KD-1"], "jokers": {}}]
        fin_de_manche(e, 1)
        self.assertEqual(e["penalites"], [[32, 0]])
        self.assertEqual(e["brouillon"], [])

    def test_gagnant_par_defausse(self):
        e = etat_neuf(nb=2)
        e["mains"][0] = ["2S-1"]
        e["phase"] = "jouer"
        defausser(e, 0, "2S-1")
        self.assertEqual(e["phase"], "fin_manche")
        self.assertEqual(e["penalites"][-1][0], 0)
        self.assertGreater(e["penalites"][-1][1], 0)

    def test_derniere_manche_terminee(self):
        e = etat_neuf(manches=1)
        fin_de_manche(e, 0)
        self.assertEqual(e["phase"], "terminee")

    def test_manche_suivante_change_le_premier(self):
        e = etat_neuf()
        e["table"] = [{"id": "g1"}]
        e["ouvert"][2] = True
        e["reconstitutions"] = 2
        fin_de_manche(e, 0)
        manche_suivante(e)
        self.assertEqual((e["manche"], e["premier"], e["actif"]), (2, 1, 1))
        self.assertEqual((e["table"], e["ouvert"], e["reconstitutions"]), ([], [False] * 4, 0))
        self.assertEqual(e["phase"], "piocher")
        self.assertTrue(all(len(m) == 13 for m in e["mains"]))
        self.assertEqual(len(e["penalites"]), 1)

    def test_nom_joueur(self):
        self.assertEqual((nom_joueur(0), nom_joueur(2)), ("Toi", "Ordinateur 2"))
