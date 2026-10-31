import copy

from django.test import SimpleTestCase

from rami.jeu import Rami
from rami.options import OPTIONS
from tapis import registre
from tapis.jeu import CoupRefuse
from tapis.options import valider
from tapis.vue import valider_vue

SUITE = ["7H-1", "8H-1", "9H-1"]
BRELAN = ["9S-1", "9D-1", "9C-1"]


def partie(nb=2, graine=7, **options):
    return Rami().nouvelle_partie(valider(OPTIONS, options), nb, graine)


def retirer_ailleurs(etat, cartes):
    """Chaque carte n'existe qu'une fois : on l'ôte de la pioche, de la défausse et des mains."""
    for pile in [etat["pioche"], etat["defausse"], *etat["mains"]]:
        pile[:] = [c for c in pile if c not in cartes]


def etat_jouer(main, nb=2, **options):
    """Le joueur 0 a pioché et tient exactement `main`."""
    etat = partie(nb, **options)
    retirer_ailleurs(etat, main)
    etat["mains"][0] = list(main)
    etat["phase"] = "jouer"
    return etat


def etat_ouvert(main, **options):
    """Le joueur 0 a ouvert ; la table porte g1 = 7-8-9 de cœur et g2 = 4-joker-6 de pique."""
    etat = etat_jouer(main, **options)
    retirer_ailleurs(etat, SUITE + ["4S-1", "JK-1", "6S-1"])
    etat["ouvert"][0] = True
    etat["table"] = [
        {"id": "g1", "auteur": 0, "type": "suite", "cartes": SUITE, "jokers": {}},
        {
            "id": "g2", "auteur": 1, "type": "suite",
            "cartes": ["4S-1", "JK-1", "6S-1"], "jokers": {"JK-1": "5S"},
        },
    ]
    etat["prochain_groupe"] = 3
    return etat


def ids(actions):
    return [a["id"] for a in actions]


class RegistreTests(SimpleTestCase):
    def test_inscrit_au_registre(self):
        jeu = registre.obtenir("rami")
        self.assertIsInstance(jeu, Rami)
        self.assertEqual(
            (jeu.code, jeu.nom, jeu.min_joueurs, jeu.max_joueurs), ("rami", "Rami 51", 2, 6)
        )

    def test_adversaire_pas_encore_branche(self):
        with self.assertRaises(NotImplementedError):
            Rami().adversaire(partie(), 0)


class ActionsTests(SimpleTestCase):
    def test_actions_par_phase(self):
        rami = Rami()
        e = partie()
        self.assertEqual(ids(rami.actions_permises(e, 0)), ["piocher", "prendre_defausse"])
        self.assertEqual(rami.actions_permises(e, 1), [])

        e = etat_jouer(SUITE + BRELAN + ["2S-2"])
        self.assertEqual(ids(rami.actions_permises(e, 0)), ["poser", "defausser"])
        e, _ = rami.appliquer(e, 0, {"action": "poser", "cartes": SUITE})
        self.assertEqual(
            ids(rami.actions_permises(e, 0)),
            ["poser", "defausser", "valider_ouverture", "annuler"],
        )

        e = etat_ouvert(["2S-2", "5S-1"])
        self.assertEqual(
            ids(rami.actions_permises(e, 0)), ["poser", "defausser", "ajouter", "recuperer_joker"]
        )
        e = etat_ouvert(["2S-2"], recuperation_joker="jamais")
        self.assertEqual(ids(rami.actions_permises(e, 0)), ["poser", "defausser", "ajouter"])

        e["phase"] = "fin_manche"
        e["actif"] = 0
        self.assertEqual(ids(rami.actions_permises(e, 0)), ["manche_suivante"])
        e["phase"] = "terminee"
        self.assertEqual(rami.actions_permises(e, 0), [])

    def test_descripteurs(self):
        e = etat_ouvert(["2S-2", "5S-1"])
        par_id = {a["id"]: a for a in Rami().actions_permises(e, 0)}
        self.assertEqual(
            par_id["poser"],
            {"id": "poser", "libelle": "Poser la combinaison", "cartes_min": 3,
             "cartes_max": 13, "cible": None},
        )
        self.assertEqual(
            par_id["ajouter"],
            {"id": "ajouter", "libelle": "Ajouter à la combinaison", "cartes_min": 1,
             "cartes_max": 12, "cible": "groupe"},
        )
        self.assertEqual(par_id["recuperer_joker"]["cible"], "groupe")
        self.assertEqual(par_id["defausser"]["libelle"], "Défausser")

    def test_joueur_actif(self):
        rami = Rami()
        e = partie(nb=3)
        self.assertEqual(rami.joueur_actif(e), 0)
        e["actif"] = 2
        self.assertEqual(rami.joueur_actif(e), 2)
        e["phase"] = "terminee"
        self.assertIsNone(rami.joueur_actif(e))


class AppliquerTests(SimpleTestCase):
    def test_appliquer_ne_modifie_pas_l_etat(self):
        rami = Rami()
        e = partie()
        avant = copy.deepcopy(e)
        nouveau, message = rami.appliquer(e, 0, {"action": "piocher"})
        self.assertEqual(e, avant)
        self.assertEqual(nouveau["phase"], "jouer")
        self.assertEqual(message, "Tu pioches.")

        e = etat_jouer(SUITE + BRELAN + ["2S-2"])
        e, _ = rami.appliquer(e, 0, {"action": "poser", "cartes": SUITE})
        avant = copy.deepcopy(e)
        nouveau, _ = rami.appliquer(e, 0, {"action": "defausser", "cartes": ["2S-2"]})
        self.assertEqual(e, avant)
        self.assertEqual(nouveau["actif"], 1)

    def test_coups_malformes_refuses(self):
        rami = Rami()
        e = etat_ouvert(["2S-2", "5S-1", "10H-1"])
        autre = e["mains"][1][0]
        coups = [
            ({"action": "voler"}, "Action impossible maintenant."),
            ({"action": "piocher"}, "Action impossible maintenant."),
            ({"action": "defausser", "cartes": [autre]}, "Cette carte n'est pas dans ta main."),
            ({"action": "defausser", "cartes": ["ZZ-9"]}, "Carte inconnue."),
            ({"action": "ajouter", "cartes": ["10H-1"], "cible": "g99"},
             "Combinaison introuvable."),
            ({"action": "ajouter", "cartes": ["10H-1"]}, "Combinaison introuvable."),
            ({"action": "defausser", "cartes": ["2S-2", "5S-1"]}, "Choisis 1 carte."),
            ({"action": "poser", "cartes": ["2S-2"]}, "Choisis de 3 à 13 cartes."),
            ("pas un objet", "Coup mal formé."),
        ]
        for coup, message in coups:
            with self.subTest(coup=coup):
                avant = copy.deepcopy(e)
                with self.assertRaisesMessage(CoupRefuse, message):
                    rami.appliquer(e, 0, coup)
                self.assertEqual(e, avant)

    def test_pas_son_tour(self):
        with self.assertRaisesMessage(CoupRefuse, "Action impossible maintenant."):
            Rami().appliquer(partie(), 1, {"action": "piocher"})

    def test_dispatch(self):
        rami = Rami()
        e = etat_ouvert(["10H-1", "5S-1", "2S-2"])
        e, message = rami.appliquer(e, 0, {"action": "ajouter", "cartes": ["10H-1"], "cible": "g1"})
        self.assertEqual(e["table"][0]["cartes"], SUITE + ["10H-1"])
        self.assertEqual(message, "Tu complètes une suite.")
        # Le 5S remplace le joker de g2 ; le joker peut être rejoué sur g1 (J de cœur).
        e, _ = rami.appliquer(e, 0, {"action": "recuperer_joker", "cartes": ["5S-1"], "cible": "g2"})
        self.assertIn("JK-1", e["mains"][0])
        self.assertEqual(e["joker_recupere"], "JK-1")

    def test_defausse_annule_le_brouillon(self):
        rami = Rami()
        e = etat_jouer(SUITE + ["2S-2", "3D-1"])
        e, _ = rami.appliquer(e, 0, {"action": "poser", "cartes": SUITE})
        e, _ = rami.appliquer(e, 0, {"action": "defausser", "cartes": ["2S-2"]})
        self.assertEqual(e["brouillon"], [])
        self.assertEqual(sorted(e["mains"][0]), sorted(SUITE + ["3D-1"]))
        self.assertEqual(e["defausse"][-1], "2S-2")

    def test_defausse_refusee_avec_le_joker_recupere(self):
        rami = Rami()
        e = etat_ouvert(["5S-1", "2S-2", "3D-1"])
        e, _ = rami.appliquer(e, 0, {"action": "recuperer_joker", "cartes": ["5S-1"], "cible": "g2"})
        for carte in ("2S-2", "JK-1"):
            with self.assertRaisesMessage(CoupRefuse, "Utilise d'abord le joker récupéré."):
                rami.appliquer(e, 0, {"action": "defausser", "cartes": [carte]})
        e, _ = rami.appliquer(e, 0, {"action": "ajouter", "cartes": ["JK-1"], "cible": "g1"})
        e, _ = rami.appliquer(e, 0, {"action": "defausser", "cartes": ["2S-2"]})
        self.assertEqual(e["actif"], 1)

    def test_defausse_a_poser(self):
        rami = Rami()
        e = partie(defausse_a_poser=True)
        e["defausse"] = ["2S-2"]
        e, _ = rami.appliquer(e, 0, {"action": "prendre_defausse"})
        with self.assertRaisesMessage(CoupRefuse, "Pose d'abord la carte prise à la défausse."):
            rami.appliquer(e, 0, {"action": "defausser", "cartes": [e["mains"][0][0]]})

        e = partie()
        e["defausse"] = ["2S-2"]
        e, _ = rami.appliquer(e, 0, {"action": "prendre_defausse"})
        e, _ = rami.appliquer(e, 0, {"action": "defausser", "cartes": [e["mains"][0][0]]})
        self.assertEqual(e["actif"], 1)

    def test_rendre_defausse_debloque(self):
        rami = Rami()
        e = partie(defausse_a_poser=True)
        retirer_ailleurs(e, ["2S-2"])
        e["defausse"] = ["5D-1", "2S-2"]
        e, _ = rami.appliquer(e, 0, {"action": "prendre_defausse"})
        self.assertIn("rendre_defausse", ids(rami.actions_permises(e, 0)))
        avant = len(e["mains"][0])
        e, message = rami.appliquer(e, 0, {"action": "rendre_defausse"})
        self.assertEqual(message, "Tu reposes le 2♠ sur la défausse.")
        self.assertEqual((e["phase"], e["prise"], e["defausse"]), ("piocher", None, ["5D-1", "2S-2"]))
        self.assertEqual(len(e["mains"][0]), avant - 1)
        self.assertEqual(ids(rami.actions_permises(e, 0)), ["piocher"])
        valider_vue(rami.vue(e, 0))
        with self.assertRaisesMessage(CoupRefuse, "Action impossible maintenant."):
            rami.appliquer(e, 0, {"action": "prendre_defausse"})
        # Le tour suivant, la défausse peut de nouveau être prise.
        e, _ = rami.appliquer(e, 0, {"action": "piocher"})
        self.assertNotIn("rendre_defausse", ids(rami.actions_permises(e, 0)))
        e, _ = rami.appliquer(e, 0, {"action": "defausser", "cartes": [e["mains"][0][0]]})
        self.assertEqual(ids(rami.actions_permises(e, 1)), ["piocher", "prendre_defausse"])

    def test_rendre_defausse_annule_le_brouillon(self):
        rami = Rami()
        e = partie(defausse_a_poser=True)
        retirer_ailleurs(e, SUITE + ["3D-1"])
        e["mains"][0] = ["7H-1", "8H-1", "3D-1"]
        e["defausse"] = ["9H-1"]
        e, _ = rami.appliquer(e, 0, {"action": "prendre_defausse"})
        e, _ = rami.appliquer(e, 0, {"action": "poser", "cartes": SUITE})
        self.assertIn("rendre_defausse", ids(rami.actions_permises(e, 0)))
        e, _ = rami.appliquer(e, 0, {"action": "rendre_defausse"})
        self.assertEqual(e["brouillon"], [])
        self.assertEqual(sorted(e["mains"][0]), ["3D-1", "7H-1", "8H-1"])
        self.assertEqual(e["defausse"], ["9H-1"])

    def test_rendre_defausse_seulement_avec_l_option(self):
        rami = Rami()
        e = partie()
        e, _ = rami.appliquer(e, 0, {"action": "prendre_defausse"})
        self.assertNotIn("rendre_defausse", ids(rami.actions_permises(e, 0)))

    def test_prendre_defausse_vide_impossible(self):
        e = partie()
        e["defausse"] = []
        self.assertEqual(ids(Rami().actions_permises(e, 0)), ["piocher"])

    def test_manche_suivante(self):
        rami = Rami()
        e = partie(manches=2)
        e["pioche"] = []
        e["reconstitutions"] = 3
        e, message = rami.appliquer(e, 0, {"action": "piocher"})
        self.assertEqual(e["phase"], "fin_manche")
        self.assertIn("épuisée", message)
        e, message = rami.appliquer(e, 0, {"action": "manche_suivante"})
        self.assertEqual((e["manche"], e["phase"], e["actif"]), (2, "piocher", 1))
        self.assertEqual(message, "La manche 2 commence.")
