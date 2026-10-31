import copy
import json

from django.test import SimpleTestCase

from dame.jeu import Dame
from dame.options import OPTIONS
from tapis import registre
from tapis.cartes import enseigne
from tapis.jeu import CoupRefuse
from tapis.options import valider

COEURS = [f"{v}H-1" for v in ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]]


def partie(nb=4, graine=7, **options):
    return Dame().nouvelle_partie(valider(OPTIONS, options), nb, graine)


def etat_plis(mains, actif=0, plis_joues=1, **options):
    """Phase des plis avec exactement ces mains ; par défaut après le premier pli, cœurs fermés."""
    e = partie(nb=len(mains), echange=False, **options)
    e["mains"] = [list(m) for m in mains]
    e["actif"] = actif
    e["plis_joues"] = plis_joues
    return e


def jouer(e, j, carte):
    return Dame().appliquer(e, j, {"action": "jouer", "cartes": [carte]})


def donner(e, j, cartes):
    return Dame().appliquer(e, j, {"action": "donner", "cartes": cartes})


def faire_l_echange(e):
    """Chacun donne ses 3 premières cartes, dans l'ordre de l'échange."""
    dame = Dame()
    while e["phase"] == "echange":
        j = dame.joueur_actif(e)
        e, _ = donner(e, j, e["mains"][j][:3])
    return e


class RegistreTests(SimpleTestCase):
    def test_inscrit_au_registre(self):
        jeu = registre.obtenir("dame")
        self.assertIsInstance(jeu, Dame)
        d = jeu.decrire()
        self.assertEqual(
            (d["code"], d["nom"], d["min_joueurs"], d["max_joueurs"]),
            ("dame", "Dame de pique", 3, 6),
        )
        self.assertEqual(
            d["options"],
            [
                {"code": "echange", "libelle": "Échange de 3 cartes", "type": "booleen",
                 "defaut": True},
                {"code": "score_fin", "libelle": "Score de fin de partie", "type": "entier",
                 "defaut": 100, "minimum": 20, "maximum": 200},
                {"code": "valet_carreau", "libelle": "Valet de carreau à −10", "type": "booleen",
                 "defaut": False},
            ],
        )

    def test_nombre_de_joueurs(self):
        for nb in (2, 7):
            with self.assertRaises(ValueError):
                partie(nb=nb)


class DistributionTests(SimpleTestCase):
    def test_cartes_retirees_et_donne_egale(self):
        retirees = {
            3: {"2D-1"},
            4: set(),
            5: {"2D-1", "2S-1"},
            6: {"2D-1", "2S-1", "3D-1", "3S-1"},
        }
        for nb, attendu in retirees.items():
            with self.subTest(nb=nb):
                e = partie(nb=nb)
                cartes = [c for m in e["mains"] for c in m]
                self.assertEqual(len(cartes), len(set(cartes)))
                self.assertEqual(len(cartes), 52 - len(attendu))
                self.assertEqual({len(m) for m in e["mains"]}, {(52 - len(attendu)) // nb})
                self.assertIn("2C-1", cartes)
                self.assertEqual(attendu & set(cartes), set())

    def test_mains_triees(self):
        e = partie()
        for main in e["mains"]:
            couleurs = [enseigne(c) for c in main]
            # Chaque couleur d'un seul tenant.
            self.assertEqual(len([k for k in range(1, 13) if couleurs[k] != couleurs[k - 1]]),
                             len(set(couleurs)) - 1)

    def test_graine_de_128_bits(self):
        dame = Dame()
        graine = (1 << 128) - 1
        e = partie(graine=graine, score_fin=20)
        self.assertEqual(json.loads(json.dumps(e)), e)
        coups = 0
        while (j := dame.joueur_actif(e)) is not None:
            e, _ = dame.appliquer(e, j, dame.adversaire(e, j))
            coups += 1
            self.assertLess(coups, 5000)
        self.assertEqual(e["graine"], graine)
        self.assertNotEqual(partie(graine=graine)["mains"], partie(graine=graine - 1)["mains"])


class EchangeTests(SimpleTestCase):
    def test_sens_tourne(self):
        dame = Dame()
        attendus = {4: ["gauche", "droite", "en_face", "aucun", "gauche"],
                    3: ["gauche", "droite", "aucun", "gauche"],
                    5: ["gauche", "droite", "aucun"],
                    6: ["gauche", "droite", "aucun"]}
        for nb, sens in attendus.items():
            e = partie(nb=nb, score_fin=200)
            for attendu in sens:
                with self.subTest(nb=nb, manche=e["manche"]):
                    self.assertEqual(e["sens"], attendu)
                    self.assertEqual(e["phase"], "plis" if attendu == "aucun" else "echange")
                e["phase"] = "fin_manche"
                e["actif"] = 0
                e, _ = dame.appliquer(e, 0, {"action": "manche_suivante"})

    def test_sans_option_pas_d_echange(self):
        e = partie(echange=False)
        self.assertEqual((e["sens"], e["phase"]), ("aucun", "plis"))
        self.assertIn("2C-1", e["mains"][e["actif"]])

    def test_ordre_des_dons(self):
        dame = Dame()
        e = partie(nb=4)
        ordre = []
        while e["phase"] == "echange":
            j = dame.joueur_actif(e)
            ordre.append(j)
            e, _ = donner(e, j, e["mains"][j][:3])
        self.assertEqual(ordre, [1, 2, 3, 0])

    def test_don_prive_et_differe(self):
        e = partie(nb=4)
        avant = copy.deepcopy(e)
        donnees = e["mains"][1][:3]
        e2, message = donner(e, 1, donnees)
        self.assertEqual(e, avant)
        self.assertIsNone(message)
        self.assertEqual(len(e2["mains"][1]), 10)
        # Personne ne reçoit avant que tous aient choisi.
        self.assertEqual(e2["mains"][2], e["mains"][2])
        self.assertEqual(e2["actif"], 2)
        self.assertEqual(e2["phase"], "echange")
        for j in (2, 3):
            e2, message = donner(e2, j, e2["mains"][j][:3])
            self.assertIsNone(message)
            self.assertEqual(len(e2["mains"][(j + 1) % 4]), 13)  # rien reçu encore

    def test_echange_vers_la_gauche(self):
        e = partie(nb=4)
        donnees = [m[:3] for m in e["mains"]]
        fin = faire_l_echange(e)
        for s in range(4):
            receveur = (s + 1) % 4
            self.assertTrue(set(donnees[s]) <= set(fin["mains"][receveur]))
            self.assertFalse(set(donnees[s]) & set(fin["mains"][s]))
            self.assertEqual(sorted(fin["recues"][receveur]), sorted(donnees[s]))
            self.assertEqual(len(fin["mains"][s]), 13)
        self.assertEqual(fin["phase"], "plis")
        self.assertIn("2C-1", fin["mains"][fin["actif"]])

    def test_echange_vers_la_droite_et_en_face(self):
        for sens, decalage in (("droite", -1), ("en_face", 2)):
            with self.subTest(sens=sens):
                e = partie(nb=4)
                e["sens"] = sens
                donnees = [m[:3] for m in e["mains"]]
                fin = faire_l_echange(e)
                for s in range(4):
                    self.assertTrue(set(donnees[s]) <= set(fin["mains"][(s + decalage) % 4]))

    def test_messages_prives(self):
        dame = Dame()
        e = partie(nb=4)
        coup = {"action": "donner", "cartes": e["mains"][1][:3]}
        self.assertRegex(
            dame.message_prive(e, 1, coup), r"^Ordinateur 1 donne .+, .+ et .+ à Ordinateur 2\.$"
        )
        while dame.joueur_actif(e) != 0:
            j = dame.joueur_actif(e)
            e, _ = donner(e, j, e["mains"][j][:3])
        recues = list(e["dons"][3])
        coup = {"action": "donner", "cartes": e["mains"][0][:3]}
        message = dame.message_prive(e, 0, coup)
        self.assertTrue(message.startswith("Tu donnes "), message)
        self.assertIn(" à Ordinateur 1. Tu reçois ", message)
        self.assertTrue(message.endswith(" d'Ordinateur 3."), message)
        from dame.manche import etiquette
        for c in recues:
            self.assertIn(etiquette(c), message)

    def test_dons_refuses(self):
        e = partie(nb=4)
        main = e["mains"][1]
        with self.assertRaisesMessage(CoupRefuse, "Choisis 3 cartes."):
            donner(e, 1, main[:2])
        with self.assertRaisesMessage(CoupRefuse, "Choisis 3 cartes différentes."):
            donner(e, 1, [main[0], main[0], main[1]])
        with self.assertRaisesMessage(CoupRefuse, "Cette carte n'est pas dans ta main."):
            donner(e, 1, main[:2] + [e["mains"][2][0]])
        with self.assertRaisesMessage(CoupRefuse, "Carte inconnue."):
            donner(e, 1, main[:2] + ["ZZ-1"])
        with self.assertRaisesMessage(CoupRefuse, "Action impossible maintenant."):
            donner(e, 0, e["mains"][0][:3])
        with self.assertRaisesMessage(CoupRefuse, "Action impossible maintenant."):
            jouer(e, 1, main[0])


class PlisTests(SimpleTestCase):
    def test_entame_au_deux_de_trefle(self):
        e = etat_plis([["2C-1", "5C-1"], ["3C-1", "4S-1"], ["9C-1", "KD-1"]], plis_joues=0)
        with self.assertRaisesMessage(CoupRefuse, "Entame avec le 2♣."):
            jouer(e, 0, "5C-1")
        e, message = jouer(e, 0, "2C-1")
        self.assertEqual(message, "Tu joues 2♣.")
        self.assertEqual(e["actif"], 1)
        self.assertEqual(e["pli"], [[0, "2C-1"]])

    def test_fournir(self):
        e = etat_plis([["5C-1"], ["3C-1", "AS-1"], ["9D-1"]])
        e, _ = jouer(e, 0, "5C-1")
        with self.assertRaisesMessage(CoupRefuse, "Tu dois fournir : trèfle."):
            jouer(e, 1, "AS-1")
        e, message = jouer(e, 1, "3C-1")
        self.assertEqual(message, "Ordinateur 1 joue 3♣.")
        e, _ = jouer(e, 2, "9D-1")  # sans trèfle : n'importe quelle carte

    def test_premier_pli_ni_coeur_ni_dame(self):
        e = etat_plis([["2C-1"], ["5H-1", "QS-1", "4D-1"], ["9C-1"]], plis_joues=0)
        e, _ = jouer(e, 0, "2C-1")
        with self.assertRaisesMessage(CoupRefuse, "Pas de cœur ni de dame de pique au premier pli."):
            jouer(e, 1, "5H-1")
        with self.assertRaisesMessage(CoupRefuse, "Pas de cœur ni de dame de pique au premier pli."):
            jouer(e, 1, "QS-1")
        jouer(e, 1, "4D-1")
        # Avec seulement des cœurs et la dame : permis.
        e["mains"][1] = ["5H-1", "QS-1"]
        jouer(e, 1, "5H-1")
        jouer(e, 1, "QS-1")
        # Après le premier pli : permis.
        e["plis_joues"] = 1
        e["mains"][1] = ["5H-1", "4D-1"]
        jouer(e, 1, "5H-1")

    def test_coeurs_ouverts(self):
        e = etat_plis([["5H-1", "4D-1"], ["3C-1"], ["9C-1"]])
        self.assertFalse(e["coeurs_ouverts"])
        with self.assertRaisesMessage(CoupRefuse, "Les cœurs ne sont pas encore ouverts."):
            jouer(e, 0, "5H-1")
        e["mains"][0] = ["5H-1", "AH-1"]  # que des cœurs
        jouer(e, 0, "5H-1")
        e["mains"][0] = ["5H-1", "4D-1"]
        e["coeurs_ouverts"] = True
        jouer(e, 0, "5H-1")

    def test_un_coeur_ouvre_les_coeurs_pas_la_dame(self):
        e = etat_plis([["4D-1", "2S-1"], ["QS-1", "3C-1"], ["7H-1", "9C-1"]])
        e, _ = jouer(e, 0, "4D-1")
        e, _ = jouer(e, 1, "QS-1")
        self.assertFalse(e["coeurs_ouverts"])
        e, _ = jouer(e, 2, "7H-1")
        self.assertTrue(e["coeurs_ouverts"])

    def test_le_plus_fort_de_la_couleur_remporte(self):
        e = etat_plis([["10D-1", "2S-1"], ["AS-1", "3C-1"], ["JD-1", "9C-1"], ["5H-1", "8C-1"]])
        e, _ = jouer(e, 0, "10D-1")
        e, _ = jouer(e, 1, "AS-1")  # l'as d'une autre couleur ne prend pas
        e, _ = jouer(e, 2, "JD-1")
        e, message = jouer(e, 3, "5H-1")
        self.assertEqual(message, "Ordinateur 3 joue 5♥. Ordinateur 2 remporte le pli (1 point).")
        self.assertEqual(e["actif"], 2)
        self.assertEqual(e["pli"], [])
        self.assertEqual(e["dernier_pli"], [[0, "10D-1"], [1, "AS-1"], [2, "JD-1"], [3, "5H-1"]])
        self.assertEqual(sorted(e["ramassees"][2]), sorted(["10D-1", "AS-1", "JD-1", "5H-1"]))
        self.assertEqual(e["plis_joues"], 2)
        # Le pli ramassé reste visible jusqu'à la première carte du suivant.
        e, _ = jouer(e, 2, "9C-1")
        self.assertEqual(e["dernier_pli"], [])
        self.assertEqual(e["pli"], [[2, "9C-1"]])

    def test_message_du_pli(self):
        e = etat_plis([["QS-1", "2S-1"], ["KH-1", "3C-1"], ["AH-1", "9C-1"]])
        e["coeurs_ouverts"] = True
        e, _ = jouer(e, 0, "QS-1")
        e, _ = jouer(e, 1, "KH-1")
        e, message = jouer(e, 2, "AH-1")
        self.assertEqual(message, "Ordinateur 2 joue A♥. Tu remportes le pli (15 points).")
        e = etat_plis([["4C-1", "2S-1"], ["3C-1", "3S-1"], ["9C-1", "4S-1"]])
        e, _ = jouer(e, 0, "4C-1")
        e, _ = jouer(e, 1, "3C-1")
        _, message = jouer(e, 2, "9C-1")
        self.assertEqual(message, "Ordinateur 2 joue 9♣. Ordinateur 2 remporte le pli (0 point).")

    def test_figures_en_francais(self):
        from dame.manche import etiquette
        self.assertEqual([etiquette(c) for c in ["AS-1", "KH-1", "QS-1", "JD-1", "10C-1"]],
                         ["A♠", "R♥", "D♠", "V♦", "10♣"])


def dernier_pli(ramassees, dernier, **options):
    """4 joueurs, une carte chacun : le dernier pli de la manche, entamé par le joueur 0."""
    e = etat_plis([[c] for c in dernier], plis_joues=12, **options)
    e["ramassees"] = [list(r) for r in ramassees]
    e["coeurs_ouverts"] = True
    return e


def jouer_le_pli(e):
    message = None
    for _ in range(e["nb"]):
        j = e["actif"]
        e, message = jouer(e, j, e["mains"][j][0])
    return e, message


class FinDeMancheTests(SimpleTestCase):
    def test_points(self):
        e = dernier_pli([["QS-1", "2H-1"], ["3H-1"], [], []], ["AC-1", "4H-1", "5C-1", "6C-1"])
        e, message = jouer_le_pli(e)
        self.assertEqual(e["scores"], [[15, 1, 0, 0]])
        self.assertEqual(e["phase"], "fin_manche")
        self.assertEqual(e["actif"], 0)
        self.assertTrue(message.endswith("Tu remportes le pli (1 point). La manche est terminée."),
                        message)

    def test_grand_chelem(self):
        tous = COEURS[:12] + ["QS-1"]
        e = dernier_pli([tous, [], [], []], ["AC-1", "AH-1", "5C-1", "6C-1"])
        e, message = jouer_le_pli(e)
        self.assertEqual(e["scores"], [[0, 26, 26, 26]])
        self.assertIn("Tu réussis le grand chelem : chacun des autres marque 26.", message)

    def test_valet_de_carreau(self):
        e = dernier_pli([["QS-1"], ["JD-1"], [], []], ["AC-1", "4H-1", "5C-1", "6C-1"],
                        valet_carreau=True)
        e, _ = jouer_le_pli(e)
        self.assertEqual(e["scores"], [[14, -10, 0, 0]])
        # Sans l'option, il ne vaut rien.
        e = dernier_pli([["QS-1"], ["JD-1"], [], []], ["AC-1", "4H-1", "5C-1", "6C-1"])
        e, _ = jouer_le_pli(e)
        self.assertEqual(e["scores"], [[14, 0, 0, 0]])

    def test_valet_hors_du_grand_chelem(self):
        tous = COEURS[:12] + ["QS-1"]
        e = dernier_pli([tous, ["JD-1"], [], []], ["AC-1", "AH-1", "5C-1", "6C-1"],
                        valet_carreau=True)
        e, _ = jouer_le_pli(e)
        self.assertEqual(e["scores"], [[0, 16, 26, 26]])
        e = dernier_pli([tous + ["JD-1"], [], [], []], ["AC-1", "AH-1", "5C-1", "6C-1"],
                        valet_carreau=True)
        e, _ = jouer_le_pli(e)
        self.assertEqual(e["scores"], [[-10, 26, 26, 26]])

    def test_manche_suivante(self):
        dame = Dame()
        e = dernier_pli([["QS-1"], [], [], []], ["AC-1", "4H-1", "5C-1", "6C-1"])
        e["options"]["echange"] = True
        e, _ = jouer_le_pli(e)
        with self.assertRaisesMessage(CoupRefuse, "Action impossible maintenant."):
            jouer(e, 0, "AC-1")
        e, message = dame.appliquer(e, 0, {"action": "manche_suivante"})
        self.assertEqual(message, "La manche 2 commence : échange vers la droite.")
        self.assertEqual((e["manche"], e["phase"], e["sens"]), (2, "echange", "droite"))
        self.assertEqual(e["dernier_pli"], [])
        self.assertEqual(e["ramassees"], [[], [], [], []])
        self.assertEqual(e["plis_joues"], 0)
        self.assertFalse(e["coeurs_ouverts"])
        self.assertEqual({len(m) for m in e["mains"]}, {13})
        self.assertEqual(e["scores"], [[14, 0, 0, 0]])
        e["phase"], e["actif"], e["manche"] = "fin_manche", 0, 3
        _, message = dame.appliquer(e, 0, {"action": "manche_suivante"})
        self.assertEqual(message, "La manche 4 commence, sans échange.")

    def test_fin_de_partie(self):
        dame = Dame()
        e = dernier_pli([["QS-1"], [], [], []], ["AC-1", "4H-1", "5C-1", "6C-1"], score_fin=20)
        e["scores"] = [[6, 0, 0, 0]]
        e, message = jouer_le_pli(e)
        self.assertEqual(e["phase"], "terminee")
        self.assertIsNone(dame.joueur_actif(e))
        self.assertTrue(message.endswith("La partie est terminée."), message)
        with self.assertRaisesMessage(CoupRefuse, "Action impossible maintenant."):
            dame.appliquer(e, 0, {"action": "manche_suivante"})


class AppliquerTests(SimpleTestCase):
    def test_appliquer_ne_modifie_pas_l_etat(self):
        e = etat_plis([["5C-1"], ["3C-1"], ["9C-1"]])
        avant = copy.deepcopy(e)
        jouer(e, 0, "5C-1")
        self.assertEqual(e, avant)

    def test_coups_malformes(self):
        dame = Dame()
        e = etat_plis([["5C-1", "6C-1"], ["3C-1"], ["9C-1"]])
        with self.assertRaisesMessage(CoupRefuse, "Choisis 1 carte."):
            dame.appliquer(e, 0, {"action": "jouer", "cartes": ["5C-1", "6C-1"]})
        with self.assertRaisesMessage(CoupRefuse, "Cette carte n'est pas dans ta main."):
            jouer(e, 0, "3C-1")
        with self.assertRaisesMessage(CoupRefuse, "Action impossible maintenant."):
            dame.appliquer(e, 0, {"action": "donner", "cartes": []})
        with self.assertRaisesMessage(CoupRefuse, "Action impossible maintenant."):
            jouer(e, 1, "3C-1")
        with self.assertRaisesMessage(CoupRefuse, "Action manquante."):
            dame.appliquer(e, 0, {})

    def test_joueur_actif(self):
        dame = Dame()
        e = partie()
        self.assertEqual(dame.joueur_actif(e), 1)
        e["phase"] = "terminee"
        self.assertIsNone(dame.joueur_actif(e))
