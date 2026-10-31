import copy
import json

from django.test import SimpleTestCase

from huit.jeu import Huit
from huit.manche import points, retourner
from huit.tests.outils import ids, paquet_complet, partie, table, toutes_les_cartes
from tapis import registre
from tapis.cartes import est_joker, valeur
from tapis.jeu import CoupRefuse


def jouer(carte):
    return {"action": "jouer", "cartes": [carte]}


PIOCHER = {"action": "piocher"}
PASSER = {"action": "passer"}


class RegistreTests(SimpleTestCase):
    def test_inscrit_au_registre(self):
        jeu = registre.obtenir("huit")
        self.assertIsInstance(jeu, Huit)
        self.assertEqual(
            (jeu.code, jeu.nom, jeu.min_joueurs, jeu.max_joueurs), ("huit", "8 américain", 2, 6)
        )

    def test_options(self):
        self.assertEqual(
            Huit().decrire()["options"],
            [
                {"code": "cartes_speciales", "libelle": "Cartes spéciales (2, valet, as)",
                 "type": "booleen", "defaut": True},
                {"code": "jokers", "libelle": "Jokers (+4, sur tout)", "type": "booleen",
                 "defaut": False},
                {"code": "manches", "libelle": "Nombre de manches", "type": "entier",
                 "defaut": 3, "minimum": 1, "maximum": 10},
            ],
        )

    def test_nombre_de_joueurs_invalide(self):
        for nb in (1, 7):
            with self.assertRaises(ValueError):
                partie(nb=nb)


class DistributionTests(SimpleTestCase):
    def test_mains_et_paquets(self):
        for nb, main, cartes in [(2, 8, 52), (3, 8, 52), (4, 8, 52), (5, 7, 104), (6, 7, 104)]:
            for jokers in (False, True):
                with self.subTest(nb=nb, jokers=jokers):
                    e = partie(nb=nb, jokers=jokers)
                    self.assertEqual([len(m) for m in e["mains"]], [main] * nb)
                    self.assertEqual(len(e["defausse"]), 1)
                    total = toutes_les_cartes(e)
                    self.assertEqual(total, paquet_complet(e))
                    nb_jokers = sum(n for c, n in total.items() if est_joker(c))
                    self.assertEqual(nb_jokers, (cartes // 52) * 2 if jokers else 0)
                    self.assertEqual(sum(total.values()), cartes + nb_jokers)

    def test_premiere_carte_ni_huit_ni_joker(self):
        for graine in range(1, 60):
            e = partie(nb=2 + graine % 5, graine=graine, jokers=True)
            dessus = e["defausse"][-1]
            self.assertFalse(est_joker(dessus) or valeur(dessus) == "8", graine)
            self.assertEqual(e["reference"], dessus)

    def test_un_huit_retourne_va_au_milieu_de_la_pioche(self):
        pioche = ["2S-1", "3S-1", "4S-1", "5S-1", "8H-1"]
        self.assertEqual(retourner(pioche), "5S-1")
        self.assertEqual(pioche, ["2S-1", "3S-1", "8H-1", "4S-1"])
        pioche = ["2S-1", "3S-1", "4S-1", "JK-1", "8H-1"]
        self.assertEqual(retourner(pioche), "4S-1")
        self.assertNotIn("4S-1", pioche)
        self.assertEqual(sorted(pioche), ["2S-1", "3S-1", "8H-1", "JK-1"])

    def test_le_joueur_a_gauche_du_donneur_commence(self):
        jeu = Huit()
        e = partie(nb=3, manches=3)
        self.assertEqual((e["actif"], e["sens"]), (0, 1))
        for attendu in (1, 2):
            e["phase"] = "fin_manche"
            e["actif"] = 0
            e["sens"] = -1
            e, message = jeu.appliquer(e, 0, {"action": "manche_suivante"})
            self.assertEqual(message, f"La manche {attendu + 1} commence.")
            self.assertEqual((e["actif"], e["sens"], e["phase"]), (attendu, 1, "jouer"))
            self.assertEqual(toutes_les_cartes(e), paquet_complet(e))

    def test_graine_de_128_bits(self):
        graine = (1 << 128) - 1
        e = partie(graine=graine)
        self.assertEqual(json.loads(json.dumps(e)), e)
        self.assertEqual(partie(graine=graine), e)
        self.assertNotEqual(partie(graine=graine - 1)["mains"], e["mains"])


class JouerTests(SimpleTestCase):
    def test_meme_couleur_ou_meme_valeur(self):
        jeu = Huit()
        e = table(partie(), {0: ["3H-1", "7S-1", "KD-1"]}, "7H-1")
        e1, message = jeu.appliquer(e, 0, jouer("3H-1"))
        self.assertEqual(message, "Tu joues le 3♥.")
        self.assertEqual((e1["defausse"][-1], e1["reference"], e1["actif"]), ("3H-1", "3H-1", 1))
        self.assertEqual(e1["mains"][0], ["7S-1", "KD-1"])
        e1, _ = jeu.appliquer(e, 0, jouer("7S-1"))
        self.assertEqual(e1["reference"], "7S-1")
        with self.assertRaisesMessage(CoupRefuse, "Le K♦ ne se joue pas sur le 7♥."):
            jeu.appliquer(e, 0, jouer("KD-1"))

    def test_message_de_l_ordinateur(self):
        e = table(partie(), {1: ["3H-1", "9C-1"]}, "7H-1", actif=1)
        _, message = Huit().appliquer(e, 1, jouer("3H-1"))
        self.assertEqual(message, "Ordinateur 1 joue le 3♥.")

    def test_huit_puis_couleur_par_le_meme_joueur(self):
        jeu = Huit()
        e = table(partie(nb=3), {0: ["8S-1", "KD-1", "2C-1"]}, "7H-1")
        e, message = jeu.appliquer(e, 0, jouer("8S-1"))
        self.assertEqual(message, "Tu joues le 8♠. Choisis une couleur.")
        self.assertEqual((e["phase"], e["actif"]), ("couleur", 0))
        self.assertEqual(
            ids(jeu.actions_permises(e, 0)), ["couleur_S", "couleur_H", "couleur_D", "couleur_C"]
        )
        self.assertEqual(jeu.actions_permises(e, 1), [])
        with self.assertRaisesMessage(CoupRefuse, "Annonce d'abord une couleur."):
            jeu.appliquer(e, 0, jouer("KD-1"))
        with self.assertRaisesMessage(CoupRefuse, "Annonce d'abord une couleur."):
            jeu.appliquer(e, 0, PIOCHER)
        e, message = jeu.appliquer(e, 0, {"action": "couleur_D"})
        self.assertEqual(message, "Tu annonces Carreau.")
        self.assertEqual((e["phase"], e["actif"], e["couleur"]), ("jouer", 1, "D"))

    def test_la_couleur_annoncee_s_impose(self):
        jeu = Huit()
        e = table(partie(nb=3), {1: ["4H-1", "7S-1", "QD-1", "8C-1"]}, ["6S-1", "8S-1"], actif=1)
        e["reference"], e["couleur"] = "8S-1", "D"
        with self.assertRaisesMessage(CoupRefuse, "La couleur demandée est Carreau."):
            jeu.appliquer(e, 1, jouer("7S-1"))
        e1, _ = jeu.appliquer(e, 1, jouer("QD-1"))
        self.assertIsNone(e1["couleur"])
        self.assertEqual(e1["reference"], "QD-1")
        # Un 8 se pose aussi sur une couleur annoncée.
        e1, message = jeu.appliquer(e, 1, jouer("8C-1"))
        self.assertEqual(message, "Ordinateur 1 joue le 8♣. Ordinateur 1 choisit une couleur.")
        self.assertEqual(e1["phase"], "couleur")
        e1, message = jeu.appliquer(e1, 1, {"action": "couleur_S"})
        self.assertEqual(message, "Ordinateur 1 annonce Pique.")
        self.assertEqual((e1["couleur"], e1["actif"]), ("S", 2))

    def test_coups_mal_formes(self):
        jeu = Huit()
        e = table(partie(), {0: ["3H-1", "4H-1"]}, "7H-1")
        cas = [
            ({"action": "jouer", "cartes": []}, "Choisis 1 carte."),
            ({"action": "jouer", "cartes": ["3H-1", "4H-1"]}, "Choisis 1 carte."),
            ({"action": "jouer", "cartes": ["ZZ-1"]}, "Carte inconnue."),
            ({"action": "jouer", "cartes": ["5H-1"]}, "Cette carte n'est pas dans ta main."),
            ({"action": "piocher", "cartes": ["3H-1"]}, "Cette action ne prend pas de carte."),
            ({"action": "voler"}, "Action impossible maintenant."),
            ({"action": "manche_suivante"}, "Action impossible maintenant."),
            ({"action": "couleur_H"}, "Action impossible maintenant."),
            ({"cartes": []}, "Action manquante."),
            ("jouer", "Coup mal formé."),
        ]
        for coup, message in cas:
            with self.subTest(coup=coup), self.assertRaisesMessage(CoupRefuse, message):
                jeu.appliquer(e, 0, coup)

    def test_pas_son_tour(self):
        e = table(partie(), {1: ["3H-1"]}, "7H-1")
        with self.assertRaisesMessage(CoupRefuse, "Action impossible maintenant."):
            Huit().appliquer(e, 1, jouer("3H-1"))

    def test_appliquer_ne_modifie_pas_l_etat(self):
        jeu = Huit()
        e = partie(nb=3, jokers=True)
        avant = copy.deepcopy(e)
        j = jeu.joueur_actif(e)
        jeu.appliquer(e, j, PIOCHER)
        jeu.appliquer(e, j, jeu.adversaire(e, j))
        self.assertEqual(e, avant)

    def test_joueur_actif(self):
        jeu = Huit()
        e = partie(nb=3)
        self.assertEqual(jeu.joueur_actif(e), 0)
        e["actif"] = 2
        self.assertEqual(jeu.joueur_actif(e), 2)
        e["phase"] = "terminee"
        self.assertIsNone(jeu.joueur_actif(e))


class PiocheTests(SimpleTestCase):
    def test_piocher_puis_jouer_la_carte_piochee(self):
        jeu = Huit()
        e = table(partie(nb=3), {0: ["3H-1", "KD-1"]}, "7H-1")
        e["pioche"].append("9H-1")
        e, message = jeu.appliquer(e, 0, PIOCHER)
        self.assertEqual(message, "Tu pioches.")
        self.assertEqual((e["piochee"], e["actif"]), ("9H-1", 0))
        self.assertEqual(e["mains"][0], ["3H-1", "KD-1", "9H-1"])
        self.assertEqual(ids(jeu.actions_permises(e, 0)), ["jouer", "passer"])
        # Seule la carte piochée peut être jouée, même si une autre convient.
        with self.assertRaisesMessage(CoupRefuse, "Tu ne peux jouer que la carte piochée."):
            jeu.appliquer(e, 0, jouer("3H-1"))
        with self.assertRaisesMessage(CoupRefuse, "Tu as déjà pioché."):
            jeu.appliquer(e, 0, PIOCHER)
        e, _ = jeu.appliquer(e, 0, jouer("9H-1"))
        self.assertEqual((e["piochee"], e["actif"], e["defausse"][-1]), (None, 1, "9H-1"))

    def test_piocher_puis_passer(self):
        jeu = Huit()
        e = table(partie(nb=3), {0: ["3H-1"]}, "7H-1")
        e["pioche"].append("KD-1")
        e, _ = jeu.appliquer(e, 0, PIOCHER)
        with self.assertRaisesMessage(CoupRefuse, "Le K♦ ne se joue pas sur le 7♥."):
            jeu.appliquer(e, 0, jouer("KD-1"))
        e, message = jeu.appliquer(e, 0, PASSER)
        self.assertEqual(message, "Tu passes.")
        self.assertEqual((e["piochee"], e["actif"]), (None, 1))
        self.assertEqual(e["mains"][0], ["3H-1", "KD-1"])
        self.assertEqual(ids(jeu.actions_permises(e, 1)), ["jouer", "piocher"])

    def test_passer_sans_avoir_pioche(self):
        e = table(partie(), {0: ["3H-1"]}, "7H-1")
        with self.assertRaisesMessage(CoupRefuse, "Pioche d'abord une carte."):
            Huit().appliquer(e, 0, PASSER)

    def test_carte_piochee_jumelle(self):
        # À 5 joueurs, deux paquets : la carte piochée est 7H-1, pas sa jumelle 7H-2.
        jeu = Huit()
        e = table(partie(nb=5), {0: ["7H-2", "KD-1"]}, "7C-1")
        e["pioche"].append("7H-1")
        e, _ = jeu.appliquer(e, 0, PIOCHER)
        with self.assertRaisesMessage(CoupRefuse, "Tu ne peux jouer que la carte piochée."):
            jeu.appliquer(e, 0, jouer("7H-2"))
        e, _ = jeu.appliquer(e, 0, jouer("7H-1"))
        self.assertEqual(e["mains"][0], ["7H-2", "KD-1"])

    def test_huit_pioche_puis_joue(self):
        jeu = Huit()
        e = table(partie(nb=3), {0: ["3C-1"]}, "7H-1")
        e["pioche"].append("8D-1")
        e, _ = jeu.appliquer(e, 0, PIOCHER)
        e, _ = jeu.appliquer(e, 0, jouer("8D-1"))
        self.assertEqual((e["phase"], e["actif"], e["piochee"]), ("couleur", 0, None))

    def test_pioche_vide_on_remelange_la_defausse(self):
        jeu = Huit()
        e = table(partie(), {0: ["3C-1"]}, ["4S-1", "5S-1", "6S-1", "7H-1"])
        e["mains"][1] += e["pioche"]
        e["pioche"] = []
        e, message = jeu.appliquer(e, 0, PIOCHER)
        self.assertEqual(
            message, "La défausse est remélangée pour refaire la pioche. Tu pioches."
        )
        self.assertEqual(e["defausse"], ["7H-1"])
        self.assertEqual(len(e["pioche"]), 2)
        self.assertIn(e["piochee"], ["4S-1", "5S-1", "6S-1"])
        self.assertEqual(toutes_les_cartes(e), paquet_complet(e))

    def test_pioche_et_defausse_vides_on_passe(self):
        jeu = Huit()
        e = table(partie(nb=3), {0: ["3C-1"]}, "7H-1")
        e["mains"][1] += e["pioche"]
        e["pioche"] = []
        e, message = jeu.appliquer(e, 0, PIOCHER)
        self.assertEqual(message, "Il n'y a plus rien à piocher : tu passes.")
        self.assertEqual((e["actif"], e["piochee"], e["blocages"]), (1, None, 1))

    def test_tout_le_monde_bloque_la_manche_s_arrete(self):
        jeu = Huit()
        e = table(partie(nb=2, manches=2), {0: ["3C-1"], 1: ["KD-1"]}, "7H-1")
        e["mains"][1] += e["pioche"]
        e["pioche"] = []
        e, _ = jeu.appliquer(e, 0, PIOCHER)
        e, message = jeu.appliquer(e, 1, PIOCHER)
        self.assertEqual(
            message,
            "Il n'y a plus rien à piocher : Ordinateur 1 passe. "
            "Personne ne peut plus jouer : la manche est terminée.",
        )
        self.assertEqual(e["phase"], "fin_manche")
        self.assertEqual(e["scores"][0][0], 3)
        self.assertGreater(e["scores"][0][1], 0)

    def test_un_coup_joue_remet_les_blocages_a_zero(self):
        jeu = Huit()
        e = table(partie(nb=3), {0: ["3C-1"], 1: ["7C-1", "KD-1"]}, "7H-1")
        e["mains"][2] += e["pioche"]
        e["pioche"] = []
        e, _ = jeu.appliquer(e, 0, PIOCHER)
        e, _ = jeu.appliquer(e, 1, jouer("7C-1"))
        self.assertEqual(e["blocages"], 0)


class PenaliteTests(SimpleTestCase):
    def test_un_deux_fait_piocher_deux_cartes(self):
        jeu = Huit()
        e = table(partie(nb=3), {0: ["2H-1", "KD-1"], 1: ["5H-1", "9C-1"]}, "7H-1")
        e, message = jeu.appliquer(e, 0, jouer("2H-1"))
        self.assertEqual(message, "Tu joues le 2♥. Ordinateur 1 doit piocher 2 cartes.")
        self.assertEqual((e["actif"], e["penalite"], e["penalite_par"]), (1, 2, "2"))
        par_id = {a["id"]: a for a in jeu.actions_permises(e, 1)}
        self.assertEqual(list(par_id), ["jouer", "piocher"])
        self.assertEqual(par_id["piocher"]["libelle"], "Piocher 2")
        # Une carte de même couleur ne suffit pas.
        with self.assertRaisesMessage(
            CoupRefuse, "Une pénalité est en cours : pose un 2 ou pioche 2 cartes."
        ):
            jeu.appliquer(e, 1, jouer("5H-1"))
        n = len(e["pioche"])
        e, message = jeu.appliquer(e, 1, PIOCHER)
        self.assertEqual(message, "Ordinateur 1 pioche 2 cartes.")
        self.assertEqual(len(e["mains"][1]), 4)
        self.assertEqual(len(e["pioche"]), n - 2)
        # Il perd son tour : c'est au suivant, sans pénalité ni carte piochée en attente.
        self.assertEqual((e["actif"], e["penalite"], e["penalite_par"], e["piochee"]),
                         (2, 0, None, None))
        self.assertEqual(ids(jeu.actions_permises(e, 2)), ["jouer", "piocher"])

    def test_les_deux_se_cumulent(self):
        jeu = Huit()
        e = table(
            partie(nb=3),
            {0: ["2H-1", "KD-1"], 1: ["2S-1", "9C-1"], 2: ["2C-1", "4D-1"]},
            "7H-1",
        )
        e, _ = jeu.appliquer(e, 0, jouer("2H-1"))
        # Un 2 de n'importe quelle couleur contre.
        e, message = jeu.appliquer(e, 1, jouer("2S-1"))
        self.assertEqual(message, "Ordinateur 1 joue le 2♠. Ordinateur 2 doit piocher 4 cartes.")
        self.assertEqual((e["actif"], e["penalite"]), (2, 4))
        e, message = jeu.appliquer(e, 2, jouer("2C-1"))
        self.assertEqual(message, "Ordinateur 2 joue le 2♣. Tu dois piocher 6 cartes.")
        self.assertEqual((e["actif"], e["penalite"]), (0, 6))
        self.assertEqual(jeu.actions_permises(e, 0)[1]["libelle"], "Piocher 6")
        e, message = jeu.appliquer(e, 0, PIOCHER)
        self.assertEqual(message, "Tu pioches 6 cartes.")
        self.assertEqual(len(e["mains"][0]), 7)
        self.assertEqual((e["actif"], e["penalite"]), (1, 0))
        self.assertEqual(e["reference"], "2C-1")

    def test_pas_de_huit_ni_de_joker_sous_une_penalite_de_deux(self):
        jeu = Huit()
        e = table(partie(nb=3, jokers=True), {0: ["2H-1", "KD-1"], 1: ["8S-1", "JK-1"]}, "7H-1")
        e, _ = jeu.appliquer(e, 0, jouer("2H-1"))
        for carte in ("8S-1", "JK-1"):
            with self.assertRaisesMessage(
                CoupRefuse, "Une pénalité est en cours : pose un 2 ou pioche 2 cartes."
            ):
                jeu.appliquer(e, 1, jouer(carte))

    def test_la_penalite_suit_le_sens_du_jeu(self):
        jeu = Huit()
        e = table(partie(nb=3), {0: ["2H-1", "KD-1"], 2: ["2S-1", "9C-1"]}, "7H-1")
        e["sens"] = -1
        e, message = jeu.appliquer(e, 0, jouer("2H-1"))
        self.assertEqual(e["actif"], 2)
        e, _ = jeu.appliquer(e, 2, jouer("2S-1"))
        self.assertEqual((e["actif"], e["penalite"]), (1, 4))
        e, _ = jeu.appliquer(e, 1, PIOCHER)
        self.assertEqual(e["actif"], 0)

    def test_penalite_plus_grande_que_la_pioche(self):
        jeu = Huit()
        e = table(partie(nb=2), {0: ["2H-1", "KD-1"], 1: ["9C-1"]},
                  ["4S-1", "5S-1", "7H-1"])
        reste = e["pioche"]
        e["mains"][1] += reste[1:]
        e["pioche"] = reste[:1]
        # 1 carte dans la pioche, 3 sous le 2 dans la défausse une fois le 2 posé.
        e, _ = jeu.appliquer(e, 0, jouer("2H-1"))
        e["penalite"] = 6
        avant = len(e["mains"][1])
        e, message = jeu.appliquer(e, 1, PIOCHER)
        self.assertEqual(
            message,
            "La défausse est remélangée pour refaire la pioche. "
            "Ordinateur 1 pioche 4 cartes : il n'y en a pas plus.",
        )
        self.assertEqual(len(e["mains"][1]), avant + 4)
        self.assertEqual((e["pioche"], e["defausse"]), ([], ["2H-1"]))
        self.assertEqual((e["actif"], e["penalite"]), (0, 0))
        self.assertEqual(toutes_les_cartes(e), paquet_complet(e))

    def test_penalite_sans_rien_a_piocher(self):
        jeu = Huit()
        e = table(partie(nb=3), {0: ["2H-1", "KD-1"], 1: ["9C-1"]}, "7H-1")
        e["mains"][2] += e["pioche"]
        e["pioche"] = []
        e, _ = jeu.appliquer(e, 0, jouer("2H-1"))
        e["mains"][2] += e["defausse"][:-1]  # rien à remélanger sous le 2
        e["defausse"] = ["2H-1"]
        e, message = jeu.appliquer(e, 1, PIOCHER)
        self.assertEqual(message, "Il n'y a plus rien à piocher : Ordinateur 1 passe.")
        self.assertEqual((e["actif"], e["penalite"], e["blocages"]), (2, 0, 1))

    def test_un_deux_en_derniere_carte_ne_fait_pas_piocher(self):
        jeu = Huit()
        e = table(partie(nb=3, manches=2), {0: ["2H-1"], 1: ["9C-1", "KD-1"]}, "7H-1")
        e, message = jeu.appliquer(e, 0, jouer("2H-1"))
        self.assertEqual(
            message, "Tu joues le 2♥. Tu n'as plus de carte : la manche est terminée."
        )
        self.assertEqual((e["phase"], e["penalite"]), ("fin_manche", 0))
        self.assertEqual(e["scores"][0][:2], [0, 19])

    def test_un_deux_qui_contre_en_derniere_carte_annule_la_penalite(self):
        jeu = Huit()
        e = table(partie(nb=3, manches=2), {0: ["2H-1", "KD-1"], 1: ["2S-1"]}, "7H-1")
        e, _ = jeu.appliquer(e, 0, jouer("2H-1"))
        e, _ = jeu.appliquer(e, 1, jouer("2S-1"))
        self.assertEqual((e["phase"], e["penalite"], e["penalite_par"]), ("fin_manche", 0, None))
        self.assertEqual(e["scores"][0][1], 0)


class JokerTests(SimpleTestCase):
    def test_joker_sur_tout_sans_annonce_et_plus_quatre(self):
        jeu = Huit()
        e = table(partie(nb=3, jokers=True), {0: ["JK-1", "KD-1"], 1: ["5H-1", "2H-1"]}, "7H-1")
        e, message = jeu.appliquer(e, 0, jouer("JK-1"))
        self.assertEqual(message, "Tu joues le joker. Ordinateur 1 doit piocher 4 cartes.")
        self.assertEqual((e["phase"], e["actif"]), ("jouer", 1))
        self.assertEqual((e["penalite"], e["penalite_par"], e["reference"]), (4, "joker", "7H-1"))
        self.assertEqual(jeu.actions_permises(e, 1)[1]["libelle"], "Piocher 4")
        # Un 2 ne contre pas un joker.
        with self.assertRaisesMessage(
            CoupRefuse, "Une pénalité est en cours : pose un joker ou pioche 4 cartes."
        ):
            jeu.appliquer(e, 1, jouer("2H-1"))
        e, _ = jeu.appliquer(e, 1, PIOCHER)
        self.assertEqual((len(e["mains"][1]), e["actif"]), (6, 2))

    def test_la_carte_sous_le_joker_reste_la_reference(self):
        jeu = Huit()
        e = table(partie(nb=3, jokers=True), {2: ["5H-1", "7C-1", "KD-1"]}, ["7H-1", "JK-1"],
                  actif=2)
        with self.assertRaisesMessage(CoupRefuse, "Le K♦ ne se joue pas sur le 7♥."):
            jeu.appliquer(e, 2, jouer("KD-1"))
        jeu.appliquer(e, 2, jouer("5H-1"))
        jeu.appliquer(e, 2, jouer("7C-1"))

    def test_le_joker_garde_la_couleur_annoncee(self):
        jeu = Huit()
        e = table(partie(nb=3, jokers=True), {0: ["JK-1", "KD-1"]}, ["7H-1", "8S-1"])
        e["reference"], e["couleur"] = "8S-1", "C"
        e, _ = jeu.appliquer(e, 0, jouer("JK-1"))
        self.assertEqual((e["couleur"], e["reference"]), ("C", "8S-1"))

    def test_les_jokers_se_cumulent(self):
        jeu = Huit()
        e = table(
            partie(nb=3, jokers=True),
            {0: ["JK-1", "KD-1"], 1: ["JK-2", "3C-1"], 2: ["9S-1"]},
            "7H-1",
        )
        e, _ = jeu.appliquer(e, 0, jouer("JK-1"))
        e, message = jeu.appliquer(e, 1, jouer("JK-2"))
        self.assertEqual(message, "Ordinateur 1 joue le joker. Ordinateur 2 doit piocher 8 cartes.")
        self.assertEqual((e["actif"], e["penalite"]), (2, 8))
        e, message = jeu.appliquer(e, 2, PIOCHER)
        self.assertEqual(message, "Ordinateur 2 pioche 8 cartes.")
        self.assertEqual((len(e["mains"][2]), e["actif"]), (9, 0))
        self.assertEqual(e["reference"], "7H-1")

    def test_joker_sans_cartes_speciales(self):
        jeu = Huit()
        e = table(partie(nb=2, jokers=True, cartes_speciales=False), {0: ["JK-1", "KD-1"]},
                  "7H-1")
        e, _ = jeu.appliquer(e, 0, jouer("JK-1"))
        self.assertEqual((e["penalite"], e["actif"]), (4, 1))

    def test_joker_en_derniere_carte(self):
        jeu = Huit()
        e = table(partie(nb=2, jokers=True, manches=1), {0: ["JK-1"], 1: ["JK-2"]}, "7H-1")
        e, _ = jeu.appliquer(e, 0, jouer("JK-1"))
        self.assertEqual((e["phase"], e["penalite"]), ("terminee", 0))
        self.assertEqual(e["scores"], [[0, 50]])


class CartesSpecialesTests(SimpleTestCase):
    def test_valet_fait_passer_le_suivant(self):
        jeu = Huit()
        e = table(partie(nb=3), {0: ["JH-1", "KD-1"]}, "7H-1")
        e, message = jeu.appliquer(e, 0, jouer("JH-1"))
        self.assertEqual(message, "Tu joues le J♥. Ordinateur 1 passe son tour.")
        self.assertEqual(e["actif"], 2)
        e = table(partie(nb=3), {2: ["JH-1", "KD-1"]}, "7H-1", actif=2)
        e, message = jeu.appliquer(e, 2, jouer("JH-1"))
        self.assertEqual(message, "Ordinateur 2 joue le J♥. Tu passes ton tour.")
        self.assertEqual(e["actif"], 1)

    def test_valet_a_deux_joueurs_on_rejoue(self):
        e = table(partie(nb=2), {0: ["JH-1", "KD-1"]}, "7H-1")
        e, _ = Huit().appliquer(e, 0, jouer("JH-1"))
        self.assertEqual(e["actif"], 0)
        self.assertEqual(ids(Huit().actions_permises(e, 0)), ["jouer", "piocher"])

    def test_as_inverse_le_sens(self):
        jeu = Huit()
        e = table(partie(nb=4), {0: ["AH-1", "KD-1"], 3: ["AD-1", "4C-1"]}, "7H-1")
        e, message = jeu.appliquer(e, 0, jouer("AH-1"))
        self.assertEqual(message, "Tu joues le A♥. Le sens du jeu s'inverse.")
        self.assertEqual((e["sens"], e["actif"]), (-1, 3))
        e, _ = jeu.appliquer(e, 3, jouer("AD-1"))
        self.assertEqual((e["sens"], e["actif"]), (1, 0))

    def test_as_a_deux_joueurs_vaut_un_valet(self):
        e = table(partie(nb=2), {0: ["AH-1", "KD-1"]}, "7H-1")
        e, message = Huit().appliquer(e, 0, jouer("AH-1"))
        self.assertEqual(message, "Tu joues le A♥. Ordinateur 1 passe son tour.")
        self.assertEqual((e["sens"], e["actif"]), (1, 0))

    def test_sans_cartes_speciales(self):
        jeu = Huit()
        for carte in ("2H-1", "JH-1", "AH-1"):
            with self.subTest(carte=carte):
                e = table(partie(nb=3, cartes_speciales=False), {0: [carte, "KD-1"]}, "7H-1")
                e, message = jeu.appliquer(e, 0, jouer(carte))
                self.assertEqual(message, f"Tu joues le {carte[0]}♥.")
                self.assertEqual((e["actif"], e["sens"], e["penalite"]), (1, 1, 0))

    def test_huit_en_derniere_carte_sans_annonce(self):
        jeu = Huit()
        e = table(partie(nb=2, manches=2), {0: ["8S-1"], 1: ["8H-1", "KD-1", "AC-1", "5S-1"]},
                  "7H-1")
        e, message = jeu.appliquer(e, 0, jouer("8S-1"))
        self.assertEqual(message, "Tu joues le 8♠. Tu n'as plus de carte : la manche est terminée.")
        self.assertEqual((e["phase"], e["actif"]), ("fin_manche", 0))
        self.assertEqual(e["scores"], [[0, 66]])

    def test_valet_ou_as_en_derniere_carte(self):
        jeu = Huit()
        for carte in ("JH-1", "AH-1"):
            e = table(partie(nb=3, manches=2), {1: [carte]}, "7H-1", actif=1)
            e, message = jeu.appliquer(e, 1, jouer(carte))
            self.assertEqual(
                message,
                f"Ordinateur 1 joue le {carte[0]}♥. Ordinateur 1 n'a plus de carte : "
                "la manche est terminée.",
            )
            self.assertEqual((e["phase"], e["sens"]), ("fin_manche", 1))


class MancheTests(SimpleTestCase):
    def test_points(self):
        self.assertEqual(
            [points(c) for c in ["8S-1", "KH-1", "QD-2", "JC-1", "AS-1", "10H-1", "2D-1", "JK-3"]],
            [50, 10, 10, 10, 1, 10, 2, 50],
        )

    def test_fin_de_manche_et_de_partie(self):
        jeu = Huit()
        e = table(partie(nb=3, manches=2), {1: ["3H-1"], 0: ["KD-1"], 2: ["8C-1", "4C-1"]},
                  "7H-1", actif=1)
        e, _ = jeu.appliquer(e, 1, jouer("3H-1"))
        self.assertEqual((e["phase"], e["actif"], e["scores"]), ("fin_manche", 0, [[10, 0, 54]]))
        self.assertEqual(ids(jeu.actions_permises(e, 0)), ["manche_suivante"])
        self.assertEqual(jeu.actions_permises(e, 1), [])
        e, _ = jeu.appliquer(e, 0, {"action": "manche_suivante"})
        self.assertEqual((e["manche"], e["actif"], e["phase"]), (2, 1, "jouer"))
        e = table(e, {1: ["3H-1"]}, "7H-1", actif=1)
        e, _ = jeu.appliquer(e, 1, jouer("3H-1"))
        self.assertEqual(e["phase"], "terminee")
        self.assertEqual(len(e["scores"]), 2)
        self.assertIsNone(jeu.joueur_actif(e))
        self.assertEqual(jeu.actions_permises(e, 0), [])
