import copy
import json

from django.test import SimpleTestCase

from tapis import registre
from tapis.cartes import enseigne, melanger, paquet, valeur
from tapis.jeu import CoupRefuse
from whist import manche
from whist.jeu import Whist
from whist.tests.aides import appliquer, etat_encheres, etat_plis, jouer, jouer_le_pli, partie
from whist.vue import vue


def ids_actions(e, j):
    return [a["id"] for a in Whist().actions_permises(e, j)]


def avec_mains(e, mains):
    """Remplace les mains et recalcule le trou, comme à la distribution."""
    e["mains"] = [manche.trier(m) for m in mains]
    e["retournee"] = e["mains"][e["donneur"]][-1]
    e["contrat"] = None
    e["atout"] = None
    e["phase"] = "encheres"
    e["actif"] = (e["donneur"] + 1) % 4
    return manche._trou(e)


def mains_de(par_siege):
    """Quatre mains de 13 : les cartes imposées par siège, le reste complété dans l'ordre."""
    imposees = {c for cartes in par_siege.values() for c in cartes}
    reste = [c for c in paquet(1, 0) if c not in imposees]
    mains = []
    for s in range(4):
        main = list(par_siege.get(s, []))
        while len(main) < 13:
            main.append(reste.pop(0))
        mains.append(main)
    return mains


class RegistreTests(SimpleTestCase):
    def test_inscrit_au_registre(self):
        jeu = registre.obtenir("whist")
        self.assertIsInstance(jeu, Whist)
        d = jeu.decrire()
        self.assertEqual(
            (d["code"], d["nom"], d["min_joueurs"], d["max_joueurs"]),
            ("whist", "Whist à la couleur", 4, 4),
        )
        self.assertEqual(d["options"], [
            {"code": "donnes", "libelle": "Nombre de donnes", "type": "entier", "defaut": 8,
             "minimum": 4, "maximum": 24},
            {"code": "trou", "libelle": "Trou (trois as)", "type": "booleen", "defaut": True},
            {"code": "misere", "libelle": "Misère et misère ouverte", "type": "booleen",
             "defaut": True},
        ])

    def test_quatre_joueurs_exactement(self):
        for nb in (2, 3, 5):
            with self.assertRaises(ValueError):
                Whist().nouvelle_partie({}, nb, 1)


class DistributionTests(SimpleTestCase):
    def test_treize_cartes_chacun_et_retournee_au_donneur(self):
        e = partie(trou=False)
        cartes = [c for m in e["mains"] for c in m]
        self.assertEqual(sorted(cartes), sorted(paquet(1, 0)))
        self.assertEqual({len(m) for m in e["mains"]}, {13})
        self.assertEqual(e["donneur"], 3)
        self.assertIn(e["retournee"], e["mains"][3])
        self.assertEqual((e["phase"], e["actif"]), ("encheres", 0))

    def test_retournee_est_la_derniere_carte(self):
        e = partie(trou=False)
        melange = melanger(paquet(1, 0), e["graine"] * 1000 + e["essais"])
        self.assertEqual(e["retournee"], melange[-1])
        self.assertEqual(set(e["mains"][0]), set(melange[0::4]))

    def test_graine_de_128_bits(self):
        whist = Whist()
        graine = (1 << 128) - 1
        e = partie(graine=graine, donnes=4)
        self.assertEqual(json.loads(json.dumps(e)), e)
        coups = 0
        while (j := whist.joueur_actif(e)) is not None:
            e, _ = whist.appliquer(e, j, whist.adversaire(e, j))
            coups += 1
            self.assertLess(coups, 3000)
        self.assertEqual(e["graine"], graine)
        self.assertNotEqual(partie(graine=graine)["mains"], partie(graine=graine - 1)["mains"])

    def test_appliquer_ne_modifie_pas_l_etat(self):
        e = etat_encheres()
        avant = copy.deepcopy(e)
        appliquer(e, 0, "demander")
        self.assertEqual(e, avant)


class TrouTests(SimpleTestCase):
    def test_trois_as_jouent_avec_le_quatrieme(self):
        e = etat_encheres()
        message = avec_mains(e, mains_de({1: ["AS-1", "AH-1", "AD-1"], 3: ["AC-1", "7H-1"]}))
        self.assertEqual(e["contrat"], {"code": "trou", "preneurs": [1, 3]})
        self.assertEqual(e["atout"], enseigne(e["retournee"]))
        self.assertEqual((e["phase"], e["actif"]), ("plis", 0))
        self.assertEqual(
            message,
            "Trou ! Ordinateur 1 a trois as et joue avec Ordinateur 3, qui a le quatrième as : "
            f"8 plis à deux, atout {manche.COULEURS[e['atout']]}.",
        )

    def test_trou_du_joueur_humain(self):
        e = etat_encheres()
        message = avec_mains(e, mains_de({0: ["AS-1", "AH-1", "AC-1"], 2: ["AD-1"]}))
        self.assertEqual(e["contrat"]["preneurs"], [0, 2])
        self.assertTrue(message.startswith(
            "Trou ! Tu as trois as et joues avec Ordinateur 2, qui a le quatrième as"), message)

    def test_quatre_as_jouent_avec_le_roi_de_coeur(self):
        e = etat_encheres()
        avec_mains(e, mains_de({2: ["AS-1", "AH-1", "AD-1", "AC-1"], 1: ["KH-1"]}))
        self.assertEqual(e["contrat"], {"code": "trou", "preneurs": [1, 2]})
        # Avec aussi le roi, c'est la dame.
        e = etat_encheres()
        message = avec_mains(
            e, mains_de({2: ["AS-1", "AH-1", "AD-1", "AC-1", "KH-1"], 0: ["QH-1"]})
        )
        self.assertEqual(e["contrat"]["preneurs"], [0, 2])
        self.assertIn("avec toi, qui as le D♥", message)

    def test_le_trou_arrive_a_la_distribution_et_seulement_avec_l_option(self):
        trous = [g for g in range(1, 80) if partie(graine=g)["phase"] == "plis"]
        self.assertTrue(trous)
        for g in trous:
            e = partie(graine=g)
            self.assertEqual(e["contrat"]["code"], "trou")
            self.assertTrue(any(
                sum(1 for c in e["mains"][s] if valeur(c) == "A") >= 3
                for s in e["contrat"]["preneurs"]
            ))
            sans = partie(graine=g, trou=False)
            self.assertEqual(sans["mains"], e["mains"])
            self.assertEqual((sans["phase"], sans["contrat"]), ("encheres", None))


class EncheresTests(SimpleTestCase):
    def test_annonces_au_depart(self):
        e = etat_encheres()
        self.assertEqual(ids_actions(e, 0), [
            "passer", "demander", "seul", "abondance_9", "misere", "abondance_10",
            "abondance_11", "misere_ouverte", "abondance_12", "solo", "solo_slim",
        ])
        self.assertEqual(ids_actions(e, 1), [])

    def test_sans_misere(self):
        e = etat_encheres(misere=False)
        self.assertNotIn("misere", ids_actions(e, 0))
        self.assertNotIn("misere_ouverte", ids_actions(e, 0))
        with self.assertRaisesMessage(CoupRefuse, "Action impossible maintenant."):
            appliquer(e, 0, "misere")

    def test_il_faut_annoncer_plus_haut(self):
        e = etat_encheres()
        e, message = appliquer(e, 0, "seul")
        self.assertEqual(message, "Tu annonces seul.")
        self.assertEqual(e["actif"], 1)
        self.assertEqual(ids_actions(e, 1)[:3], ["passer", "abondance_9", "misere"])
        with self.assertRaisesMessage(CoupRefuse, "Action impossible maintenant."):
            appliquer(e, 1, "demander")
        e, message = appliquer(e, 1, "misere")
        self.assertEqual(message, "Ordinateur 1 annonce misère.")
        self.assertEqual(ids_actions(e, 2)[:2], ["passer", "abondance_10"])

    def test_une_annonce_ne_prend_pas_de_carte(self):
        e = etat_encheres()
        with self.assertRaisesMessage(CoupRefuse, "Cette action ne prend pas de carte."):
            appliquer(e, 0, "passer", [e["mains"][0][0]])

    def test_demande_acceptee_vaut_l_emballage(self):
        e = etat_encheres()
        e, message = appliquer(e, 0, "demander")
        self.assertEqual(message, "Tu demandes.")
        self.assertEqual(ids_actions(e, 1)[:3], ["passer", "accepter", "seul"])
        e, _ = appliquer(e, 1, "passer")
        e, message = appliquer(e, 2, "accepter")
        self.assertEqual(message, "Ordinateur 2 accepte : emballage avec toi.")
        self.assertEqual(e["enchere"], {"code": "emballage", "preneur": 0, "partenaire": 2})
        self.assertEqual(e["actif"], 3)
        self.assertNotIn("accepter", ids_actions(e, 3))
        self.assertEqual(ids_actions(e, 3)[1], "seul")  # seul couvre l'emballage
        e, message = appliquer(e, 3, "passer")
        atout = manche.COULEURS[enseigne(e["retournee"])]
        self.assertEqual(
            message, f"Ordinateur 3 passe. Contrat : emballage pour Ordinateur 2 et toi, "
                     f"atout {atout}.")
        self.assertEqual(e["contrat"], {"code": "emballage", "preneurs": [0, 2]})
        self.assertEqual(e["atout"], enseigne(e["retournee"]))
        self.assertEqual((e["phase"], e["actif"]), ("plis", 0))

    def test_on_n_accepte_pas_sa_propre_demande(self):
        e = etat_encheres()
        e, _ = appliquer(e, 0, "demander")
        for j in (1, 2, 3):
            e, _ = appliquer(e, j, "seul" if j == 1 else "passer")
        # Ordinateur 1 a couvert la demande : 0 parle encore, sans « accepter ».
        self.assertEqual(e["actif"], 0)
        self.assertNotIn("accepter", ids_actions(e, 0))

    def test_qui_a_passe_ne_revient_pas(self):
        e = etat_encheres()
        e, _ = appliquer(e, 0, "passer")
        e, _ = appliquer(e, 1, "demander")
        e, _ = appliquer(e, 2, "seul")
        e, _ = appliquer(e, 3, "passer")
        self.assertEqual(e["actif"], 1)  # 0 a passé : on le saute
        e, message = appliquer(e, 1, "passer")
        self.assertEqual(e["contrat"], {"code": "seul", "preneurs": [2]})
        self.assertIn("Contrat : seul pour Ordinateur 2", message)

    def test_demande_sans_partenaire(self):
        e = etat_encheres()
        e, _ = appliquer(e, 0, "passer")
        e, _ = appliquer(e, 1, "demander")
        e, _ = appliquer(e, 2, "passer")
        e, message = appliquer(e, 3, "passer")
        self.assertEqual(message, "Ordinateur 3 passe. Personne n'accepte la demande "
                                  "d'Ordinateur 1.")
        self.assertEqual((e["phase"], e["actif"]), ("demande_seule", 1))
        self.assertEqual(ids_actions(e, 1), ["seul", "passer"])
        joue, message = appliquer(e, 1, "seul")
        self.assertEqual(joue["contrat"], {"code": "seul", "preneurs": [1]})
        self.assertEqual(joue["phase"], "plis")
        self.assertTrue(message.startswith("Ordinateur 1 joue seul. Contrat : seul"), message)
        rejoue, message = appliquer(e, 1, "passer")
        self.assertEqual(rejoue["donneur"], 0)
        self.assertEqual(rejoue["scores"], [])
        self.assertTrue(message.startswith(
            "Ordinateur 1 passe : la donne est rejouée, tu distribues."), message)
        e = etat_encheres()
        e, _ = appliquer(e, 0, "demander")
        for j in (1, 2):
            e, _ = appliquer(e, j, "passer")
        e, message = appliquer(e, 3, "passer")
        self.assertEqual(message, "Ordinateur 3 passe. Personne n'accepte ta demande.")
        self.assertEqual((e["phase"], e["actif"]), ("demande_seule", 0))

    def test_tout_le_monde_passe(self):
        e = etat_encheres()
        for j in (0, 1, 2):
            e, message = appliquer(e, j, "passer")
            self.assertEqual(e["phase"], "encheres")
        e, message = appliquer(e, 3, "passer")
        self.assertTrue(message.startswith(
            "Ordinateur 3 passe. Tout le monde passe : la donne est rejouée, tu distribues."),
            message)
        self.assertEqual((e["donneur"], e["scores"], e["essais"]), (0, [], 2))
        self.assertIn(e["retournee"], e["mains"][0])
        if e["phase"] == "encheres":
            self.assertEqual(e["actif"], 1)

    def test_donne_rejouee_ne_compte_pas(self):
        e = etat_encheres(donnes=4)
        for j in (0, 1, 2, 3):
            e, _ = appliquer(e, j, "passer")
        menu = {m["libelle"]: m["valeur"] for m in vue(e, 0)["menu"]}
        self.assertEqual(menu["Donne"], "1 / 4")

    def test_abondance_et_choix_de_l_atout(self):
        e = etat_encheres()
        e, _ = appliquer(e, 0, "passer")
        e, _ = appliquer(e, 1, "abondance_9")
        e, _ = appliquer(e, 2, "passer")
        e, message = appliquer(e, 3, "passer")
        self.assertTrue(message.endswith(
            "Contrat : abondance 9 pour Ordinateur 1, qui choisit l'atout."), message)
        self.assertEqual((e["phase"], e["actif"]), ("atout", 1))
        self.assertEqual(ids_actions(e, 1), ["atout_S", "atout_H", "atout_D", "atout_C"])
        e, message = appliquer(e, 1, "atout_D")
        self.assertEqual(message, "Ordinateur 1 choisit l'atout : carreau.")
        self.assertEqual((e["atout"], e["phase"], e["actif"]), ("D", "plis", 0))

    def test_abondance_du_joueur_humain(self):
        e = etat_encheres()
        e, _ = appliquer(e, 0, "solo_slim")
        for j in (1, 2):
            e, _ = appliquer(e, j, "passer")
        e, message = appliquer(e, 3, "passer")
        self.assertTrue(message.endswith("Contrat : solo slim pour toi, qui choisis l'atout."))
        self.assertEqual((e["phase"], e["actif"]), ("atout", 0))
        e, message = appliquer(e, 0, "atout_S")
        self.assertEqual(message, "Tu choisis l'atout : pique.")

    def test_misere_sans_atout(self):
        e = etat_encheres()
        e, _ = appliquer(e, 0, "misere_ouverte")
        for j in (1, 2):
            e, _ = appliquer(e, j, "passer")
        e, message = appliquer(e, 3, "passer")
        self.assertTrue(message.endswith("Contrat : misère ouverte pour toi, sans atout."))
        self.assertIsNone(e["atout"])

    def test_solo_a_l_atout_retourne(self):
        e = etat_encheres()
        e, _ = appliquer(e, 0, "passer")
        e, _ = appliquer(e, 1, "solo")
        e, _ = appliquer(e, 2, "passer")
        e, _ = appliquer(e, 3, "passer")
        self.assertEqual(e["contrat"], {"code": "solo", "preneurs": [1]})
        self.assertEqual(e["atout"], enseigne(e["retournee"]))


class PlisTests(SimpleTestCase):
    def test_il_faut_fournir(self):
        e = etat_plis([["2S-1"], ["3S-1", "4H-1"], ["5D-1"], ["6C-1"]])
        e, message = jouer(e, 0, "2S-1")
        self.assertEqual(message, "Tu joues 2♠.")
        with self.assertRaisesMessage(CoupRefuse, "Tu dois fournir : pique."):
            jouer(e, 1, "4H-1")
        e, _ = jouer(e, 1, "3S-1")
        e, _ = jouer(e, 2, "5D-1")  # pas de pique : n'importe quoi

    def test_refus_de_cartes(self):
        e = etat_plis([["2S-1"], ["3S-1"], ["5D-1"], ["6C-1"]])
        with self.assertRaisesMessage(CoupRefuse, "Cette carte n'est pas dans ta main."):
            jouer(e, 0, "3S-1")
        with self.assertRaisesMessage(CoupRefuse, "Carte inconnue."):
            jouer(e, 0, "ZZ-1")
        with self.assertRaisesMessage(CoupRefuse, "Choisis 1 carte."):
            appliquer(e, 0, "jouer", [])
        with self.assertRaisesMessage(CoupRefuse, "Action impossible maintenant."):
            jouer(e, 1, "3S-1")

    def test_l_atout_remporte_le_pli(self):
        e = etat_plis([["AS-1", "2D-1"], ["KS-1", "3D-1"], ["2H-1", "4D-1"], ["QS-1", "5D-1"]])
        e, message = jouer_le_pli(e, ["AS-1", "KS-1", "2H-1", "QS-1"])
        self.assertTrue(message.endswith("Ordinateur 2 remporte le pli."), message)
        self.assertEqual((e["plis"], e["actif"], e["plis_joues"]), ([0, 0, 1, 0], 2, 12))
        self.assertEqual(e["dernier_pli"], [[0, "AS-1"], [1, "KS-1"], [2, "2H-1"], [3, "QS-1"]])

    def test_sans_atout_la_plus_haute_de_la_couleur(self):
        e = etat_plis([["9S-1", "2D-1"], ["KC-1", "3D-1"], ["10S-1", "4D-1"], ["2S-1", "5D-1"]],
                      atout="H")
        e, _ = jouer_le_pli(e, ["9S-1", "KC-1", "10S-1", "2S-1"])
        self.assertEqual(e["actif"], 2)
        self.assertEqual(manche.gagnant_du_pli([[0, "2S-1"], [1, "AH-1"]], None), 0)

    def test_la_misere_s_arrete_au_premier_pli_du_preneur(self):
        e = etat_plis([["AS-1", "2D-1"], ["KS-1", "3D-1"], ["2S-1", "4D-1"], ["QS-1", "5D-1"]],
                      code="misere", preneurs=[0], atout=None)
        e, message = jouer_le_pli(e, ["AS-1", "KS-1", "2S-1", "QS-1"])
        self.assertEqual(e["phase"], "fin_donne")
        self.assertIn("Tu remportes le pli. La misère est chutée. Contrat chuté (1 pli) : "
                      "tu marques −21, chacun des autres +7.", message)
        self.assertEqual(e["scores"], [[-21, 7, 7, 7]])

    def test_fin_de_donne_et_donne_suivante(self):
        e = etat_plis([["AS-1"], ["KS-1"], ["2S-1"], ["QS-1"]], code="seul", preneurs=[0])
        e["plis"] = [6, 2, 2, 2]
        e, message = jouer_le_pli(e, ["AS-1", "KS-1", "2S-1", "QS-1"])
        self.assertEqual(
            message,
            "Ordinateur 3 joue D♠. Tu remportes le pli. Contrat réussi (7 plis) : "
            "tu marques +15, chacun des autres −5. La donne est terminée.",
        )
        self.assertEqual((e["phase"], e["actif"]), ("fin_donne", 0))
        self.assertEqual(ids_actions(e, 0), ["donne_suivante"])
        e, message = appliquer(e, 0, "donne_suivante")
        self.assertEqual(e["donneur"], 0)
        self.assertTrue(message.startswith("Donne 2 : tu distribues."), message)
        self.assertEqual({len(m) for m in e["mains"]}, {13})
        self.assertEqual(e["plis"], [0, 0, 0, 0])

    def test_la_partie_finit_apres_le_nombre_de_donnes(self):
        e = etat_plis([["AS-1"], ["KS-1"], ["2S-1"], ["QS-1"]], code="emballage",
                      preneurs=[1, 3], donnes=4)
        e["scores"] = [[1, -1, 1, -1]] * 3
        e["plis"] = [3, 4, 2, 3]
        e, message = jouer_le_pli(e, ["AS-1", "KS-1", "2S-1", "QS-1"])
        self.assertTrue(message.endswith(
            "Contrat chuté (7 plis) : Ordinateur 1 et Ordinateur 3 marquent −3 chacun, "
            "les deux autres +3. La partie est terminée."), message)
        self.assertEqual(e["phase"], "terminee")
        self.assertIsNone(Whist().joueur_actif(e))
        self.assertEqual(ids_actions(e, 0), [])

    def test_bilan_a_deux_avec_le_joueur_humain(self):
        e = etat_plis([["AS-1"], ["KS-1"], ["2S-1"], ["QS-1"]], code="emballage",
                      preneurs=[0, 1])
        e["plis"] = [4, 4, 2, 2]
        e, message = jouer_le_pli(e, ["AS-1", "KS-1", "2S-1", "QS-1"])
        self.assertIn("Contrat réussi (9 plis) : Ordinateur 1 et toi marquez +3 chacun, "
                      "les deux autres −3.", message)


class PointsTests(SimpleTestCase):
    """Une ligne du tableau §2 par test, réussie et ratée ; chaque donne est à somme nulle."""

    def _verifier(self, code, preneurs, plis, attendu):
        ligne = manche.ligne_de_points(code, preneurs, plis)
        self.assertEqual(ligne, attendu, f"{code}, {plis} plis")
        self.assertEqual(sum(ligne), 0)

    def test_emballage(self):
        for code in ("emballage", "trou"):
            with self.subTest(code=code):
                self._verifier(code, [0, 2], 8, [2, -2, 2, -2])
                self._verifier(code, [0, 2], 11, [5, -5, 5, -5])
                self._verifier(code, [1, 3], 12, [-6, 6, -6, 6])
                self._verifier(code, [1, 3], 13, [-14, 14, -14, 14])
                self._verifier(code, [0, 2], 7, [-3, 3, -3, 3])
                self._verifier(code, [0, 2], 4, [-6, 6, -6, 6])

    def test_seul(self):
        self._verifier("seul", [2], 5, [-3, -3, 9, -3])
        self._verifier("seul", [2], 7, [-5, -5, 15, -5])  # l'exemple de la spec
        self._verifier("seul", [2], 13, [-11, -11, 33, -11])
        self._verifier("seul", [2], 4, [4, 4, -12, 4])
        self._verifier("seul", [2], 1, [7, 7, -21, 7])

    def test_abondances(self):
        for code, valeur_, vise in (("abondance_9", 5, 9), ("abondance_10", 7, 10),
                                    ("abondance_11", 10, 11), ("abondance_12", 15, 12)):
            with self.subTest(code=code):
                self._verifier(code, [1], vise, [-valeur_, 3 * valeur_, -valeur_, -valeur_])
                self._verifier(code, [1], 13, [-valeur_, 3 * valeur_, -valeur_, -valeur_])
                self._verifier(code, [1], vise - 1, [valeur_, -3 * valeur_, valeur_, valeur_])
                self._verifier(code, [1], 2, [valeur_, -3 * valeur_, valeur_, valeur_])

    def test_miseres(self):
        for code, valeur_ in (("misere", 7), ("misere_ouverte", 15)):
            with self.subTest(code=code):
                self._verifier(code, [3], 0, [-valeur_, -valeur_, -valeur_, 3 * valeur_])
                self._verifier(code, [3], 1, [valeur_, valeur_, valeur_, -3 * valeur_])

    def test_solos(self):
        for code, valeur_ in (("solo", 25), ("solo_slim", 30)):
            with self.subTest(code=code):
                self._verifier(code, [0], 13, [3 * valeur_, -valeur_, -valeur_, -valeur_])
                self._verifier(code, [0], 12, [-3 * valeur_, valeur_, valeur_, valeur_])

    def test_valeurs(self):
        self.assertEqual(manche.valeur_du_contrat("emballage", 13), (True, 14))
        self.assertEqual(manche.valeur_du_contrat("seul", 13), (True, 11))
        self.assertEqual(manche.valeur_du_contrat("abondance_9", 12), (True, 5))
        self.assertEqual(manche.valeur_du_contrat("misere", 0), (True, 7))

    def test_totaux(self):
        e = partie()
        e["scores"] = [[2, -2, 2, -2], [-5, -5, 15, -5]]
        self.assertEqual(manche.totaux(e), [-3, -7, 17, -7])
