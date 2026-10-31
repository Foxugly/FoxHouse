import json

from django.test import SimpleTestCase

from huit.jeu import Huit
from huit.tests.outils import ids, partie, table
from huit.vue import vue
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


def ids_interdits(etat, j):
    """Les cartes que le joueur j ne doit jamais voir : la pioche et les mains des autres."""
    interdits = set(etat["pioche"])
    for k, main in enumerate(etat["mains"]):
        if k != j:
            interdits |= set(main)
    return interdits


class VueTests(SimpleTestCase):
    def test_vue_conforme_et_par_le_jeu(self):
        e = partie(nb=3)
        valider_vue(vue(e, 0))
        valider_vue(vue(e, 2))
        self.assertEqual(Huit().vue(e, 1), vue(e, 1))

    def test_sieges_et_compteurs(self):
        e = partie(nb=4)
        e["scores"] = [[10, 0, 5, 3], [2, 7, 0, 1]]
        v = vue(e, 2)
        self.assertEqual([s["id"] for s in v["sieges"]], [2, 3, 0, 1])
        self.assertEqual(
            [s["nom"] for s in v["sieges"]], ["Ordinateur 2", "Ordinateur 3", "Toi", "Ordinateur 1"]
        )
        self.assertEqual([s["actif"] for s in v["sieges"]], [False, False, True, False])
        self.assertEqual(
            v["sieges"][2]["compteurs"],
            [{"libelle": "Cartes", "valeur": 8}, {"libelle": "Points", "valeur": 12}],
        )

    def test_zones(self):
        e = partie(nb=3)
        v = vue(e, 0)
        self.assertEqual([z["id"] for z in v["zones"]],
                         ["main-0", "main-1", "main-2", "pioche", "defausse"])
        main = zone(v, "main-0")
        self.assertEqual((main["type"], main["siege"], main["libelle"]), ("main", 0, "Ta main"))
        self.assertEqual([c["id"] for c in main["cartes"]], e["mains"][0])
        self.assertEqual(zone(v, "main-1")["cartes"], [{"cachee": True}] * 8)
        self.assertEqual(zone(v, "main-1")["libelle"], "Ordinateur 1")
        pioche = zone(v, "pioche")
        self.assertEqual((pioche["type"], pioche["nombre"], pioche["cartes"]),
                         ("pile", len(e["pioche"]), []))
        defausse = zone(v, "defausse")
        self.assertEqual((defausse["type"], defausse["nombre"]), ("pile", 1))
        self.assertEqual([c["id"] for c in defausse["cartes"]], [e["defausse"][-1]])

    def test_menu(self):
        e = table(partie(nb=3, manches=4), {0: ["2H-1", "KD-1"]}, "7H-1")
        self.assertEqual(menu(vue(e, 0)), {"Manche": "1 / 4", "Sens du jeu": "normal"})
        e, _ = Huit().appliquer(e, 0, {"action": "jouer", "cartes": ["2H-1"]})
        self.assertEqual(menu(vue(e, 1))["Pénalité"], "2 cartes")
        e["sens"], e["couleur"] = -1, "C"
        self.assertEqual(
            menu(vue(e, 1)),
            {"Manche": "1 / 4", "Couleur demandée": "Trèfle", "Sens du jeu": "inversé",
             "Pénalité": "2 cartes"},
        )

    def test_menu_carte_sous_le_joker(self):
        e = table(partie(nb=3, jokers=True), {0: ["KD-1"]}, ["7H-1", "JK-1"])
        v = vue(e, 0)
        self.assertEqual(menu(v)["Carte à suivre"], "7♥")
        self.assertEqual(zone(v, "defausse")["cartes"], [{"id": "JK-1", "joker": True}])
        valider_vue(v)

    def test_actions(self):
        jeu = Huit()
        e = table(partie(nb=3), {0: ["8H-1", "KD-1"]}, "7H-1")
        v = vue(e, 0)
        self.assertEqual(
            v["actions"],
            [
                {"id": "jouer", "libelle": "Jouer", "cartes_min": 1, "cartes_max": 1,
                 "cible": None},
                {"id": "piocher", "libelle": "Piocher", "cartes_min": 0, "cartes_max": 0,
                 "cible": None},
            ],
        )
        self.assertEqual(vue(e, 1)["actions"], [])
        e, _ = jeu.appliquer(e, 0, {"action": "jouer", "cartes": ["8H-1"]})
        self.assertEqual(
            [a["libelle"] for a in vue(e, 0)["actions"]], ["Pique", "Cœur", "Carreau", "Trèfle"]
        )
        self.assertEqual(ids(vue(e, 0)["actions"])[0], "couleur_S")

    def test_resultat(self):
        jeu = Huit()
        e = table(partie(nb=2, manches=2), {0: ["3H-1"], 1: ["KD-1", "4C-1"]}, "7H-1")
        self.assertIsNone(vue(e, 0)["resultat"])
        e, _ = jeu.appliquer(e, 0, {"action": "jouer", "cartes": ["3H-1"]})
        v = vue(e, 0)
        valider_vue(v)
        self.assertEqual(
            v["resultat"],
            {"titre": "Fin de la manche 1", "colonnes": ["Joueur", "Manche 1", "Total"],
             "lignes": [["Toi", 0, 0], ["Ordinateur 1", 14, 14]]},
        )
        self.assertEqual(menu(v), {"Manche": "1 / 2"})
        self.assertEqual(ids(v["actions"]), ["manche_suivante"])

        e["phase"] = "terminee"
        e["scores"] = [[0, 14], [30, 5]]
        v = vue(e, 1)
        valider_vue(v)
        self.assertTrue(v["terminee"])
        self.assertEqual(v["actions"], [])
        self.assertEqual(v["resultat"]["titre"], "Fin de la partie — Ordinateur 1 gagne")
        self.assertEqual(v["resultat"]["lignes"], [["Ordinateur 1", 14, 5, 19], ["Toi", 0, 30, 30]])
        e["scores"] = [[0, 14], [5, 30]]
        self.assertEqual(vue(e, 0)["resultat"]["titre"], "Fin de la partie — Tu gagnes")
        e["scores"] = [[0, 14], [14, 0]]
        self.assertEqual(vue(e, 0)["resultat"]["titre"], "Fin de la partie — égalité")

    def test_vue_ne_fuit_rien(self):
        jeu = Huit()
        for graine in range(1, 31):
            nb = 2 + graine % 5
            e = partie(nb=nb, graine=graine, manches=2, jokers=graine % 2 == 0)
            coups = 0
            while (j := jeu.joueur_actif(e)) is not None:
                self._verifier(e, graine % nb)
                e, _ = jeu.appliquer(e, j, jeu.adversaire(e, j))
                coups += 1
                self.assertLess(coups, 3000, f"graine {graine} : la partie ne finit pas")
            self._verifier(e, 0)

    def _verifier(self, etat, j):
        v = vue(etat, j)
        valider_vue(v)
        self.assertNotIn("graine", json.dumps(v))
        vues = chaines(v)
        self.assertEqual(ids_interdits(etat, j) & vues, set(), f"phase {etat['phase']}")
        # Témoin : le détecteur voit bien ce qui est montré (sa main, le dessus de la défausse).
        visibles = set(etat["mains"][j]) | set(etat["defausse"][-1:])
        self.assertEqual(visibles - vues, set(), "le détecteur ne voit pas les cartes visibles")
