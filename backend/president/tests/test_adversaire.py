import time

from django.test import SimpleTestCase

from parties import deroulement
from president.adversaire import choisir
from president.jeu import President
from president.tests.test_jeu import etat_pli, fin_de_manche, jouer, partie
from tapis.jeu import CoupRefuse
from tapis.vue import valider_vue

# Les 4 jeux d'options de la partie entre adversaires : les valeurs par défaut, chaque option
# booléenne inversée, et une partie en 2 manches.
JEUX_D_OPTIONS = [
    {},
    {"deux_ferme": False},
    {"echanges": False},
    {"manches": 2},
]
GRAINES = range(1, 121)
COUPS_MAX = 3000


def coup(action, cartes=()):
    return {"action": action, "cartes": list(cartes), "cible": None}


def etat_suivre(pli, main, **options):
    """Le joueur 1 doit répondre à `pli`, posé par le joueur 0, en tenant `main`."""
    e = etat_pli([list(pli) + ["4D-1"], list(main), ["3H-1"]], **options)
    e, _ = jouer(e, 0, list(pli))
    return e


class ChoixTests(SimpleTestCase):
    def test_entame_sa_plus_basse_valeur_avec_toutes_ses_cartes(self):
        e = etat_pli([["7C-1", "4S-1", "2S-1", "4H-1"], ["5S-1"], ["6S-1"]])
        self.assertEqual(choisir(e, 0), coup("jouer", ["4H-1", "4S-1"]))

    def test_entame_avec_que_des_2(self):
        e = etat_pli([["2S-1", "2H-1"], ["5S-1"], ["6S-1"]])
        self.assertEqual(choisir(e, 0), coup("jouer", ["2H-1", "2S-1"]))

    def test_la_plus_basse_combinaison_qui_bat_le_pli(self):
        e = etat_suivre(["5C-1"], ["KD-1", "8C-1", "6S-1", "6H-1", "9S-1"])
        # Les 6 forment une paire : on ne la casse pas ; le 8 est la plus basse qui bat le 5.
        self.assertEqual(choisir(e, 1), coup("jouer", ["8C-1"]))

    def test_paire_contre_paire(self):
        e = etat_suivre(["5C-1", "5D-1"], ["6S-1", "6H-1", "6D-1", "9S-1", "9H-1", "QC-1"])
        self.assertEqual(choisir(e, 1), coup("jouer", ["9H-1", "9S-1"]))

    def test_ne_bat_pas_avec_une_valeur_egale_ou_plus_basse(self):
        e = etat_suivre(["9C-1"], ["4S-1", "9S-1", "KS-1", "KH-1"])
        self.assertEqual(choisir(e, 1), coup("passer"))

    def test_garde_ses_2_tant_qu_il_a_plus_de_3_cartes(self):
        e = etat_suivre(["KC-1"], ["2S-1", "4C-1", "5C-1", "6C-1"])
        self.assertEqual(choisir(e, 1), coup("passer"))
        e = etat_suivre(["KC-1"], ["2S-1", "4C-1", "5C-1"])
        self.assertEqual(choisir(e, 1), coup("jouer", ["2S-1"]))

    def test_passe_sans_combinaison(self):
        e = etat_suivre(["2C-1"], ["4C-1", "AS-1"], deux_ferme=False)
        self.assertEqual(choisir(e, 1), coup("passer"))

    def test_echange_rend_ses_plus_basses(self):
        e = fin_de_manche(4, [2, 0, 3, 1])
        e, _ = President().appliquer(e, 0, coup("manche_suivante"))
        main = e["mains"][2]
        from president.manche import trier

        self.assertEqual(choisir(e, 2), coup("rendre", trier(main)[:2]))
        e, _ = President().appliquer(e, 2, choisir(e, 2))
        self.assertEqual(choisir(e, 0), coup("rendre", trier(e["mains"][0])[:1]))

    def test_manche_suivante(self):
        e = fin_de_manche(3, [0, 1, 2])
        self.assertEqual(choisir(e, 0), coup("manche_suivante"))


class CoupsPrivesTests(SimpleTestCase):
    def test_le_retour_de_la_machine_ne_fait_pas_d_etape(self):
        jeu = President()
        e = fin_de_manche(4, [2, 0, 3, 1])
        sieges = [{"type": "humain", "joueur": "a" * 32}] + [{"type": "machine"}] * 3
        # L'humain (Vice-président) lance la manche : le Président (machine) rend ses 2 cartes
        # sans étape, puis c'est au tour de l'humain de rendre la sienne.
        e, etapes = deroulement.jouer(jeu, e, sieges, 0, coup("manche_suivante"))
        self.assertEqual(len(etapes), 1)
        self.assertEqual((e["phase"], e["actif"]), ("echange", 0))
        self.assertEqual(len(e["recues"][1]), 2)  # le Pauvre a bien reçu
        carte = e["mains"][0][0]
        e, etapes = deroulement.jouer(jeu, e, sieges, 0, coup("rendre", [carte]))
        self.assertTrue(etapes[0]["message"].startswith("Tu donnes "))
        self.assertTrue(etapes[0]["message"].endswith(" au Vice-pauvre."))
        # Ensuite, le Pauvre (machine) entame : les étapes suivantes sont publiques.
        for etape in etapes[1:]:
            self.assertNotIn("donne", etape["message"])


class PartiesEntreAdversairesTests(SimpleTestCase):
    def test_toutes_les_parties_finissent(self):
        # 120 graines réparties sur les 4 jeux d'options ; 4 et 5 étant premiers entre eux,
        # chaque jeu d'options est joué à 3, 4, 5, 6 et 7 joueurs.
        jeu = President()
        debut = time.monotonic()
        for graine in GRAINES:
            nb = 3 + graine % 5
            options = JEUX_D_OPTIONS[graine % len(JEUX_D_OPTIONS)]
            with self.subTest(options=options, graine=graine, nb=nb):
                self._jouer(jeu, partie(nb=nb, graine=graine, **options), options, graine)
        self.assertLess(time.monotonic() - debut, 15, "les parties sont trop lentes")

    def _jouer(self, jeu, e, options, graine):
        coups = 0
        while (j := jeu.joueur_actif(e)) is not None:
            choix = jeu.adversaire(e, j)
            try:
                e, _ = jeu.appliquer(e, j, choix)
            except CoupRefuse as refus:
                self.fail(
                    f"graine {graine}, options {options}, joueur {j}, phase {e['phase']} : "
                    f"coup refusé {choix} ({refus})"
                )
            if coups % 7 == 0:
                valider_vue(jeu.vue(e, coups % e["nb"]))
            coups += 1
            self.assertLess(
                coups, COUPS_MAX, f"graine {graine}, options {options} : la partie ne finit pas"
            )
        valider_vue(jeu.vue(e, 0))
        self.assertEqual(e["phase"], "terminee")
        self.assertEqual(len(e["points"]), e["options"]["manches"])
        nb = e["nb"]
        for ligne in e["points"]:
            self.assertEqual(sorted(ligne), list(range(nb)))
