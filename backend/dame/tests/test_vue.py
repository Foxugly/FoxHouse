import json

from django.test import SimpleTestCase

from dame.jeu import Dame
from dame.tests.test_jeu import dernier_pli, donner, etat_plis, jouer, jouer_le_pli, partie
from dame.vue import vue
from tapis.vue import valider_vue


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


def ids_interdits(etat, j):
    """Les cartes que le joueur j ne doit jamais voir : mains et dons des autres."""
    interdits = set()
    for k in range(etat["nb"]):
        if k != j:
            interdits |= set(etat["mains"][k]) | set(etat["dons"][k] or [])
    return interdits


class VueTests(SimpleTestCase):
    def test_vue_conforme(self):
        e = partie(nb=4)
        for j in range(4):
            valider_vue(vue(e, j))
        e, _ = donner(e, 1, e["mains"][1][:3])
        valider_vue(vue(e, 0))
        e = dernier_pli([["QS-1"], [], [], []], ["AC-1", "4H-1", "5C-1", "6C-1"])
        e, _ = jouer_le_pli(e)
        v = vue(e, 0)
        valider_vue(v)
        self.assertFalse(v["terminee"])
        self.assertEqual(Dame().vue(e, 0), v)

    def test_sieges_et_compteurs(self):
        e = etat_plis([["2S-1"], ["3S-1"], ["4S-1"], ["5S-1"]])
        e["ramassees"] = [["QS-1", "2H-1"], [], ["3H-1"], []]
        e["scores"] = [[3, 10, 0, 13], [1, 1, 1, 0]]
        v = vue(e, 2)
        self.assertEqual([s["id"] for s in v["sieges"]], [2, 3, 0, 1])
        self.assertEqual([s["nom"] for s in v["sieges"]],
                         ["Ordinateur 2", "Ordinateur 3", "Toi", "Ordinateur 1"])
        self.assertEqual([s["actif"] for s in v["sieges"]], [False, False, True, False])
        self.assertEqual(
            v["sieges"][2]["compteurs"],
            [{"libelle": "Points", "valeur": 14}, {"libelle": "Total", "valeur": 4}],
        )

    def test_zones_des_mains_et_des_plis(self):
        e = etat_plis([["2S-1", "9S-1"], ["3S-1", "8D-1"], ["4S-1", "8C-1"]])
        e, _ = jouer(e, 0, "2S-1")
        v = vue(e, 1)
        self.assertEqual(ids(zone(v, "main-1")), ["3S-1", "8D-1"])
        self.assertEqual(zone(v, "main-0")["cartes"], [{"cachee": True}])
        self.assertEqual(zone(v, "main-0")["libelle"], "Toi")
        self.assertEqual(zone(v, "main-1")["libelle"], "Ta main")
        pli0 = zone(v, "pli-0")
        self.assertEqual((pli0["type"], pli0["siege"], pli0["libelle"]), ("pli", 0, "Pli"))
        self.assertEqual(ids(pli0), ["2S-1"])
        self.assertEqual(ids(zone(v, "pli-1")), [])
        self.assertFalse([z for z in v["zones"] if z["siege"] is None])

    def test_le_pli_ramasse_reste_visible(self):
        e = etat_plis([["2S-1", "9S-1"], ["3S-1", "8D-1"], ["4S-1", "8C-1"]])
        for j, c in ((0, "2S-1"), (1, "3S-1"), (2, "4S-1")):
            e, _ = jouer(e, j, c)
        v = vue(e, 0)
        self.assertEqual([ids(zone(v, f"pli-{s}")) for s in range(3)],
                         [["2S-1"], ["3S-1"], ["4S-1"]])
        e, _ = jouer(e, 2, "8C-1")
        v = vue(e, 0)
        self.assertEqual([ids(zone(v, f"pli-{s}")) for s in range(3)], [[], [], ["8C-1"]])

    def test_menu(self):
        e = partie(nb=4)
        self.assertEqual(menu(vue(e, 0)), {
            "Manche": 1, "Échange": "vers la gauche", "Cœurs": "fermés", "Score de fin": 100,
        })
        e = etat_plis([["2S-1"], ["3S-1"], ["4H-1"]])
        e["coeurs_ouverts"] = True
        self.assertEqual(menu(vue(e, 0))["Cœurs"], "ouverts")
        self.assertEqual(menu(vue(e, 0))["Échange"], "aucun")

    def test_cartes_recues_au_menu(self):
        dame = Dame()
        e = partie(nb=4)
        while e["phase"] == "echange":
            j = dame.joueur_actif(e)
            e, _ = donner(e, j, e["mains"][j][:3])
        recues = e["recues"][0]
        self.assertEqual(len(recues), 3)
        from dame.manche import enumerer
        self.assertEqual(menu(vue(e, 0))["Reçues"], enumerer(recues))
        # Jusqu'à la fin du premier pli seulement.
        while e["plis_joues"] == 0:
            j = dame.joueur_actif(e)
            e, _ = dame.appliquer(e, j, dame.adversaire(e, j))
        self.assertNotIn("Reçues", menu(vue(e, 0)))

    def test_actions(self):
        e = partie(nb=4)
        self.assertEqual(vue(e, 0)["actions"], [])
        self.assertEqual(vue(e, 1)["actions"], [{
            "id": "donner", "libelle": "Donner à Ordinateur 2", "cartes_min": 3,
            "cartes_max": 3, "cible": None,
        }])
        e = etat_plis([["2S-1"], ["3S-1"], ["4H-1"]])
        self.assertEqual(vue(e, 0)["actions"], [{
            "id": "jouer", "libelle": "Jouer", "cartes_min": 1, "cartes_max": 1, "cible": None,
            "direct": True,
        }])
        e = dernier_pli([["QS-1"], [], [], []], ["AC-1", "4H-1", "5C-1", "6C-1"])
        e, _ = jouer_le_pli(e)
        self.assertEqual([a["id"] for a in vue(e, 0)["actions"]], ["manche_suivante"])
        self.assertEqual(vue(e, 0)["actions"][0]["libelle"], "Manche suivante")

    def test_resultat(self):
        e = partie(nb=3)
        self.assertIsNone(vue(e, 0)["resultat"])
        e = dernier_pli([["QS-1"], [], [], []], ["AC-1", "4H-1", "5C-1", "6C-1"])
        e, _ = jouer_le_pli(e)
        r = vue(e, 0)["resultat"]
        self.assertEqual(r["titre"], "Fin de la manche 1")
        self.assertEqual(r["colonnes"], ["Joueur", "Manche 1", "Total"])
        self.assertEqual(r["lignes"][0], ["Toi", 14, 14])
        e["phase"] = "terminee"
        e["scores"] = [[30, 40, 50, 60], [80, 61, 60, 50]]
        v = vue(e, 0)
        self.assertTrue(v["terminee"])
        self.assertEqual(v["actions"], [])
        r = v["resultat"]
        self.assertEqual(r["titre"], "Fin de la partie — Ordinateur 1 gagne")
        self.assertEqual(r["lignes"][1], ["Ordinateur 1", 40, 61, 101])
        e["scores"] = [[30, 40, 50, 60], [70, 60, 60, 50]]
        self.assertEqual(vue(e, 0)["resultat"]["titre"], "Fin de la partie — égalité")
        e["scores"] = [[3, 40, 50, 60], [70, 60, 60, 50]]
        self.assertEqual(vue(e, 0)["resultat"]["titre"], "Fin de la partie — Tu gagnes")

    def test_echange_ne_revele_pas_les_choix(self):
        e = partie(nb=4)
        e, _ = donner(e, 1, e["mains"][1][:3])
        e, _ = donner(e, 2, e["mains"][2][:3])
        for j in (0, 3):
            v = vue(e, j)
            self.assertEqual(ids_interdits(e, j) & chaines(v), set())
        # Témoin : la main de 0 est bien visible.
        self.assertEqual(set(e["mains"][0]) - chaines(vue(e, 0)), set())

    def test_vue_ne_fuit_rien(self):
        dame = Dame()
        for graine in range(1, 21):
            nb = 3 + graine % 4
            e = partie(nb=nb, graine=graine, score_fin=30)
            coups = 0
            while (j := dame.joueur_actif(e)) is not None:
                for k in range(nb):
                    self._verifier(e, k)
                e, _ = dame.appliquer(e, j, dame.adversaire(e, j))
                coups += 1
                self.assertLess(coups, 5000, f"graine {graine} : la partie ne finit pas")
            self._verifier(e, 0)

    def _verifier(self, etat, j):
        v = vue(etat, j)
        self.assertNotIn("graine", json.dumps(v))
        vues = chaines(v)
        self.assertEqual(ids_interdits(etat, j) & vues, set(), f"phase {etat['phase']}")
        visibles = set(etat["mains"][j]) | {c for _, c in etat["pli"] or etat["dernier_pli"]}
        self.assertEqual(visibles - vues, set(), "le détecteur ne voit pas les cartes visibles")
