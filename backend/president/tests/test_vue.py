import json

from django.test import SimpleTestCase

from president.jeu import President
from president.manche import etiquette_carte
from president.tests.test_jeu import etat_pli, fin_de_manche, jouer, partie, passer
from president.vue import vue
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


def echange_en_cours():
    """Manche 2 à 4 joueurs : Président 2, Vice-président 0, Vice-pauvre 3, Pauvre 1."""
    e = fin_de_manche(4, [2, 0, 3, 1])
    e, _ = President().appliquer(e, 0, {"action": "manche_suivante"})
    return e


class VueTests(SimpleTestCase):
    def test_vue_conforme_a_chaque_phase(self):
        jeu = President()
        etats = [partie(nb=5)]
        e = etat_pli([["5S-1", "4C-1"], ["6S-1", "3S-1"], ["7S-1", "8H-1"]], manches=1)
        e, _ = jouer(e, 0, ["5S-1"])
        etats.append(e)
        e, _ = passer(e, 1)
        e, _ = passer(e, 2)
        etats.append(e)  # pli fermé
        etats.append(echange_en_cours())
        etats.append(fin_de_manche(3, [0, 1, 2]))
        fin = fin_de_manche(3, [0, 1, 2])
        fin["phase"] = "terminee"
        etats.append(fin)
        for k, etat in enumerate(etats):
            for j in range(etat["nb"]):
                with self.subTest(etat=k, joueur=j):
                    v = vue(etat, j)
                    valider_vue(v)
                    self.assertEqual(v, jeu.vue(etat, j))
                    self.assertEqual(v["jeu"], "president")
        self.assertTrue(vue(fin, 0)["terminee"])
        self.assertEqual(vue(fin, 0)["actions"], [])

    def test_sieges_et_compteurs(self):
        e = fin_de_manche(4, [2, 0, 3, 1])
        e["mains"] = [["5S-1"], ["6S-1", "7S-1"], [], ["8S-1"]]
        e["points"] = [[2, 0, 3, 1], [3, 1, 0, 2]]
        e["phase"], e["actif"] = "pli", 3
        v = vue(e, 2)
        self.assertEqual([s["id"] for s in v["sieges"]], [2, 3, 0, 1])
        self.assertEqual(
            [s["nom"] for s in v["sieges"]], ["Ordinateur 2", "Ordinateur 3", "Toi", "Ordinateur 1"]
        )
        self.assertEqual([s["actif"] for s in v["sieges"]], [False, True, False, False])
        self.assertEqual(
            v["sieges"][2]["compteurs"],
            [{"libelle": "Cartes", "valeur": 1}, {"libelle": "Rang", "valeur": "Vice-président"},
             {"libelle": "Total", "valeur": 5}],
        )
        # Première manche : pas encore de rang.
        self.assertEqual(vue(partie(), 0)["sieges"][0]["compteurs"][1]["valeur"], "—")

    def test_zones(self):
        e = etat_pli([["9S-1", "4C-1", "9H-1"], ["6S-1", "8S-1"], ["7S-1"]])
        v = vue(e, 0)
        self.assertEqual([z["id"] for z in v["zones"]], ["main-0", "main-1", "main-2", "pli"])
        main = zone(v, "main-0")
        self.assertEqual((main["type"], main["siege"], main["libelle"]), ("main", 0, "Ta main"))
        self.assertEqual([c["id"] for c in main["cartes"]], ["4C-1", "9H-1", "9S-1"])  # triée
        self.assertEqual(zone(v, "main-1")["cartes"], [{"cachee": True}] * 2)
        self.assertEqual(zone(v, "main-1")["libelle"], "Ordinateur 1")
        pli = zone(v, "pli")
        self.assertEqual((pli["type"], pli["siege"], pli["libelle"], pli["cartes"]),
                         ("pli", None, "Pli", []))

        e, _ = jouer(e, 0, ["9S-1", "9H-1"])
        pli = zone(vue(e, 1), "pli")
        self.assertEqual([c["id"] for c in pli["cartes"]], ["9S-1", "9H-1"])
        self.assertEqual(pli["libelle"], "Pli")
        self.assertEqual(menu(vue(e, 1)), {
            "Manche": "1 / 5", "À poser": "2 cartes", "Dernière combinaison": "Toi",
        })
        e, _ = passer(e, 1)
        e, _ = passer(e, 2)
        v = vue(e, 0)
        # Fermé, le pli reste affiché jusqu'à l'entame suivante.
        self.assertEqual(zone(v, "pli")["libelle"], "Dernier pli")
        self.assertEqual([c["id"] for c in zone(v, "pli")["cartes"]], ["9S-1", "9H-1"])
        self.assertEqual(menu(v)["À poser"], "1 à 4 cartes (entame)")

    def test_menu_a_l_entame_de_la_manche(self):
        e = etat_pli([["5S-1"], ["6S-1"], ["7S-1"]])
        self.assertEqual(menu(vue(e, 0)), {
            "Manche": "1 / 5", "À poser": "1 à 4 cartes (entame)", "Dernière combinaison": "—",
        })
        e, _ = President().appliquer(etat_pli([["5S-1", "6S-1"], ["8S-1"], ["7S-1"]]), 0,
                                     {"action": "jouer", "cartes": ["5S-1"]})
        self.assertEqual(menu(vue(e, 2))["À poser"], "1 carte")

    def test_cartes_recues_montrees_au_seul_receveur(self):
        e = echange_en_cours()
        recues = e["recues"][2]
        v = vue(e, 2)
        self.assertEqual(
            menu(v)["Cartes reçues"], " ".join(etiquette_carte(c) for c in recues)
        )
        self.assertNotIn("À poser", menu(v))  # pas pendant l'échange
        for j in (1, 3):
            self.assertNotIn("Cartes reçues", menu(vue(e, j)))
        self.assertIn("Cartes reçues", menu(vue(e, 0)))  # le Vice-président a reçu 1 carte
        self.assertEqual(vue(e, 2)["actions"][0]["libelle"], "Donner au Pauvre")
        self.assertEqual(vue(e, 0)["actions"], [])

    def test_resultat(self):
        e = fin_de_manche(3, [1, 2, 0], manches=2)
        r = vue(e, 0)["resultat"]
        self.assertEqual(r["titre"], "Fin de la manche 1")
        self.assertEqual(r["colonnes"], ["Joueur", "Rang", "Manche 1", "Total"])
        self.assertEqual(r["lignes"], [
            ["Toi", "Pauvre", 0, 0],
            ["Ordinateur 1", "Président", 2, 2],
            ["Ordinateur 2", "Neutre", 1, 1],
        ])
        self.assertIsNone(vue(partie(), 0)["resultat"])

        e["phase"] = "terminee"
        e["points"] = [[0, 2, 1], [2, 1, 0]]
        r = vue(e, 0)["resultat"]
        self.assertEqual(r["titre"], "Fin de la partie — Ordinateur 1 gagne")
        self.assertEqual(r["colonnes"], ["Joueur", "Rang", "Manche 1", "Manche 2", "Total"])
        e["points"] = [[2, 1, 0], [2, 1, 0]]
        self.assertEqual(vue(e, 0)["resultat"]["titre"], "Fin de la partie — Tu gagnes")
        e["points"] = [[2, 1, 0], [0, 1, 2]]
        self.assertEqual(vue(e, 0)["resultat"]["titre"], "Fin de la partie — égalité")

    def test_vue_ne_fuit_rien(self):
        jeu = President()
        for graine in range(1, 41):
            nb = 3 + graine % 5
            options = {"manches": 2, "echanges": True, "deux_ferme": graine % 2 == 0}
            grande = 10**30 + graine  # une graine reconnaissable dans le JSON
            e = jeu.nouvelle_partie(options, nb, grande)
            coups = 0
            while (j := jeu.joueur_actif(e)) is not None:
                self._verifier(e, coups % nb)
                e, _ = jeu.appliquer(e, j, jeu.adversaire(e, j))
                coups += 1
                self.assertLess(coups, 3000, f"graine {graine} : la partie ne finit pas")
            for j in range(nb):
                self._verifier(e, j)

    def _verifier(self, etat, j):
        v = vue(etat, j)
        texte = json.dumps(v, ensure_ascii=False)
        self.assertNotIn("graine", texte)
        self.assertNotIn(str(etat["graine"]), texte)
        vues = chaines(v)
        interdits = {c for k, main in enumerate(etat["mains"]) if k != j for c in main}
        self.assertEqual(interdits & vues, set(), f"phase {etat['phase']}")
        # Témoin : le détecteur voit bien ce qui est montré (sa main, le pli).
        visibles = set(etat["mains"][j]) | set(etat["pli"]["cartes"])
        self.assertEqual(visibles - vues, set(), "le détecteur ne voit pas les cartes visibles")
        # Les cartes reçues par un autre ne sont jamais nommées.
        if not etat["recues"][j]:
            self.assertNotIn("Cartes reçues", texte)
