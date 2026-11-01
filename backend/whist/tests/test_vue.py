import json

from django.test import SimpleTestCase

from tapis.vue import valider_vue
from whist.jeu import Whist
from whist.tests.aides import appliquer, etat_encheres, etat_plis, jouer, jouer_le_pli, partie
from whist.vue import main_ouverte, retournee_visible, vue


def chaines(v):
    """Toutes les chaînes (clés et valeurs) de la vue telle qu'envoyée en JSON."""
    trouvees = set()

    def parcourir(x):
        if isinstance(x, str):
            trouvees.add(x)
        elif isinstance(x, dict):
            for cle, valeur in x.items():
                trouvees.add(cle)
                parcourir(valeur)
        elif isinstance(x, list):
            for valeur in x:
                parcourir(valeur)

    parcourir(json.loads(json.dumps(v)))
    return trouvees


def zone(v, zid):
    return next(z for z in v["zones"] if z["id"] == zid)


def menu(v):
    return {m["libelle"]: m["valeur"] for m in v["menu"]}


def ids(zone_):
    return [c["id"] for c in zone_["cartes"]]


def publiques(etat):
    """Les cartes en main que tout le monde voit : la retournée, la main d'une misère ouverte."""
    vues = set()
    if retournee_visible(etat):
        vues.add(etat["retournee"])
    if (s := main_ouverte(etat)) is not None:
        vues |= set(etat["mains"][s])
    return vues


def ids_interdits(etat, j):
    interdits = set()
    for k in range(4):
        if k != j:
            interdits |= set(etat["mains"][k])
    return interdits - publiques(etat)


class VueTests(SimpleTestCase):
    def test_vue_conforme(self):
        e = etat_encheres()
        for j in range(4):
            valider_vue(vue(e, j))
        self.assertEqual(Whist().vue(e, 0), vue(e, 0))
        e = etat_plis([["AS-1"], ["KS-1"], ["2S-1"], ["QS-1"]])
        e, _ = jouer_le_pli(e, ["AS-1", "KS-1", "2S-1", "QS-1"])
        valider_vue(vue(e, 0))

    def test_sieges_et_compteurs(self):
        e = etat_plis([["2S-1"], ["3S-1"], ["4S-1"], ["5S-1"]], actif=2)
        e["plis"] = [3, 1, 4, 1]
        e["scores"] = [[2, -2, 2, -2], [-5, -5, 15, -5]]
        v = vue(e, 2)
        self.assertEqual([s["id"] for s in v["sieges"]], [2, 3, 0, 1])
        self.assertEqual([s["nom"] for s in v["sieges"]],
                         ["Ordinateur 2", "Ordinateur 3", "Toi", "Ordinateur 1"])
        self.assertEqual([s["actif"] for s in v["sieges"]], [True, False, False, False])
        self.assertEqual(v["sieges"][0]["compteurs"],
                         [{"libelle": "Plis", "valeur": 4}, {"libelle": "Total", "valeur": 17}])

    def test_zones_des_mains_et_des_plis(self):
        e = etat_plis([["2S-1", "9S-1"], ["3S-1", "8D-1"], ["4S-1", "8C-1"], ["5S-1", "7C-1"]])
        e, _ = jouer(e, 0, "2S-1")
        v = vue(e, 1)
        self.assertEqual(ids(zone(v, "main-1")), ["3S-1", "8D-1"])
        self.assertEqual(zone(v, "main-1")["libelle"], "Ta main")
        self.assertEqual(zone(v, "main-0")["cartes"], [{"cachee": True}])
        self.assertEqual(zone(v, "main-0")["libelle"], "Toi")
        pli0 = zone(v, "pli-0")
        self.assertEqual((pli0["type"], pli0["siege"], pli0["libelle"]), ("pli", 0, "Pli"))
        self.assertEqual(ids(pli0), ["2S-1"])
        self.assertEqual(ids(zone(v, "pli-1")), [])

    def test_le_pli_ramasse_reste_visible(self):
        e = etat_plis([["2S-1", "9S-1"], ["3S-1", "8D-1"], ["AS-1", "8C-1"], ["5S-1", "7C-1"]])
        e, _ = jouer_le_pli(e, ["2S-1", "3S-1", "AS-1", "5S-1"])
        v = vue(e, 0)
        self.assertEqual([ids(zone(v, f"pli-{s}")) for s in range(4)],
                         [["2S-1"], ["3S-1"], ["AS-1"], ["5S-1"]])
        e, _ = jouer(e, 2, "8C-1")
        v = vue(e, 0)
        self.assertEqual([ids(zone(v, f"pli-{s}")) for s in range(4)], [[], [], ["8C-1"], []])

    def test_la_carte_retournee_tant_que_le_donneur_ne_l_a_pas_jouee(self):
        e = etat_plis([["2S-1", "9S-1"], ["3S-1", "8D-1"], ["4S-1", "8C-1"], ["7H-1", "7C-1"]],
                      retournee="7H-1", donneur=3)
        v = vue(e, 0)
        atout = zone(v, "atout")
        self.assertEqual((atout["type"], atout["siege"], atout["libelle"]), ("pile", None, "Atout"))
        self.assertEqual(ids(atout), ["7H-1"])
        self.assertEqual(menu(v)["Retournée"], "7♥")
        # Le donneur la voit aussi dans sa main (même identifiant, le schéma l'accepte).
        v3 = vue(e, 3)
        valider_vue(v3)
        self.assertIn("7H-1", ids(zone(v3, "main-3")))
        e, _ = jouer_le_pli(e, ["2S-1", "3S-1", "4S-1", "7H-1"])
        v = vue(e, 0)
        self.assertFalse([z for z in v["zones"] if z["id"] == "atout"])
        self.assertNotIn("Retournée", menu(v))

    def test_misere_ouverte_main_etalee_apres_le_premier_pli(self):
        mains = [["2S-1", "9S-1"], ["3S-1", "8D-1"], ["AS-1", "8C-1"], ["5S-1", "7C-1"]]
        e = etat_plis(mains, code="misere_ouverte", preneurs=[1], atout=None)
        e["plis_joues"] = 0
        # Avant la fin du premier pli : cachée.
        self.assertEqual(zone(vue(e, 0), "main-1")["cartes"][0], {"cachee": True})
        e, _ = jouer_le_pli(e, ["2S-1", "3S-1", "AS-1", "5S-1"])
        v = vue(e, 0)
        self.assertEqual(ids(zone(v, "main-1")), e["mains"][1])
        self.assertEqual(zone(v, "main-3")["cartes"][0], {"cachee": True})
        # Une misère simple ne s'étale pas.
        e["contrat"]["code"] = "misere"
        self.assertEqual(zone(vue(e, 0), "main-1")["cartes"][0], {"cachee": True})

    def test_menu_pendant_les_encheres(self):
        e = etat_encheres(donnes=6)
        m = menu(vue(e, 0))
        self.assertEqual(m["Donne"], "1 / 6")
        self.assertEqual(m["Donneur"], "Ordinateur 3")
        self.assertEqual(m["Plus haute annonce"], "aucune")
        self.assertIn("Retournée", m)
        e, _ = appliquer(e, 0, "demander")
        e, _ = appliquer(e, 1, "accepter")
        self.assertEqual(menu(vue(e, 0))["Plus haute annonce"], "Emballage (Ordinateur 1 et toi)")

    def test_menu_apres_les_encheres(self):
        e = etat_plis([["2S-1"], ["3S-1"], ["4S-1"], ["5S-1"]], code="emballage",
                      preneurs=[0, 2], atout="D")
        e["plis"] = [3, 0, 2, 0]
        m = menu(vue(e, 1))
        self.assertEqual(m["Contrat"], "Emballage")
        self.assertEqual(m["Preneurs"], "Ordinateur 2 et toi")
        self.assertEqual(m["Atout"], "carreau")
        self.assertEqual(m["Plis des preneurs"], 5)
        self.assertNotIn("Plus haute annonce", m)
        e["contrat"] = {"code": "misere", "preneurs": [3]}
        e["atout"] = None
        m = menu(vue(e, 1))
        self.assertEqual((m["Preneur"], m["Atout"]), ("Ordinateur 3", "sans atout"))
        self.assertNotIn("Plis des preneurs", m)
        e["phase"] = "atout"
        e["contrat"] = {"code": "abondance_9", "preneurs": [3]}
        self.assertEqual(menu(vue(e, 1))["Atout"], "à choisir")

    def test_actions(self):
        e = etat_encheres()
        actions = vue(e, 0)["actions"]
        self.assertEqual(actions[0], {"id": "passer", "libelle": "Passer", "cartes_min": 0,
                                      "cartes_max": 0, "cible": None})
        self.assertEqual([a["libelle"] for a in actions[1:4]],
                         ["Demander", "Seul (5 plis)", "Abondance 9"])
        self.assertEqual(vue(e, 1)["actions"], [])
        e, _ = appliquer(e, 0, "demander")
        self.assertEqual(vue(e, 1)["actions"][1]["libelle"], "Accepter")
        e = etat_plis([["2S-1"], ["3S-1"], ["4S-1"], ["5S-1"]])
        self.assertEqual(vue(e, 0)["actions"], [{
            "id": "jouer", "libelle": "Jouer", "cartes_min": 1, "cartes_max": 1, "cible": None,
            "direct": True,
        }])
        e["phase"] = "demande_seule"
        self.assertEqual([(a["id"], a["libelle"]) for a in vue(e, 0)["actions"]],
                         [("seul", "Jouer seul (5 plis)"), ("passer", "Passer")])
        e["phase"] = "atout"
        self.assertEqual([a["libelle"] for a in vue(e, 0)["actions"]],
                         ["Atout pique", "Atout cœur", "Atout carreau", "Atout trèfle"])
        e["phase"] = "fin_donne"
        self.assertEqual([(a["id"], a["libelle"]) for a in vue(e, 0)["actions"]],
                         [("donne_suivante", "Donne suivante")])

    def test_resultat(self):
        e = partie()
        self.assertIsNone(vue(e, 0)["resultat"])
        e = etat_plis([["AS-1"], ["KS-1"], ["2S-1"], ["QS-1"]], code="seul", preneurs=[0])
        e["plis"] = [6, 2, 2, 2]
        e, _ = jouer_le_pli(e, ["AS-1", "KS-1", "2S-1", "QS-1"])
        r = vue(e, 0)["resultat"]
        self.assertEqual(r["titre"], "Fin de la donne 1")
        self.assertEqual(r["colonnes"], ["Joueur", "Donne 1", "Total"])
        self.assertEqual(r["lignes"][0], ["Toi", 15, 15])
        self.assertEqual(menu(vue(e, 0))["Donne"], "1 / 8")
        e["phase"] = "terminee"
        e["scores"] = [[2, -2, 2, -2], [-5, 15, -5, -5]]
        v = vue(e, 0)
        self.assertTrue(v["terminee"])
        self.assertEqual(v["actions"], [])
        self.assertEqual(v["resultat"]["titre"], "Fin de la partie — Ordinateur 1 gagne")
        self.assertEqual(v["resultat"]["lignes"][1], ["Ordinateur 1", -2, 15, 13])
        e["scores"] = [[2, -2, 2, -2]]
        self.assertEqual(vue(e, 0)["resultat"]["titre"], "Fin de la partie — égalité")
        e["scores"] = [[15, -5, -5, -5]]
        self.assertEqual(vue(e, 0)["resultat"]["titre"], "Fin de la partie — Tu gagnes")
        valider_vue(vue(e, 0))

    def test_vue_ne_fuit_rien(self):
        whist = Whist()
        for graine in range(1, 21):
            options = [{}, {"trou": False}, {"misere": False}][graine % 3]
            e = partie(graine=graine, donnes=4, **options)
            coups = 0
            while (j := whist.joueur_actif(e)) is not None:
                for k in range(4):
                    self._verifier(e, k)
                e, _ = whist.appliquer(e, j, whist.adversaire(e, j))
                coups += 1
                self.assertLess(coups, 3000, f"graine {graine} : la partie ne finit pas")
            self._verifier(e, 0)

    def test_fuite_sous_misere_ouverte(self):
        whist = Whist()
        e = etat_encheres(graine=3)
        e, _ = appliquer(e, 0, "misere_ouverte")
        for j in (1, 2, 3):
            e, _ = appliquer(e, j, "passer")
        while e["phase"] == "plis":
            for k in range(4):
                self._verifier(e, k)
            j = whist.joueur_actif(e)
            e, _ = whist.appliquer(e, j, whist.adversaire(e, j))
        self._verifier(e, 1)

    def _verifier(self, etat, j):
        v = vue(etat, j)
        self.assertNotIn("graine", json.dumps(v))
        vues = chaines(v)
        self.assertEqual(ids_interdits(etat, j) & vues, set(), f"phase {etat['phase']}")
        visibles = (set(etat["mains"][j]) | publiques(etat)
                    | {c for _, c in etat["pli"] or etat["dernier_pli"]})
        self.assertEqual(visibles - vues, set(), "le détecteur ne voit pas les cartes visibles")
