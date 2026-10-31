from django.test import SimpleTestCase

from rami.manche import nouvel_etat
from rami.options import OPTIONS
from rami.poses import ajouter_a, annuler, poser, recuperer, valider_ouverture
from tapis.jeu import CoupRefuse
from tapis.options import valider

SUITE = ["7H-1", "8H-1", "9H-1"]
BRELAN = ["9S-1", "9D-1", "9C-1"]


def etat_jouer(main, nb=2, **options):
    """Un état où le joueur 0 a pioché et tient exactement `main`."""
    etat = nouvel_etat(valider(OPTIONS, options), nb, 7)
    etat["mains"][0] = list(main)
    etat["phase"] = "jouer"
    return etat


class OuvertureTests(SimpleTestCase):
    def test_ouverture_51(self):
        e = etat_jouer(SUITE + BRELAN + ["2S-2"])
        poser(e, 0, SUITE)
        poser(e, 0, BRELAN)
        self.assertEqual(len(e["brouillon"]), 2)
        self.assertEqual(e["table"], [])
        self.assertEqual(e["mains"][0], ["2S-2"])
        valider_ouverture(e, 0)
        self.assertTrue(e["ouvert"][0])
        self.assertEqual(e["brouillon"], [])
        self.assertEqual([g["id"] for g in e["table"]], ["g1", "g2"])
        self.assertEqual([g["auteur"] for g in e["table"]], [0, 0])
        self.assertEqual(e["table"][0]["cartes"], SUITE)
        self.assertEqual(e["prochain_groupe"], 3)

    def test_ouverture_insuffisante(self):
        e = etat_jouer(SUITE + ["2S-2"])
        poser(e, 0, SUITE)
        with self.assertRaisesRegex(CoupRefuse, "24"):
            valider_ouverture(e, 0)
        self.assertFalse(e["ouvert"][0])
        self.assertEqual(len(e["brouillon"]), 1)

    def test_annuler_rend_les_cartes(self):
        e = etat_jouer(SUITE + BRELAN + ["2S-2"])
        poser(e, 0, SUITE)
        poser(e, 0, BRELAN)
        self.assertEqual(annuler(e, 0), "Tu reprends les cartes en attente.")
        self.assertEqual(e["brouillon"], [])
        self.assertCountEqual(e["mains"][0], SUITE + BRELAN + ["2S-2"])

    def test_suite_sans_joker_obligatoire(self):
        groupes = [["5C-1", "6C-1", "JK-1"], ["KS-1", "KH-1", "KD-1"], ["QS-1", "QH-1", "QD-1"]]
        main = [c for g in groupes for c in g] + ["2S-2"]
        e = etat_jouer(main, ouverture_suite_sans_joker=True)
        for g in groupes:
            poser(e, 0, g)
        with self.assertRaisesRegex(CoupRefuse, "suite sans joker"):
            valider_ouverture(e, 0)
        self.assertFalse(e["ouvert"][0])
        # Sans l'option, le même brouillon (78 points) suffit.
        e = etat_jouer(main)
        for g in groupes:
            poser(e, 0, g)
        valider_ouverture(e, 0)
        self.assertTrue(e["ouvert"][0])

    def test_pose_refusee(self):
        e = etat_jouer(SUITE + ["2S-2"])
        with self.assertRaisesRegex(CoupRefuse, "combinaison"):
            poser(e, 0, ["7H-1", "8H-1", "2S-2"])
        with self.assertRaisesRegex(CoupRefuse, "pas dans ta main"):
            poser(e, 0, ["7H-1", "8H-1", "10H-1"])
        with self.assertRaisesRegex(CoupRefuse, "Choisis des cartes différentes"):
            poser(e, 0, ["7H-1", "7H-1", "8H-1"])
        with self.assertRaisesRegex(CoupRefuse, "Choisis des cartes différentes"):
            poser(e, 0, [])
        e["phase"] = "piocher"
        with self.assertRaises(CoupRefuse):
            poser(e, 0, SUITE)
        self.assertEqual(e["brouillon"], [])

    def test_pose_apres_ouverture_va_sur_la_table(self):
        e = etat_jouer(SUITE + ["2S-2"])
        e["ouvert"][0] = True
        poser(e, 0, SUITE)
        self.assertEqual(e["brouillon"], [])
        self.assertEqual(e["table"][0]["id"], "g1")
        self.assertEqual(e["prochain_groupe"], 2)


def table_adverse(e):
    """Le joueur 1 a posé 7H 8H 9H en g1."""
    e["table"] = [
        {"id": "g1", "auteur": 1, "type": "suite", "cartes": list(SUITE), "jokers": {}}
    ]
    e["prochain_groupe"] = 2


class AjoutTests(SimpleTestCase):
    def test_ajout_avant_ouverture_refuse(self):
        e = etat_jouer(["10H-1", "2S-2"])
        table_adverse(e)
        with self.assertRaisesRegex(CoupRefuse, "ouvert"):
            ajouter_a(e, 0, ["10H-1"], "g1")
        self.assertEqual(e["table"][0]["cartes"], SUITE)

    def test_ajout_au_groupe_d_un_adversaire(self):
        e = etat_jouer(["10H-1", "2S-2"])
        e["ouvert"][0] = True
        table_adverse(e)
        ajouter_a(e, 0, ["10H-1"], "g1")
        g = e["table"][0]
        self.assertEqual(g["cartes"], SUITE + ["10H-1"])
        self.assertEqual((g["id"], g["auteur"]), ("g1", 1))
        self.assertEqual(e["mains"][0], ["2S-2"])
        with self.assertRaisesRegex(CoupRefuse, "groupe"):
            ajouter_a(e, 0, ["2S-2"], "g1")
        with self.assertRaisesRegex(CoupRefuse, "groupe"):
            ajouter_a(e, 0, ["2S-2"], "g9")


class JokerTests(SimpleTestCase):
    def _etat(self, **options):
        e = etat_jouer(["8H-2", "2S-2"], **options)
        e["ouvert"][0] = True
        e["table"] = [
            {
                "id": "g1",
                "auteur": 1,
                "type": "suite",
                "cartes": ["7H-1", "JK-1", "9H-1"],
                "jokers": {"JK-1": "8H"},
            }
        ]
        return e

    def test_recuperer_joker(self):
        e = self._etat()
        recuperer(e, 0, "8H-2", "g1")
        self.assertCountEqual(e["mains"][0], ["JK-1", "2S-2"])
        self.assertEqual(e["joker_recupere"], "JK-1")
        g = e["table"][0]
        self.assertEqual(g["cartes"], ["7H-1", "8H-2", "9H-1"])
        self.assertEqual(g["jokers"], {})
        self.assertEqual((g["id"], g["auteur"]), ("g1", 1))

        e = self._etat(recuperation_joker="jamais")
        with self.assertRaises(CoupRefuse):
            recuperer(e, 0, "8H-2", "g1")
        self.assertEqual(e["joker_recupere"], None)
        self.assertNotIn("JK-1", e["mains"][0])

    def test_recuperer_avec_une_seule_carte_refuse(self):
        # La main deviendrait [JK] : impossible de l'ajouter en gardant une carte.
        e = self._etat()
        e["mains"][0] = ["8H-2"]
        with self.assertRaisesRegex(CoupRefuse, "Tu ne pourrais pas rejouer ce joker ce tour-ci."):
            recuperer(e, 0, "8H-2", "g1")
        self.assertEqual(e["mains"][0], ["8H-2"])
        self.assertEqual(e["table"][0]["cartes"], ["7H-1", "JK-1", "9H-1"])
        self.assertIsNone(e["joker_recupere"])

    def test_recuperer_joker_qui_ne_va_nulle_part_refuse(self):
        # Le carré redevient complet : un joker n'y entre plus, et il n'y a pas d'autre groupe.
        e = etat_jouer(["KC-2", "2S-2"])
        e["ouvert"][0] = True
        e["table"] = [
            {
                "id": "g1",
                "auteur": 1,
                "type": "brelan",
                "cartes": ["KS-1", "KH-1", "KD-1", "JK-1"],
                "jokers": {"JK-1": "KC"},
            }
        ]
        with self.assertRaisesRegex(CoupRefuse, "rejouer ce joker"):
            recuperer(e, 0, "KC-2", "g1")
        self.assertEqual(e["mains"][0], ["KC-2", "2S-2"])
        self.assertEqual(e["table"][0]["cartes"], ["KS-1", "KH-1", "KD-1", "JK-1"])
        # Avec une suite ailleurs sur la table, le joker peut y aller : accepté.
        e["table"].append(
            {"id": "g2", "auteur": 1, "type": "suite", "cartes": list(SUITE), "jokers": {}}
        )
        recuperer(e, 0, "KC-2", "g1")
        self.assertEqual(e["joker_recupere"], "JK-1")
        self.assertEqual(e["table"][0]["cartes"], ["KS-1", "KH-1", "KD-1", "KC-2"])

    def test_seconde_recuperation_refusee(self):
        e = self._etat()
        e["mains"][0].append("5S-2")
        e["table"].append(
            {
                "id": "g2",
                "auteur": 1,
                "type": "suite",
                "cartes": ["3S-1", "4S-1", "JK-2"],
                "jokers": {"JK-2": "5S"},
            }
        )
        recuperer(e, 0, "8H-2", "g1")
        with self.assertRaisesRegex(CoupRefuse, "Utilise d'abord le joker récupéré."):
            recuperer(e, 0, "5S-2", "g2")
        self.assertEqual(e["joker_recupere"], "JK-1")
        self.assertIn("5S-2", e["mains"][0])

    def test_recuperer_refuse(self):
        e = self._etat()
        with self.assertRaisesRegex(CoupRefuse, "joker"):
            recuperer(e, 0, "2S-2", "g1")
        e["ouvert"][0] = False
        with self.assertRaisesRegex(CoupRefuse, "ouvert"):
            recuperer(e, 0, "8H-2", "g1")


class GarderUneCarteTests(SimpleTestCase):
    def test_garder_une_carte_pour_la_defausse(self):
        e = etat_jouer(SUITE)
        e["ouvert"][0] = True
        with self.assertRaisesRegex(CoupRefuse, "Garde une carte pour la défausse."):
            poser(e, 0, SUITE)
        self.assertEqual(e["mains"][0], SUITE)
        self.assertEqual(e["table"], [])

        e = etat_jouer(SUITE, finir_par_defausse=False)
        e["ouvert"][0] = True
        poser(e, 0, SUITE)
        self.assertEqual(e["phase"], "fin_manche")
        self.assertEqual(e["penalites"][-1][0], 0)
        self.assertGreater(e["penalites"][-1][1], 0)

    def test_ajout_qui_vide_la_main(self):
        e = etat_jouer(["10H-1"])
        e["ouvert"][0] = True
        table_adverse(e)
        with self.assertRaisesRegex(CoupRefuse, "Garde une carte"):
            ajouter_a(e, 0, ["10H-1"], "g1")
        e = etat_jouer(["10H-1"], finir_par_defausse=False)
        e["ouvert"][0] = True
        table_adverse(e)
        ajouter_a(e, 0, ["10H-1"], "g1")
        self.assertEqual(e["phase"], "fin_manche")
        self.assertEqual(e["penalites"][-1][0], 0)

    def test_ouverture_qui_vide_la_main(self):
        e = etat_jouer(SUITE + BRELAN, finir_par_defausse=False)
        poser(e, 0, SUITE)
        poser(e, 0, BRELAN)
        self.assertEqual(e["phase"], "jouer")
        valider_ouverture(e, 0)
        self.assertEqual(e["phase"], "fin_manche")
        self.assertEqual(e["penalites"][-1][0], 0)
        self.assertEqual(len(e["table"]), 2)
