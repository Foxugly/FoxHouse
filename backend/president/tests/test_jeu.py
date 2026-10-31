import copy
import json

from django.test import SimpleTestCase

from president.jeu import President
from president.options import OPTIONS
from tapis import registre
from tapis.jeu import CoupRefuse
from tapis.options import OptionsInvalides, valider


def partie(nb=4, graine=7, **options):
    return President().nouvelle_partie(options, nb, graine)


def etat_pli(mains, actif=0, **options):
    """Un pli vide à entamer par `actif` ; chaque siège tient exactement sa main."""
    etat = partie(nb=len(mains), **options)
    etat["mains"] = [list(m) for m in mains]
    etat["actif"] = actif
    return etat


def jouer(etat, j, cartes):
    return President().appliquer(etat, j, {"action": "jouer", "cartes": cartes})


def passer(etat, j):
    return President().appliquer(etat, j, {"action": "passer"})


def ids(actions):
    return [a["id"] for a in actions]


class RegistreTests(SimpleTestCase):
    def test_inscrit_au_registre(self):
        jeu = registre.obtenir("president")
        self.assertIsInstance(jeu, President)
        d = jeu.decrire()
        self.assertEqual((d["code"], d["nom"]), ("president", "Président"))
        self.assertEqual((d["min_joueurs"], d["max_joueurs"]), (3, 7))
        self.assertEqual(
            [(o["code"], o["type"], o["defaut"]) for o in d["options"]],
            [("deux_ferme", "booleen", True), ("echanges", "booleen", True),
             ("manches", "entier", 5)],
        )
        manches = d["options"][2]
        self.assertEqual((manches["minimum"], manches["maximum"]), (1, 10))

    def test_options_validees(self):
        self.assertEqual(
            valider(OPTIONS, {}), {"deux_ferme": True, "echanges": True, "manches": 5}
        )
        with self.assertRaises(OptionsInvalides):
            partie(manches=11)
        with self.assertRaises(OptionsInvalides):
            partie(deux_ferme="oui")


class NouvellePartieTests(SimpleTestCase):
    def test_toutes_les_cartes_distribuees(self):
        for nb in range(3, 8):
            with self.subTest(nb=nb):
                e = partie(nb=nb)
                toutes = [c for m in e["mains"] for c in m]
                self.assertEqual(len(toutes), 52)
                self.assertEqual(len(set(toutes)), 52)
                tailles = [len(m) for m in e["mains"]]
                self.assertLessEqual(max(tailles) - min(tailles), 1)
                self.assertEqual(e["phase"], "pli")
                # Première manche : le détenteur du 3♣ entame.
                self.assertIn("3C-1", e["mains"][e["actif"]])

    def test_nombre_de_joueurs_invalide(self):
        for nb in (2, 8):
            with self.assertRaises(ValueError):
                partie(nb=nb)

    def test_graine_de_128_bits(self):
        graine = (1 << 128) - 1
        e = partie(graine=graine)
        self.assertEqual(json.loads(json.dumps(e)), e)
        self.assertNotEqual(e["mains"], partie(graine=graine - 1)["mains"])

    def test_joueur_actif(self):
        e = partie()
        self.assertEqual(President().joueur_actif(e), e["actif"])
        e["phase"] = "terminee"
        self.assertIsNone(President().joueur_actif(e))


class ActionsTests(SimpleTestCase):
    def test_entame(self):
        e = etat_pli([["5S-1"], ["6S-1"], ["7S-1"]])
        actions = President().actions_permises(e, 0)
        self.assertEqual(
            actions, [{"id": "jouer", "libelle": "Jouer", "cartes_min": 1, "cartes_max": 4,
                       "cible": None}],
        )
        self.assertEqual(President().actions_permises(e, 1), [])

    def test_apres_l_entame(self):
        e = etat_pli([["5S-1", "5H-1", "9S-1"], ["6S-1", "6H-1"], ["7S-1"]])
        e, _ = jouer(e, 0, ["5S-1", "5H-1"])
        self.assertEqual(
            President().actions_permises(e, 1),
            [
                {"id": "jouer", "libelle": "Jouer", "cartes_min": 2, "cartes_max": 2,
                 "cible": None},
                {"id": "passer", "libelle": "Passer", "cartes_min": 0, "cartes_max": 0,
                 "cible": None},
            ],
        )


class JouerTests(SimpleTestCase):
    def test_entame_de_plusieurs_cartes(self):
        e = etat_pli([["9S-1", "9H-1", "4C-1"], ["6S-1"], ["7S-1"]])
        e2, message = jouer(e, 0, ["9S-1", "9H-1"])
        self.assertEqual(message, "Tu poses 9♠ 9♥.")
        self.assertEqual(e2["mains"][0], ["4C-1"])
        self.assertEqual(e2["pli"], {"cartes": ["9S-1", "9H-1"], "auteur": 0, "nombre": 2})
        self.assertEqual(e2["actif"], 1)
        _, message = jouer(etat_pli([["5S-1"], ["6S-1", "8S-1"], ["7S-1"]], actif=1), 1, ["6S-1"])
        self.assertEqual(message, "Ordinateur 1 pose 6♠.")

    def test_appliquer_ne_modifie_pas_l_etat(self):
        e = etat_pli([["9S-1", "9H-1", "4C-1"], ["6S-1"], ["7S-1"]])
        avant = copy.deepcopy(e)
        jouer(e, 0, ["9S-1"])
        self.assertEqual(e, avant)

    def test_refus(self):
        e = etat_pli([["9S-1", "9H-1", "9D-1", "9C-1", "4C-1", "5C-1"], ["6S-1"], ["7S-1"]])
        cas = [
            (["9S-1", "4C-1"], "Les cartes doivent être de même valeur."),
            (["9S-1", "9H-1", "9D-1", "9C-1", "4C-1"], "Choisis de 1 à 4 cartes."),
            ([], "Choisis de 1 à 4 cartes."),
            (["6S-1"], "Cette carte n'est pas dans ta main."),
            (["ZZ-1"], "Carte inconnue."),
            (["JK-1"], "Carte inconnue."),
            (["9S-1", "9S-1"], "Une même carte est choisie deux fois."),
        ]
        for cartes, attendu in cas:
            with self.subTest(cartes=cartes), self.assertRaisesMessage(CoupRefuse, attendu):
                jouer(e, 0, cartes)

    def test_refus_apres_l_entame(self):
        e = etat_pli([["9S-1", "9H-1", "4C-1"], ["5S-1", "5H-1", "QS-1", "QH-1", "9D-1", "9C-1"],
                      ["7S-1"]])
        e, _ = jouer(e, 0, ["9S-1", "9H-1"])
        cas = [
            (["QS-1"], "Choisis 2 cartes."),
            (["5S-1", "5H-1"], "Il faut une valeur plus forte que le 9."),
            (["9D-1", "9C-1"], "Il faut une valeur plus forte que le 9."),
        ]
        for cartes, attendu in cas:
            with self.subTest(cartes=cartes), self.assertRaisesMessage(CoupRefuse, attendu):
                jouer(e, 1, cartes)
        jouer(e, 1, ["QS-1", "QH-1"])  # plus fort : accepté

        e = etat_pli([["JS-1", "4C-1"], ["5S-1", "QS-1", "QH-1"], ["7S-1"]])
        e, _ = jouer(e, 0, ["JS-1"])
        with self.assertRaisesMessage(CoupRefuse, "Choisis 1 carte."):
            jouer(e, 1, ["QS-1", "QH-1"])
        with self.assertRaisesMessage(CoupRefuse, "Il faut une valeur plus forte que le valet."):
            jouer(e, 1, ["5S-1"])

    def test_ordre_des_valeurs(self):
        # 3 < 4 < … < 10 < V < D < R < A < 2 ; les couleurs ne comptent pas.
        ordre = ["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2"]
        for bas, haut in zip(ordre, ordre[1:]):
            with self.subTest(bas=bas, haut=haut):
                e = etat_pli([[f"{bas}C-1", "4D-1"], [f"{haut}S-1", f"{bas}H-1", "3D-1"],
                              ["7S-1"]], deux_ferme=False)
                e, _ = jouer(e, 0, [f"{bas}C-1"])
                jouer(e, 1, [f"{haut}S-1"])
                with self.assertRaises(CoupRefuse):
                    jouer(e, 1, [f"{bas}H-1"])

    def test_passer_a_l_entame_refuse(self):
        e = etat_pli([["5S-1"], ["6S-1"], ["7S-1"]])
        with self.assertRaisesMessage(CoupRefuse, "Tu entames : tu ne peux pas passer."):
            passer(e, 0)

    def test_pas_son_tour_et_action_inconnue(self):
        e = etat_pli([["5S-1"], ["6S-1"], ["7S-1"]])
        with self.assertRaisesMessage(CoupRefuse, "Ce n'est pas ton tour."):
            jouer(e, 1, ["6S-1"])
        with self.assertRaisesMessage(CoupRefuse, "Action impossible maintenant."):
            President().appliquer(e, 0, {"action": "rendre", "cartes": ["5S-1"]})
        with self.assertRaisesMessage(CoupRefuse, "Action manquante."):
            President().appliquer(e, 0, {})

    def test_passer(self):
        e = etat_pli([["5S-1", "4C-1"], ["6S-1", "8S-1"], ["7S-1", "8H-1"]])
        e, _ = jouer(e, 0, ["5S-1"])
        e, message = passer(e, 1)
        self.assertEqual(message, "Ordinateur 1 passe.")
        self.assertEqual(e["actif"], 2)
        self.assertEqual(e["passes"], [1])


class FinDuPliTests(SimpleTestCase):
    def test_tous_les_autres_passent(self):
        e = etat_pli([["5S-1", "4C-1"], ["6S-1", "8S-1"], ["7S-1", "8H-1"], ["9S-1", "9H-1"]])
        e, _ = jouer(e, 0, ["5S-1"])
        e, _ = passer(e, 1)
        e, _ = passer(e, 2)
        e, message = passer(e, 3)
        self.assertEqual(message, "Ordinateur 3 passe. Pli fermé : tu entames.")
        self.assertEqual(e["actif"], 0)
        self.assertEqual(e["pli"]["nombre"], 0)  # entame : 1 à 4 cartes
        self.assertEqual(e["pli"]["cartes"], ["5S-1"])  # reste affiché jusqu'à l'entame
        self.assertEqual(e["passes"], [])
        self.assertEqual(ids(President().actions_permises(e, 0)), ["jouer"])
        # Après la fermeture, n'importe quelle valeur peut entamer, même plus basse.
        e, _ = jouer(e, 0, ["4C-1"])
        self.assertEqual(e["pli"], {"cartes": ["4C-1"], "auteur": 0, "nombre": 1})

    def test_qui_a_passe_peut_rejouer(self):
        e = etat_pli([["5S-1", "4C-1", "KS-1"], ["6S-1", "9D-1", "3S-1"], ["7S-1", "8H-1"],
                      ["8S-1", "9H-1"]])
        e, _ = jouer(e, 0, ["5S-1"])
        e, _ = passer(e, 1)
        e, _ = jouer(e, 2, ["7S-1"])
        e, _ = passer(e, 3)
        e, _ = passer(e, 0)
        e, _ = jouer(e, 1, ["9D-1"])  # a passé, rejoue dans le même pli
        self.assertEqual(e["pli"]["auteur"], 1)
        e, _ = passer(e, 2)
        e, _ = passer(e, 3)
        e, _ = jouer(e, 0, ["KS-1"])  # avait passé aussi
        e, _ = passer(e, 1)
        e, _ = passer(e, 2)
        e, message = passer(e, 3)
        self.assertEqual(message, "Ordinateur 3 passe. Pli fermé : tu entames.")
        self.assertEqual(e["actif"], 0)

    def test_le_pli_ne_ferme_pas_tant_qu_un_autre_n_a_pas_passe(self):
        # Seuls les passes à la suite de la dernière combinaison comptent.
        e = etat_pli([["5S-1", "4C-1"], ["6S-1", "3S-1"], ["7S-1", "8H-1"]])
        e, _ = jouer(e, 0, ["5S-1"])
        e, _ = passer(e, 1)
        e, _ = jouer(e, 2, ["7S-1"])
        e, _ = passer(e, 0)
        self.assertEqual(e["actif"], 1)
        self.assertEqual(e["pli"]["nombre"], 1)
        e, message = passer(e, 1)
        self.assertEqual(message, "Ordinateur 1 passe. Pli fermé : Ordinateur 2 entame.")
        self.assertEqual(e["actif"], 2)

    def test_auteur_sorti_le_suivant_en_jeu_entame(self):
        # L'auteur de la combinaison a fini sa main : tous les joueurs encore en jeu passent,
        # puis le joueur qui le suit (encore en jeu) entame.
        e = etat_pli([["5S-1", "4C-1"], ["6S-1", "3S-1"], ["7S-1"], ["8S-1", "9H-1"]], actif=2)
        e, message = jouer(e, 2, ["7S-1"])
        self.assertEqual(message, "Ordinateur 2 pose 7♠. Ordinateur 2 sort : Président.")
        self.assertEqual(e["sortis"], [2])
        self.assertEqual(e["actif"], 3)
        e, _ = passer(e, 3)
        e, _ = passer(e, 0)
        self.assertEqual(e["actif"], 1)
        e, message = passer(e, 1)
        self.assertEqual(message, "Ordinateur 1 passe. Pli fermé : Ordinateur 3 entame.")
        self.assertEqual(e["actif"], 3)
        self.assertEqual(e["pli"]["nombre"], 0)

    def test_auteur_sorti_et_son_suivant_deja_sorti(self):
        e = etat_pli([["5S-1", "4C-1"], ["6S-1", "3S-1"], ["7S-1"], []], actif=2)
        e["sortis"] = [3]
        e, message = jouer(e, 2, ["7S-1"])
        self.assertEqual(message, "Ordinateur 2 pose 7♠. Ordinateur 2 sort : Vice-président.")
        self.assertEqual(e["actif"], 0)  # le siège 3 est sorti
        e, _ = passer(e, 0)
        e, message = passer(e, 1)
        self.assertEqual(message, "Ordinateur 1 passe. Pli fermé : tu entames.")
        self.assertEqual(e["actif"], 0)

    def test_deux_joueurs_en_jeu(self):
        e = etat_pli([["5S-1", "4C-1", "3C-1"], ["6S-1", "3S-1"], []])
        e["sortis"] = [2]
        e, _ = jouer(e, 0, ["5S-1"])
        self.assertEqual(e["actif"], 1)
        e, message = passer(e, 1)
        self.assertEqual(message, "Ordinateur 1 passe. Pli fermé : tu entames.")
        self.assertEqual(e["actif"], 0)
        e, _ = jouer(e, 0, ["3C-1"])
        e, _ = jouer(e, 1, ["6S-1"])
        e, message = passer(e, 0)
        self.assertEqual(message, "Tu passes. Pli fermé : Ordinateur 1 entame.")
        self.assertEqual(e["actif"], 1)

    def test_auteur_sorti_avec_deux_joueurs_restants(self):
        e = etat_pli([["5S-1"], ["6S-1", "3S-1"], ["7S-1", "4S-1"], ["8S-1"]])
        e["sortis"] = [3]
        e["mains"][3] = []
        e, _ = jouer(e, 0, ["5S-1"])  # sort : il reste 1 et 2
        self.assertEqual(e["sortis"], [3, 0])
        self.assertEqual(e["actif"], 1)
        e, _ = passer(e, 1)
        e, message = passer(e, 2)
        self.assertEqual(message, "Ordinateur 2 passe. Pli fermé : Ordinateur 1 entame.")
        self.assertEqual(e["actif"], 1)

    def test_le_dernier_en_jeu_devient_pauvre_sans_jouer(self):
        e = etat_pli([["5S-1"], ["6S-1", "3S-1"], ["7S-1", "4S-1"]], manches=2)
        e["sortis"] = [2]
        e["mains"][2] = []
        e, message = jouer(e, 0, ["5S-1"])
        self.assertEqual(
            message,
            "Tu poses 5♠. Tu sors : Neutre. Ordinateur 1 reste seul : Pauvre. "
            "Fin de la manche 1.",
        )
        self.assertEqual(e["sortis"], [2, 0, 1])
        self.assertEqual(e["phase"], "fin_manche")
        self.assertEqual(e["rangs"], [1, 2, 0])
        self.assertEqual(e["points"], [[1, 0, 2]])
        self.assertEqual(e["actif"], 0)
        self.assertEqual(ids(President().actions_permises(e, 0)), ["manche_suivante"])
        self.assertEqual(President().actions_permises(e, 1), [])

    def test_l_humain_reste_seul(self):
        e = etat_pli([["5S-1", "3S-1"], ["6S-1"], []], actif=1, manches=1)
        e["sortis"] = [2]
        e, message = jouer(e, 1, ["6S-1"])
        self.assertEqual(
            message,
            "Ordinateur 1 pose 6♠. Ordinateur 1 sort : Neutre. Tu restes seul : Pauvre. "
            "Fin de la partie.",
        )
        self.assertEqual(e["phase"], "terminee")
        self.assertIsNone(President().joueur_actif(e))
        self.assertEqual(President().actions_permises(e, 0), [])


class DeuxFermeTests(SimpleTestCase):
    def test_le_2_ferme_le_pli(self):
        e = etat_pli([["5S-1", "4C-1"], ["2S-1", "2H-1", "3S-1"], ["7S-1", "7H-1"]])
        e, _ = jouer(e, 0, ["5S-1"])
        e, message = jouer(e, 1, ["2S-1"])
        self.assertEqual(message, "Ordinateur 1 pose 2♠. Le 2 ferme le pli : Ordinateur 1 entame.")
        self.assertEqual(e["actif"], 1)
        self.assertEqual(e["pli"]["nombre"], 0)
        self.assertEqual(ids(President().actions_permises(e, 1)), ["jouer"])

    def test_le_2_ferme_et_son_auteur_est_sorti(self):
        e = etat_pli([["5S-1", "4C-1"], ["2S-1", "2H-1"], ["7S-1", "7H-1"], ["8S-1"]])
        e, _ = jouer(e, 0, ["5S-1"])
        e, _ = jouer(e, 1, ["2S-1"])
        self.assertEqual(e["actif"], 1)
        e, message = jouer(e, 1, ["2H-1"])  # entame avec son dernier 2
        self.assertEqual(
            message,
            "Ordinateur 1 pose 2♥. Ordinateur 1 sort : Président. "
            "Le 2 ferme le pli : Ordinateur 2 entame.",
        )
        self.assertEqual(e["actif"], 2)

    def test_sans_l_option_le_2_ne_ferme_pas(self):
        e = etat_pli([["5S-1", "4C-1"], ["2S-1", "3S-1"], ["7S-1", "7H-1"]], deux_ferme=False)
        e, _ = jouer(e, 0, ["5S-1"])
        e, message = jouer(e, 1, ["2S-1"])
        self.assertEqual(message, "Ordinateur 1 pose 2♠.")
        self.assertEqual(e["actif"], 2)
        e, _ = passer(e, 2)
        e, message = passer(e, 0)
        self.assertEqual(message, "Tu passes. Pli fermé : Ordinateur 1 entame.")


class RangsTests(SimpleTestCase):
    def test_noms_et_points(self):
        from president.manche import nom_rang

        attendus = {
            3: ["Président", "Neutre", "Pauvre"],
            4: ["Président", "Vice-président", "Vice-pauvre", "Pauvre"],
            5: ["Président", "Vice-président", "Neutre", "Vice-pauvre", "Pauvre"],
            7: ["Président", "Vice-président", "Neutre", "Neutre", "Neutre", "Vice-pauvre",
                "Pauvre"],
        }
        for nb, noms in attendus.items():
            self.assertEqual([nom_rang(r, nb) for r in range(nb)], noms)

    def test_manche_complete_a_quatre(self):
        e = etat_pli([["5S-1"], ["6S-1"], ["7S-1"], ["8S-1", "3C-1"]])
        e, _ = jouer(e, 0, ["5S-1"])
        e, _ = jouer(e, 1, ["6S-1"])
        e, _ = jouer(e, 2, ["7S-1"])
        self.assertEqual(e["phase"], "fin_manche")
        self.assertEqual(e["sortis"], [0, 1, 2, 3])
        self.assertEqual(e["points"], [[3, 2, 1, 0]])


def fin_de_manche(nb, sortis, **options):
    """Une manche finie dans l'ordre `sortis` (le premier est Président)."""
    e = partie(nb=nb, **options)
    e["mains"] = [[] for _ in range(nb)]
    e["sortis"] = list(sortis)
    e["rangs"] = [sortis.index(s) for s in range(nb)]
    e["points"] = [[nb - 1 - e["rangs"][s] for s in range(nb)]]
    e["phase"], e["actif"] = "fin_manche", 0
    return e


class MancheSuivanteTests(SimpleTestCase):
    def test_don_d_office_et_retour_du_president(self):
        jeu = President()
        e = fin_de_manche(4, [2, 0, 3, 1])  # Président 2, Vice-président 0, Vice-pauvre 3, Pauvre 1
        e, message = jeu.appliquer(e, 0, {"action": "manche_suivante"})
        self.assertEqual(
            message,
            "La manche 2 commence. Ordinateur 1 (Pauvre) donne ses 2 meilleures cartes à "
            "Ordinateur 2 (Président). Ordinateur 3 (Vice-pauvre) te donne sa meilleure carte.",
        )
        self.assertEqual(e["manche"], 2)
        self.assertEqual(e["phase"], "echange")
        self.assertEqual(e["actif"], 2)
        self.assertEqual([len(m) for m in e["mains"]], [14, 11, 15, 12])
        self.assertEqual(len(e["recues"][2]), 2)
        self.assertEqual(len(e["recues"][0]), 1)
        self.assertEqual(e["recues"][1], [])
        self.assertEqual(sorted(c for m in e["mains"] for c in m), sorted(
            c for m in partie()["mains"] for c in m))

        # Le Pauvre a donné ses deux plus fortes cartes.
        from president.manche import force

        donnees = e["recues"][2]
        self.assertGreaterEqual(min(force(c) for c in donnees),
                                max(force(c) for c in e["mains"][1]))

        actions = jeu.actions_permises(e, 2)
        self.assertEqual(
            actions,
            [{"id": "rendre", "libelle": "Donner au Pauvre", "cartes_min": 2, "cartes_max": 2,
              "cible": None}],
        )
        rendues = e["mains"][2][:2]
        with self.assertRaisesMessage(CoupRefuse, "Choisis 2 cartes."):
            jeu.appliquer(e, 2, {"action": "rendre", "cartes": rendues[:1]})
        with self.assertRaisesMessage(CoupRefuse, "Action impossible maintenant."):
            jeu.appliquer(e, 2, {"action": "jouer", "cartes": rendues[:1]})
        avant = e
        e, message = jeu.appliquer(e, 2, {"action": "rendre", "cartes": rendues})
        self.assertIsNone(message)  # coup privé
        self.assertEqual(
            jeu.message_prive(avant, 2, {"action": "rendre", "cartes": rendues}),
            "Ordinateur 2 donne {} au Pauvre.".format(
                " ".join(_etiquette(c) for c in rendues)),
        )
        self.assertEqual(sorted(e["recues"][1]), sorted(rendues))
        self.assertEqual([len(m) for m in e["mains"]], [14, 13, 13, 12])

        # Puis le Vice-président (l'humain ici) rend une carte au Vice-pauvre.
        self.assertEqual(e["actif"], 0)
        self.assertEqual(jeu.actions_permises(e, 0)[0]["libelle"], "Donner au Vice-pauvre")
        avant = e
        carte = e["mains"][0][0]
        e, message = jeu.appliquer(e, 0, {"action": "rendre", "cartes": [carte]})
        self.assertIsNone(message)
        self.assertEqual(
            jeu.message_prive(avant, 0, {"action": "rendre", "cartes": [carte]}),
            f"Tu donnes {_etiquette(carte)} au Vice-pauvre.",
        )
        self.assertEqual([len(m) for m in e["mains"]], [13, 13, 13, 13])
        # Le Pauvre entame.
        self.assertEqual((e["phase"], e["actif"]), ("pli", 1))
        self.assertEqual(e["pli"], {"cartes": [], "auteur": None, "nombre": 0})

    def test_le_don_d_office_ne_dit_pas_les_cartes(self):
        e = fin_de_manche(3, [1, 2, 0])
        e, message = President().appliquer(e, 0, {"action": "manche_suivante"})
        self.assertEqual(
            message,
            "La manche 2 commence. Tu donnes tes 2 meilleures cartes à Ordinateur 1 (Président).",
        )
        for c in e["recues"][1]:
            self.assertNotIn(_etiquette(c), message)
        e = fin_de_manche(3, [0, 2, 1])
        _, message = President().appliquer(e, 0, {"action": "manche_suivante"})
        self.assertEqual(
            message,
            "La manche 2 commence. Ordinateur 1 (Pauvre) te donne ses 2 meilleures cartes.",
        )

    def test_a_trois_un_seul_echange(self):
        jeu = President()
        e = fin_de_manche(3, [1, 2, 0])
        e, _ = jeu.appliquer(e, 0, {"action": "manche_suivante"})
        self.assertEqual((e["phase"], e["actif"]), ("echange", 1))
        e, _ = jeu.appliquer(e, 1, {"action": "rendre", "cartes": e["mains"][1][:2]})
        self.assertEqual((e["phase"], e["actif"]), ("pli", 0))

    def test_sans_echanges_le_pauvre_entame(self):
        jeu = President()
        e = fin_de_manche(5, [2, 0, 3, 4, 1], echanges=False)
        e, message = jeu.appliquer(e, 0, {"action": "manche_suivante"})
        self.assertEqual(message, "La manche 2 commence. Ordinateur 1 entame.")
        self.assertEqual((e["phase"], e["actif"]), ("pli", 1))
        self.assertEqual(e["recues"], [[]] * 5)
        self.assertEqual(sum(len(m) for m in e["mains"]), 52)

    def test_derniere_manche(self):
        e = etat_pli([["5S-1"], ["6S-1", "7S-1"], ["9S-1"]], manches=2)
        e["manche"] = 2
        e["points"] = [[2, 1, 0]]
        e, message = jouer(e, 0, ["5S-1"])
        e, message = jouer(e, 1, ["6S-1"])
        e, message = jouer(e, 2, ["9S-1"])
        self.assertTrue(message.endswith("Fin de la partie."))
        self.assertEqual(e["phase"], "terminee")
        self.assertEqual(e["points"], [[2, 1, 0], [2, 0, 1]])


def _etiquette(c):
    from president.manche import etiquette_carte

    return etiquette_carte(c)
