from django.test import SimpleTestCase

from rami.adversaire import choisir, plan
from rami.combinaisons import analyser
from rami.jeu import Rami
from rami.tests.test_jeu import BRELAN, SUITE, partie, retirer_ailleurs
from tapis.jeu import CoupRefuse

# Les 6 jeux d'options de la partie entre adversaires : les valeurs par défaut, chaque
# option booléenne inversée, l'as toujours à 11 et une partie en 2 manches.
JEUX_D_OPTIONS = [
    {},
    {"ouverture_suite_sans_joker": True},
    {"finir_par_defausse": False},
    {"defausse_a_poser": True},
    {"as": "toujours11"},
    {"manches": 2},
]
GRAINES = range(1, 201)
COUPS_MAX = 5000


def etat_joueur_1(main, **options):
    """Le joueur 1 a pioché et tient exactement `main`."""
    etat = partie(**options)
    retirer_ailleurs(etat, main)
    etat["mains"][1] = list(main)
    etat["actif"] = 1
    etat["phase"] = "jouer"
    return etat


class PlanTests(SimpleTestCase):
    def test_plan_trouve_suite_et_brelan(self):
        main = SUITE + BRELAN + ["2C-1"]
        combs = plan(main, "bas1_haut11")
        self.assertEqual(len(combs), 2)
        self.assertEqual(
            [sorted(c.cartes) for c in combs], [sorted(BRELAN), sorted(SUITE)]
        )  # le brelan (27 points) avant la suite (24)
        cartes = [c for comb in combs for c in comb.cartes]
        self.assertEqual(cartes.count("9H-1"), 1)

    def test_plan_sans_joker_disjoint_et_valide(self):
        main = ["JK-1", "AH-1", "2H-1", "3H-1", "QH-1", "KH-1", "AS-1", "AD-1", "5C-1"]
        combs = plan(main, "bas1_haut11")
        cartes = [c for comb in combs for c in comb.cartes]
        self.assertNotIn("JK-1", cartes)
        self.assertEqual(len(cartes), len(set(cartes)))
        for comb in combs:
            self.assertEqual(analyser(list(comb.cartes)), comb)

    def test_plan_suite_maximale_as_en_haut(self):
        combs = plan(["10S-1", "JS-1", "QS-1", "KS-1", "AS-1", "4D-1"], "bas1_haut11")
        self.assertEqual([c.cartes for c in combs], [("10S-1", "JS-1", "QS-1", "KS-1", "AS-1")])

    def test_plan_vide(self):
        self.assertEqual(plan(["2C-1", "9H-1", "JK-1"], "bas1_haut11"), [])


class ChoisirTests(SimpleTestCase):
    def test_adversaire_ouvre(self):
        rami = Rami()
        e = etat_joueur_1(SUITE + BRELAN + ["KS-1"])
        coups = []
        while e["actif"] == 1 and e["phase"] == "jouer":
            coup = choisir(e, 1)
            coups.append((coup["action"], sorted(coup["cartes"])))
            e, _ = rami.appliquer(e, 1, coup)
        self.assertEqual(
            coups,
            [
                ("poser", sorted(BRELAN)),
                ("poser", sorted(SUITE)),
                ("valider_ouverture", []),
                ("defausser", ["KS-1"]),
            ],
        )
        self.assertTrue(e["ouvert"][1])

    def test_par_le_jeu(self):
        e = partie()
        self.assertEqual(Rami().adversaire(e, 0), choisir(e, 0))

    def test_deterministe(self):
        e = etat_joueur_1(SUITE + BRELAN + ["KS-1", "2C-1"])
        self.assertEqual(choisir(e, 1), choisir(e, 1))

    def test_pas_assez_pour_ouvrir(self):
        e = etat_joueur_1(SUITE + ["KS-1", "2C-1", "JK-1"])
        self.assertEqual(choisir(e, 1), {"action": "defausser", "cartes": ["KS-1"], "cible": None})

    def test_garde_une_carte(self):
        # 13 cartes de cœur : tout poser viderait la main, l'adversaire garde le roi.
        main = [f"{v}H-1" for v in ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q"]]
        main.append("KH-1")
        e = etat_joueur_1(main)
        coup = choisir(e, 1)
        self.assertEqual(coup["action"], "poser")
        self.assertEqual(len(coup["cartes"]), 12)
        self.assertNotIn("KH-1", coup["cartes"])

    def test_prend_la_defausse_qu_il_pose(self):
        e = partie()
        retirer_ailleurs(e, SUITE + ["10H-1", "2C-1", "5D-1", "KS-1"])
        e["ouvert"][1] = True
        e["actif"] = 1
        e["mains"][1] = SUITE + ["2C-1", "5D-1"]
        e["defausse"].append("10H-1")
        self.assertEqual(choisir(e, 1)["action"], "prendre_defausse")
        e["defausse"][-1] = "KS-1"
        self.assertEqual(choisir(e, 1)["action"], "piocher")
        e["ouvert"][1] = False
        e["defausse"][-1] = "10H-1"
        self.assertEqual(choisir(e, 1)["action"], "piocher")

    def test_ne_redefausse_pas_la_carte_prise(self):
        e = etat_joueur_1(["KS-1", "2C-1", "3D-1"])
        e["ouvert"][1] = True
        e["prise"] = "KS-1"
        self.assertEqual(choisir(e, 1)["cartes"], ["3D-1"])

    def test_rend_la_defausse_qu_il_ne_peut_poser(self):
        e = etat_joueur_1(["KS-1", "2C-1"], defausse_a_poser=True)
        e["ouvert"][1] = True
        e["prise"] = "KS-1"
        self.assertEqual(choisir(e, 1)["action"], "rendre_defausse")

    def test_manche_suivante(self):
        e = partie(manches=2)
        e["phase"] = "fin_manche"
        self.assertEqual(choisir(e, 0)["action"], "manche_suivante")


class PartiesEntreAdversairesTests(SimpleTestCase):
    def test_toutes_les_parties_finissent(self):
        # Les 200 graines sont réparties sur les 6 jeux d'options (33 ou 34 chacun) : les
        # 1 200 parties complètes prendraient plusieurs minutes. 5 et 6 étant premiers entre
        # eux, chaque jeu d'options est joué à 2, 3, 4, 5 et 6 joueurs.
        rami = Rami()
        for graine in GRAINES:
            nb = 2 + graine % 5
            options = JEUX_D_OPTIONS[graine % len(JEUX_D_OPTIONS)]
            with self.subTest(options=options, graine=graine):
                self._jouer(rami, partie(nb=nb, graine=graine, **options), options, graine)

    def _jouer(self, rami, e, options, graine):
        coups = 0
        while (j := rami.joueur_actif(e)) is not None:
            coup = rami.adversaire(e, j)
            try:
                e, _ = rami.appliquer(e, j, coup)
            except CoupRefuse as refus:
                self.fail(
                    f"graine {graine}, options {options}, joueur {j}, phase {e['phase']} : "
                    f"coup refusé {coup} ({refus})"
                )
            coups += 1
            self.assertLess(
                coups, COUPS_MAX, f"graine {graine}, options {options} : la partie ne finit pas"
            )
        self.assertEqual(e["phase"], "terminee")
        self.assertEqual(len(e["penalites"]), e["options"]["manches"])
