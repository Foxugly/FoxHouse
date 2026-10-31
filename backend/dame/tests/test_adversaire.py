from django.test import SimpleTestCase

from dame.adversaire import choisir
from dame.jeu import Dame
from dame.tests.test_jeu import dernier_pli, etat_plis, jouer, jouer_le_pli, partie
from tapis.jeu import CoupRefuse
from tapis.vue import valider_vue


def carte(coup):
    return coup["cartes"]


class EchangeTests(SimpleTestCase):
    def _donne(self, main):
        e = partie(nb=4)
        e["mains"][1] = main
        coup = choisir(e, 1)
        self.assertEqual(coup["action"], "donner")
        return coup["cartes"]

    def test_piques_hauts_d_abord(self):
        self.assertEqual(
            self._donne(["2C-1", "AS-1", "5H-1", "QS-1", "KH-1", "AD-1", "KS-1"]),
            ["QS-1", "KS-1", "AS-1"],
        )

    def test_puis_les_plus_hauts_coeurs(self):
        self.assertEqual(
            self._donne(["2C-1", "QS-1", "5H-1", "KH-1", "AD-1", "9H-1"]),
            ["QS-1", "KH-1", "9H-1"],
        )

    def test_puis_les_plus_hautes_cartes(self):
        self.assertEqual(
            self._donne(["2C-1", "5H-1", "AD-1", "JC-1", "10S-1", "3S-1"]),
            ["5H-1", "AD-1", "JC-1"],
        )


class JeuTests(SimpleTestCase):
    def test_entame_la_plus_basse_hors_coeur(self):
        e = etat_plis([["2H-1", "5S-1", "3D-1", "KC-1"], ["9S-1"], ["8S-1"]])
        e["coeurs_ouverts"] = True
        self.assertEqual(carte(choisir(e, 0)), ["3D-1"])
        e["mains"][0] = ["4H-1", "2H-1"]
        self.assertEqual(carte(choisir(e, 0)), ["2H-1"])

    def test_entame_le_deux_de_trefle(self):
        e = etat_plis([["2C-1", "2D-1"], ["9S-1"], ["8S-1"]], plis_joues=0)
        self.assertEqual(carte(choisir(e, 0)), ["2C-1"])

    def test_sous_la_couleur_la_plus_haute_qui_ne_prend_pas(self):
        e = etat_plis([["10S-1"], ["2S-1", "9S-1", "JS-1", "KS-1"], ["8S-1"], ["7S-1"]])
        e, _ = jouer(e, 0, "10S-1")
        self.assertEqual(carte(choisir(e, 1)), ["9S-1"])
        e["mains"][1] = ["JS-1", "KS-1"]
        self.assertEqual(carte(choisir(e, 1)), ["JS-1"])  # prend forcément : la plus basse

    def test_dernier_sans_points_joue_sa_plus_haute(self):
        e = etat_plis([["10S-1"], ["3S-1"], ["2S-1", "9S-1", "KS-1"]])
        e, _ = jouer(e, 0, "10S-1")
        e, _ = jouer(e, 1, "3S-1")
        self.assertEqual(carte(choisir(e, 2)), ["KS-1"])
        # Avec des points dans le pli, il passe dessous.
        e["pli"][1] = [1, "QS-1"]
        self.assertEqual(carte(choisir(e, 2)), ["9S-1"])

    def test_defausse(self):
        e = etat_plis([["10C-1"], ["QS-1", "AH-1", "KD-1"], ["8C-1"]])
        e, _ = jouer(e, 0, "10C-1")
        self.assertEqual(carte(choisir(e, 1)), ["QS-1"])
        e["mains"][1] = ["5H-1", "AH-1", "KD-1"]
        self.assertEqual(carte(choisir(e, 1)), ["AH-1"])
        e["mains"][1] = ["2S-1", "KD-1"]
        self.assertEqual(carte(choisir(e, 1)), ["KD-1"])

    def test_defausse_au_premier_pli(self):
        e = etat_plis([["2C-1"], ["QS-1", "AH-1", "4D-1", "9S-1"], ["8C-1"]], plis_joues=0)
        e, _ = jouer(e, 0, "2C-1")
        self.assertEqual(carte(choisir(e, 1)), ["9S-1"])

    def test_manche_suivante(self):
        e = dernier_pli([["QS-1"], [], [], []], ["AC-1", "4H-1", "5C-1", "6C-1"])
        e, _ = jouer_le_pli(e)
        self.assertEqual(choisir(e, 0)["action"], "manche_suivante")


JEUX_D_OPTIONS = [
    {},
    {"echange": False},
    {"valet_carreau": True, "score_fin": 50},
    {"echange": False, "valet_carreau": True, "score_fin": 20},
]
GRAINES = range(1, 121)
COUPS_MAX = 20000


class PartiesEntreAdversairesTests(SimpleTestCase):
    def test_toutes_les_parties_finissent(self):
        # 120 graines, réparties sur 4 jeux d'options et 4 nombres de joueurs (3 à 6) :
        # graine % 4 choisit les options, (graine // 4) % 4 le nombre de joueurs, si bien que
        # chaque jeu d'options est joué à 3, 4, 5 et 6 joueurs.
        dame = Dame()
        for graine in GRAINES:
            options = JEUX_D_OPTIONS[graine % 4]
            nb = 3 + (graine // 4) % 4
            with self.subTest(options=options, nb=nb, graine=graine):
                self._jouer(dame, partie(nb=nb, graine=graine, **options), graine)

    def _jouer(self, dame, e, graine):
        coups = 0
        verifier_vue = graine % 10 == 0
        while (j := dame.joueur_actif(e)) is not None:
            coup = dame.adversaire(e, j)
            try:
                e, _ = dame.appliquer(e, j, coup)
            except CoupRefuse as refus:
                self.fail(f"joueur {j}, phase {e['phase']} : coup refusé {coup} ({refus})")
            if verifier_vue:
                valider_vue(dame.vue(e, 0))
            coups += 1
            self.assertLess(coups, COUPS_MAX, "la partie ne finit pas")
        self.assertEqual(e["phase"], "terminee")
        self.assertGreaterEqual(max(sum(ligne[s] for ligne in e["scores"])
                                    for s in range(e["nb"])), e["options"]["score_fin"])
        valider_vue(dame.vue(e, 0))
