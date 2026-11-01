import collections

from django.test import SimpleTestCase

from tapis.jeu import CoupRefuse
from tapis.vue import valider_vue
from whist.adversaire import (
    choisir,
    choisir_annonce,
    choisir_couleur_d_atout,
    estimer,
    main_de_misere,
)
from whist.jeu import Whist
from whist.manche import MISERES, NB_PLIS, trier
from whist.tests.aides import appliquer, etat_encheres, etat_plis, jouer, partie

# Des mains de 13 cartes.
FORTE = ["AS-1", "KS-1", "QS-1", "JS-1", "10S-1", "9S-1", "8S-1",
         "AH-1", "KH-1", "AD-1", "KD-1", "2C-1", "3C-1"]  # 9 estimés à pique (7 piques)
MOYENNE = ["AS-1", "KS-1", "2S-1", "AH-1", "3H-1", "4H-1", "KD-1", "5D-1",
           "6D-1", "AC-1", "8C-1", "9C-1", "10C-1"]  # 5 estimés (sans atout long)
FAIBLE = ["AS-1", "2S-1", "3S-1", "AH-1", "5H-1", "6H-1", "KD-1", "5D-1",
          "6D-1", "7C-1", "8C-1", "9C-1", "10C-1"]  # 3 estimés
NULLE = ["2S-1", "3S-1", "9S-1", "2H-1", "5H-1", "JH-1", "4D-1", "8D-1",
         "10D-1", "3C-1", "6C-1", "QC-1", "JC-1"]  # misère


def carte(coup):
    return coup["cartes"]


class EstimationTests(SimpleTestCase):
    def test_estimer(self):
        self.assertEqual(estimer(FORTE, "S"), 3 + 3 + 4)  # 3 as, 3 rois gardés, 4 atouts de plus
        self.assertEqual(estimer(MOYENNE, "H"), 5)
        self.assertEqual(estimer(FAIBLE, "H"), 3)
        # Un roi sec ne compte pas.
        self.assertEqual(estimer(["KS-1", "2H-1"], "C"), 0)

    def test_main_de_misere(self):
        self.assertTrue(main_de_misere(NULLE))
        self.assertFalse(main_de_misere(FAIBLE))
        self.assertFalse(main_de_misere(NULLE[:-1] + ["QS-1"]))  # deux dames
        sans_petite = ["9S-1", "10S-1", "2H-1", "4D-1", "3C-1"]
        self.assertFalse(main_de_misere(sans_petite))

    def test_couleur_d_atout(self):
        self.assertEqual(choisir_couleur_d_atout(FORTE), "S")


class EncheresTests(SimpleTestCase):
    def _e(self, main, **options):
        e = etat_encheres(**options)
        e["mains"][0] = trier(main)
        e["retournee"] = "7H-1" if "7H-1" not in main else "8H-1"
        return e

    def test_abondance_9(self):
        self.assertEqual(choisir_annonce(self._e(FORTE), 0), "abondance_9")

    def test_seul(self):
        self.assertEqual(choisir_annonce(self._e(MOYENNE), 0), "seul")
        # Plus haut que seul déjà annoncé : il passe.
        e = self._e(MOYENNE)
        e["enchere"] = {"code": "abondance_9", "preneur": 3, "partenaire": None}
        self.assertEqual(choisir_annonce(e, 0), "passer")

    def test_demande_ou_accepte(self):
        self.assertEqual(choisir_annonce(self._e(FAIBLE), 0), "demander")
        e = self._e(FAIBLE)
        e["enchere"] = {"code": "demande", "preneur": 3, "partenaire": None}
        self.assertEqual(choisir_annonce(e, 0), "accepter")
        e["enchere"] = {"code": "emballage", "preneur": 3, "partenaire": 2}
        self.assertEqual(choisir_annonce(e, 0), "passer")

    def test_misere(self):
        self.assertEqual(choisir_annonce(self._e(NULLE), 0), "misere")
        self.assertEqual(choisir_annonce(self._e(NULLE, misere=False), 0), "passer")

    def test_passe(self):
        main = ["2S-1", "3S-1", "QS-1", "KH-1", "5H-1", "6H-1", "QD-1", "5D-1",
                "6D-1", "7C-1", "8C-1", "9C-1", "10C-1"]
        self.assertEqual(choisir_annonce(self._e(main), 0), "passer")

    def test_demande_non_acceptee(self):
        e = self._e(FAIBLE)
        e["phase"] = "demande_seule"
        self.assertEqual(choisir(e, 0)["action"], "passer")
        e = self._e(MOYENNE)
        e["phase"] = "demande_seule"
        self.assertEqual(choisir(e, 0)["action"], "seul")

    def test_abondance_jouee_jusqu_au_bout(self):
        """Une abondance de la machine : choix de l'atout puis 13 plis joués."""
        whist = Whist()
        # Siège 1 reçoit la main forte ; les autres tout le reste.
        e = etat_encheres()
        reste = [c for m in e["mains"] for c in m if c not in FORTE]
        e["mains"] = [trier(reste[0:13]), trier(FORTE), trier(reste[13:26]), trier(reste[26:39])]
        e["retournee"] = e["mains"][3][-1]
        e, _ = appliquer(e, 0, "passer")
        e, _ = whist.appliquer(e, 1, choisir(e, 1))
        self.assertEqual(e["enchere"]["code"], "abondance_9")
        while e["phase"] == "encheres":
            j = whist.joueur_actif(e)
            e, _ = whist.appliquer(e, j, choisir(e, j))
        self.assertEqual((e["phase"], e["actif"]), ("atout", 1))
        e, message = whist.appliquer(e, 1, choisir(e, 1))
        self.assertEqual(message, "Ordinateur 1 choisit l'atout : pique.")
        while e["phase"] == "plis":
            j = whist.joueur_actif(e)
            e, message = whist.appliquer(e, j, choisir(e, j))
        self.assertEqual(e["plis_joues"], NB_PLIS)
        self.assertEqual(sum(e["scores"][0]), 0)
        self.assertIn("Contrat ", message)


class JeuTests(SimpleTestCase):
    def test_attaque_entame_ses_as(self):
        e = etat_plis([["AD-1", "KS-1", "2S-1"], ["3S-1"] * 3, ["4S-1"] * 3, ["5S-1"] * 3],
                      code="seul", preneurs=[0], atout="H")
        self.assertEqual(carte(choisir(e, 0)), ["AD-1"])

    def test_attaque_tire_les_atouts_s_il_en_a_la_majorite(self):
        e = etat_plis([["KH-1", "QH-1", "2S-1", "3S-1", "4S-1"], ["5S-1"] * 5, ["6S-1"] * 5,
                       ["7S-1"] * 5], code="seul", preneurs=[0], atout="H")
        e["jouees"] = [f"{v}H-1" for v in ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J")]
        self.assertEqual(carte(choisir(e, 0)), ["KH-1"])
        e["jouees"] = []
        self.assertEqual(carte(choisir(e, 0)), ["4S-1"])  # sinon sa plus longue, par le haut

    def test_defense_entame_sa_plus_longue_par_le_bas(self):
        e = etat_plis([["9D-1", "3D-1", "8D-1", "2S-1"], ["5S-1"] * 4, ["6S-1"] * 4,
                       ["7S-1"] * 4], code="seul", preneurs=[1], atout="H")
        self.assertEqual(carte(choisir(e, 0)), ["3D-1"])

    def test_prend_au_plus_bas_sauf_si_le_pli_est_au_partenaire(self):
        e = etat_plis([["9S-1", "2D-1"], ["10S-1", "KS-1", "AS-1"], ["2S-1", "3D-1"],
                       ["3S-1", "4D-1"]], code="seul", preneurs=[0], atout="H")
        e["plis_joues"] = 11
        e, _ = jouer(e, 0, "9S-1")
        self.assertEqual(carte(choisir(e, 1)), ["10S-1"])
        # Défense contre 0 : 1 prend ; 2 et 3 (partenaires de 1) fournissent bas.
        e, _ = jouer(e, 1, "KS-1")
        self.assertEqual(carte(choisir(e, 2)), ["2S-1"])

    def test_coupe_au_plus_bas_atout_ou_se_defausse(self):
        e = etat_plis([["9S-1"], ["5H-1", "2H-1", "4D-1"], ["3S-1"], ["4S-1"]],
                      code="seul", preneurs=[0], atout="H")
        e, _ = jouer(e, 0, "9S-1")
        self.assertEqual(carte(choisir(e, 1)), ["2H-1"])
        # Pli à son partenaire : il se défausse de sa plus basse hors atout.
        e = etat_plis([["9S-1"], ["5H-1", "2H-1", "4D-1"], ["3S-1"], ["4S-1"]],
                      code="seul", preneurs=[3], atout="H", actif=0)
        e, _ = jouer(e, 0, "9S-1")
        self.assertEqual(carte(choisir(e, 1)), ["4D-1"])

    def test_misere_preneur_joue_la_plus_haute_qui_ne_prend_pas(self):
        e = etat_plis([["9S-1"], ["10S-1", "8S-1", "2S-1"], ["3S-1"], ["4S-1"]],
                      code="misere", preneurs=[1], atout=None)
        e, _ = jouer(e, 0, "9S-1")
        self.assertEqual(carte(choisir(e, 1)), ["8S-1"])
        e["mains"][1] = ["10S-1", "JS-1"]
        self.assertEqual(carte(choisir(e, 1)), ["10S-1"])
        e = etat_plis([["9S-1"], ["10S-1", "8S-1", "2S-1"], ["3S-1"], ["4S-1"]],
                      code="misere", preneurs=[1], atout=None, actif=1)
        self.assertEqual(carte(choisir(e, 1)), ["2S-1"])

    def test_misere_defense_joue_bas_derriere_le_preneur(self):
        e = etat_plis([["9S-1"], ["7S-1"], ["AS-1", "5S-1", "8S-1"], ["4S-1"]],
                      code="misere", preneurs=[1], atout=None, actif=1)
        e, _ = jouer(e, 1, "7S-1")
        self.assertEqual(carte(choisir(e, 2)), ["5S-1"])

    def test_misere_ouverte_defense_entame_sa_couleur_courte(self):
        e = etat_plis([["9S-1", "3S-1", "4D-1"], ["7S-1", "8S-1", "2D-1"], ["AS-1"] * 3,
                       ["4S-1"] * 3], code="misere_ouverte", preneurs=[1], atout=None)
        self.assertEqual(carte(choisir(e, 0)), ["4D-1"])

    def test_donne_suivante(self):
        e = etat_plis([["AS-1"], ["KS-1"], ["2S-1"], ["QS-1"]])
        e["phase"] = "fin_donne"
        self.assertEqual(choisir(e, 0)["action"], "donne_suivante")


JEUX_D_OPTIONS = [
    {"donnes": 4},
    {"donnes": 8, "trou": False},
    {"donnes": 4, "misere": False},
    {"donnes": 8, "trou": False, "misere": False},
    {"donnes": 4, "trou": True, "misere": True},
]
GRAINES = range(1, 111)
COUPS_MAX = 3000


class PartiesEntreAdversairesTests(SimpleTestCase):
    def test_toutes_les_parties_finissent(self):
        # 110 graines sur 5 jeux d'options (trou et misère oui/non, 4 et 8 donnes).
        whist = Whist()
        contrats = collections.Counter()
        for graine in GRAINES:
            options = JEUX_D_OPTIONS[graine % len(JEUX_D_OPTIONS)]
            with self.subTest(options=options, graine=graine):
                self._jouer(whist, partie(graine=graine, **options), graine, contrats)
        # Chaque contrat que la machine annonce apparaît ; les autres ont leurs tests dédiés
        # (abondance, solo, misère ouverte : EncheresTests et test_jeu).
        for code in ("emballage", "seul", "misere", "trou", "rejouee"):
            self.assertGreater(contrats[code], 0, code)

    def _jouer(self, whist, e, graine, contrats):
        coups = 0
        verifier_vue = graine % 10 == 0
        while (j := whist.joueur_actif(e)) is not None:
            coup = whist.adversaire(e, j)
            essais = e["essais"]
            try:
                e, _ = whist.appliquer(e, j, coup)
            except CoupRefuse as refus:
                self.fail(f"joueur {j}, phase {e['phase']} : coup refusé {coup} ({refus})")
            if e["essais"] > essais and coup["action"] == "passer":
                contrats["rejouee"] += 1
            if e["phase"] in ("fin_donne", "terminee") and coup["action"] == "jouer":
                contrats[e["contrat"]["code"]] += 1
                self.assertEqual(sum(e["scores"][-1]), 0)
                if e["contrat"]["code"] not in MISERES:
                    self.assertEqual(e["plis_joues"], NB_PLIS)
            if verifier_vue:
                valider_vue(whist.vue(e, 0))
            coups += 1
            self.assertLess(coups, COUPS_MAX, "la partie ne finit pas")
        self.assertEqual(e["phase"], "terminee")
        self.assertEqual(len(e["scores"]), e["options"]["donnes"])
        valider_vue(whist.vue(e, 0))
