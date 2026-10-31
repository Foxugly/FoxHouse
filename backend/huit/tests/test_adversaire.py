from collections import Counter

from django.test import SimpleTestCase

from huit.adversaire import choisir, couleur_preferee
from huit.jeu import Huit
from huit.tests.outils import paquet_complet, partie, table, toutes_les_cartes
from tapis.jeu import CoupRefuse

JEUX_D_OPTIONS = [
    {"cartes_speciales": True, "jokers": False},
    {"cartes_speciales": True, "jokers": True},
    {"cartes_speciales": False, "jokers": False},
    {"cartes_speciales": False, "jokers": True},
]
GRAINES = range(1, 121)
COUPS_MAX = 3000


def jouer(carte):
    return {"action": "jouer", "cartes": [carte], "cible": None}


class ChoixTests(SimpleTestCase):
    def test_prefere_ses_cartes_speciales(self):
        e = table(partie(nb=3), {1: ["5H-1", "KH-1", "JH-1", "3C-1"]}, "7H-1", actif=1)
        self.assertEqual(choisir(e, 1), jouer("JH-1"))
        e = table(partie(nb=3), {1: ["5H-1", "2S-1", "7S-1"]}, "7H-1", actif=1)
        # Le 2♠ ne se joue pas sur le 7♥ ; le 7♠ passe avant le 5♥ : le pique est plus fourni.
        self.assertEqual(choisir(e, 1), jouer("7S-1"))

    def test_prefere_sa_couleur_la_plus_fournie(self):
        e = table(partie(nb=3, cartes_speciales=False),
                  {1: ["7S-1", "3H-1", "KC-1", "9C-1", "JH-1"]}, "7C-1", actif=1)
        # Jouables : 7♠ (valeur), K♣ et 9♣ ; le trèfle est la couleur la plus fournie.
        self.assertEqual(choisir(e, 1), jouer("9C-1"))
        # Sans cartes spéciales, le valet n'a pas la priorité.
        e = table(partie(nb=3, cartes_speciales=False),
                  {1: ["JH-1", "3D-1", "5D-1", "QD-1"]}, "QH-1", actif=1)
        self.assertEqual(choisir(e, 1), jouer("QD-1"))

    def test_le_huit_puis_le_joker_en_dernier_recours(self):
        e = table(partie(nb=3, jokers=True), {1: ["JK-1", "8S-1", "KD-1"]}, "7H-1", actif=1)
        self.assertEqual(choisir(e, 1), jouer("8S-1"))
        e = table(partie(nb=3, jokers=True), {1: ["JK-1", "8S-1", "3H-1"]}, "7H-1", actif=1)
        self.assertEqual(choisir(e, 1), jouer("3H-1"))
        e = table(partie(nb=3, jokers=True), {1: ["JK-1", "KD-1"]}, "7H-1", actif=1)
        self.assertEqual(choisir(e, 1), jouer("JK-1"))

    def test_pioche_puis_joue_la_carte_piochee_si_possible(self):
        jeu = Huit()
        e = table(partie(nb=3), {1: ["KD-1", "4C-1"]}, "7H-1", actif=1)
        self.assertEqual(choisir(e, 1)["action"], "piocher")
        e["pioche"].append("9H-1")
        e, _ = jeu.appliquer(e, 1, choisir(e, 1))
        self.assertEqual(choisir(e, 1), jouer("9H-1"))

    def test_passe_si_la_carte_piochee_ne_se_joue_pas(self):
        jeu = Huit()
        e = table(partie(nb=3), {1: ["KD-1", "4C-1"]}, "7H-1", actif=1)
        e["pioche"].append("9S-1")
        e, _ = jeu.appliquer(e, 1, choisir(e, 1))
        self.assertEqual(choisir(e, 1)["action"], "passer")

    def test_seule_la_carte_piochee_meme_si_une_autre_se_joue(self):
        jeu = Huit()
        e = table(partie(nb=3), {1: ["KD-1", "4C-1"]}, "7H-1", actif=1)
        e["pioche"].append("8C-1")
        e, _ = jeu.appliquer(e, 1, {"action": "piocher"})
        self.assertEqual(choisir(e, 1), jouer("8C-1"))
        e = table(partie(nb=3), {1: ["KD-1", "4H-1"]}, "7H-1", actif=1)
        e["pioche"].append("9S-1")
        e, _ = jeu.appliquer(e, 1, {"action": "piocher"})
        # Le 4♥ se jouerait, mais seule la carte piochée le peut encore.
        self.assertEqual(choisir(e, 1)["action"], "passer")

    def test_sous_penalite(self):
        jeu = Huit()
        e = table(partie(nb=3), {0: ["2H-1", "KD-1"], 1: ["2S-1", "5H-1"]}, "7H-1")
        e, _ = jeu.appliquer(e, 0, jouer("2H-1"))
        self.assertEqual(choisir(e, 1), jouer("2S-1"))
        e = table(partie(nb=3), {0: ["2H-1", "KD-1"], 1: ["5H-1", "8H-1"]}, "7H-1")
        e, _ = jeu.appliquer(e, 0, jouer("2H-1"))
        self.assertEqual(choisir(e, 1)["action"], "piocher")
        e = table(partie(nb=3, jokers=True), {0: ["JK-1", "KD-1"], 1: ["2H-1", "JK-2"]}, "7H-1")
        e, _ = jeu.appliquer(e, 0, jouer("JK-1"))
        self.assertEqual(choisir(e, 1), jouer("JK-2"))

    def test_annonce_sa_couleur_la_plus_presente(self):
        self.assertEqual(couleur_preferee(["KD-1", "3D-1", "5C-1", "8H-1", "8H-2"]), "D")
        self.assertEqual(couleur_preferee(["KH-1", "3S-1"]), "S")
        self.assertEqual(couleur_preferee(["JK-1", "8C-1"]), "S")
        jeu = Huit()
        e = table(partie(nb=3), {1: ["8S-1", "KD-1", "3D-1", "5C-1"]}, "7H-1", actif=1)
        e, _ = jeu.appliquer(e, 1, choisir(e, 1))
        self.assertEqual(choisir(e, 1), {"action": "couleur_D", "cartes": [], "cible": None})

    def test_manche_suivante(self):
        e = partie(manches=2)
        e["phase"] = "fin_manche"
        self.assertEqual(choisir(e, 0)["action"], "manche_suivante")

    def test_rien_a_jouer(self):
        with self.assertRaises(ValueError):
            choisir(partie(), 1)


class PartiesEntreAdversairesTests(SimpleTestCase):
    def test_toutes_les_parties_finissent(self):
        # 120 graines réparties sur les 4 jeux d'options ; 4 et 5 étant premiers entre eux,
        # chaque jeu d'options est joué de 2 à 6 joueurs.
        jeu = Huit()
        vus = Counter()
        for graine in GRAINES:
            nb = 2 + graine % 5
            options = JEUX_D_OPTIONS[graine % len(JEUX_D_OPTIONS)]
            with self.subTest(options=options, nb=nb, graine=graine):
                self._jouer(jeu, partie(nb=nb, graine=graine, manches=2, **options), vus)
        # Les parties passent bien par les règles délicates.
        for cas in ("couleur", "penalite_cumulee", "joker_contre", "carte_piochee_jouee",
                    "passer", "remelange", "sens_inverse"):
            self.assertGreater(vus[cas], 0, cas)

    def _jouer(self, jeu, e, vus):
        coups = 0
        paquet = paquet_complet(e)
        while (j := jeu.joueur_actif(e)) is not None:
            coup = jeu.adversaire(e, j)
            permises = {a["id"] for a in jeu.actions_permises(e, j)}
            self.assertIn(coup["action"], permises)
            avant = e
            try:
                e, _ = jeu.appliquer(e, j, coup)
            except CoupRefuse as refus:
                self.fail(f"joueur {j}, phase {e['phase']} : coup refusé {coup} ({refus})")
            self.assertEqual(toutes_les_cartes(e), paquet, "des cartes ont disparu")
            coups += 1
            self.assertLess(coups, COUPS_MAX, "la partie ne finit pas")
            self._noter(avant, coup, e, vus)
        self.assertEqual(e["phase"], "terminee")
        self.assertEqual(len(e["scores"]), 2)

    def _noter(self, avant, coup, apres, vus):
        if apres["phase"] == "couleur":
            vus["couleur"] += 1
        if apres["penalite"] > 4 or (apres["penalite"] == 4 and apres["penalite_par"] == "2"):
            vus["penalite_cumulee"] += 1
        if apres["penalite"] >= 8 and apres["penalite_par"] == "joker":
            vus["joker_contre"] += 1
        if coup["action"] == "jouer" and avant["piochee"] is not None:
            vus["carte_piochee_jouee"] += 1
        if coup["action"] == "passer":
            vus["passer"] += 1
        if apres.get("remelanges", 0) > avant.get("remelanges", 0):
            vus["remelange"] += 1
        if apres["sens"] == -1:
            vus["sens_inverse"] += 1
