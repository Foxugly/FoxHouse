import json
import re

from django.test import SimpleTestCase

from rami.jeu import Rami
from rami.tests.test_jeu import BRELAN, SUITE, etat_jouer, etat_ouvert, partie
from rami.vue import vue
from tapis.vue import valider_vue


_RE_CHAINE = re.compile(r'"([^"\\]*)"')


def zone(v, zid):
    return next(z for z in v["zones"] if z["id"] == zid)


def menu(v):
    return {m["libelle"]: m["valeur"] for m in v["menu"]}


def ids_interdits(etat, j):
    """Les cartes que le joueur j ne doit jamais voir."""
    interdits = set(etat["pioche"])
    for k, main in enumerate(etat["mains"]):
        if k != j:
            interdits |= set(main)
    if etat["actif"] != j:
        for comb in etat["brouillon"]:
            interdits |= set(comb["cartes"])
    return interdits


class VueTests(SimpleTestCase):
    def test_vue_conforme(self):
        rami = Rami()
        e = partie(nb=3, manches=2)
        valider_vue(vue(e, 0))

        e = etat_jouer(SUITE + BRELAN + ["2S-2"])
        e, _ = rami.appliquer(e, 0, {"action": "poser", "cartes": SUITE})
        valider_vue(vue(e, 0))
        valider_vue(vue(e, 1))

        e = partie(manches=2)
        e["pioche"], e["reconstitutions"] = [], 3
        e, _ = rami.appliquer(e, 0, {"action": "piocher"})
        self.assertEqual(e["phase"], "fin_manche")
        valider_vue(vue(e, 0))

        e = partie(manches=1)
        e["pioche"], e["reconstitutions"] = [], 3
        e, _ = rami.appliquer(e, 0, {"action": "piocher"})
        self.assertEqual(e["phase"], "terminee")
        v = vue(e, 0)
        valider_vue(v)
        self.assertTrue(v["terminee"])
        self.assertEqual(v["actions"], [])

    def test_vue_par_le_jeu(self):
        e = partie()
        self.assertEqual(Rami().vue(e, 0), vue(e, 0))

    def test_sieges_et_compteurs(self):
        e = partie(nb=4)
        e["penalites"] = [[10, 0, 5, 3], [2, 7, 0, 1]]
        v = vue(e, 2)
        self.assertEqual([s["id"] for s in v["sieges"]], [2, 3, 0, 1])
        self.assertEqual(
            [s["nom"] for s in v["sieges"]], ["Ordinateur 2", "Ordinateur 3", "Toi", "Ordinateur 1"]
        )
        self.assertEqual([s["actif"] for s in v["sieges"]], [False, False, True, False])
        self.assertEqual(
            v["sieges"][2]["compteurs"],
            [{"libelle": "Cartes", "valeur": 13}, {"libelle": "Pénalités", "valeur": 12}],
        )

    def test_brouillon_compte_dans_les_cartes(self):
        rami = Rami()
        e = etat_jouer(SUITE + BRELAN + ["2S-2"])
        e, _ = rami.appliquer(e, 0, {"action": "poser", "cartes": SUITE})
        v = vue(e, 1)
        moi = next(s for s in v["sieges"] if s["id"] == 0)
        self.assertEqual(moi["compteurs"][0]["valeur"], 7)
        self.assertEqual(zone(v, "main-0")["cartes"], [{"cachee": True}] * 7)

    def test_zones(self):
        e = partie(nb=3)
        v = vue(e, 0)
        main = zone(v, "main-0")
        self.assertEqual((main["type"], main["siege"]), ("main", 0))
        self.assertEqual([c["id"] for c in main["cartes"]], e["mains"][0])
        self.assertEqual(zone(v, "main-1")["cartes"], [{"cachee": True}] * 13)
        pioche = zone(v, "pioche")
        self.assertEqual((pioche["type"], pioche["nombre"], pioche["cartes"]),
                         ("pile", len(e["pioche"]), []))
        defausse = zone(v, "defausse")
        self.assertEqual(defausse["nombre"], 1)
        self.assertEqual([c["id"] for c in defausse["cartes"]], [e["defausse"][-1]])
        self.assertEqual(zone(v, "table")["type"], "combinaisons")

    def test_table_et_brouillon(self):
        rami = Rami()
        e = etat_ouvert(["2S-2", "5S-1"])
        e["ouvert"][0] = False
        e["mains"][0] += BRELAN
        e, _ = rami.appliquer(e, 0, {"action": "poser", "cartes": BRELAN})
        groupes = zone(vue(e, 0), "table")["groupes"]
        self.assertEqual([g["id"] for g in groupes], ["g1", "g2", "b0"])
        self.assertEqual([g["provisoire"] for g in groupes], [False, False, True])
        self.assertEqual([g["ciblable"] for g in groupes], [False, False, False])
        self.assertIn({"id": "JK-1", "joker": True, "represente": "5S"}, groupes[1]["cartes"])
        self.assertEqual(menu(vue(e, 0))["Points en attente"], 27)
        self.assertEqual(menu(vue(e, 0))["Ouverture"], "pas encore")

        # Les autres ne voient ni le brouillon ni son total.
        v1 = vue(e, 1)
        self.assertEqual([g["id"] for g in zone(v1, "table")["groupes"]], ["g1", "g2"])
        self.assertNotIn("Points en attente", menu(v1))

        e = etat_ouvert(["2S-2", "5S-1"])
        v = vue(e, 0)
        self.assertEqual([g["ciblable"] for g in zone(v, "table")["groupes"]], [True, True])
        self.assertEqual(menu(v), {"Manche": "1 / 5", "Ouverture": "faite"})
        # Hors de son tour, rien n'est ciblable.
        self.assertEqual(
            [g["ciblable"] for g in zone(vue(e, 1), "table")["groupes"]], [False, False]
        )

    def test_resultat(self):
        rami = Rami()
        e = partie(nb=2, manches=2)
        self.assertIsNone(vue(e, 0)["resultat"])
        e["pioche"], e["reconstitutions"] = [], 3
        e, _ = rami.appliquer(e, 0, {"action": "piocher"})
        r = vue(e, 0)["resultat"]
        self.assertEqual(r["titre"], "Fin de la manche 1")
        self.assertEqual(r["colonnes"], ["Joueur", "Manche 1", "Total"])
        self.assertEqual([ligne[0] for ligne in r["lignes"]], ["Toi", "Ordinateur 1"])
        self.assertEqual(r["lignes"][0][1], r["lignes"][0][2])

        e["phase"] = "terminee"
        e["penalites"] = [[10, 40], [30, 5]]
        r = vue(e, 0)["resultat"]
        self.assertEqual(r["titre"], "Fin de la partie — Tu gagnes")
        self.assertEqual(r["colonnes"], ["Joueur", "Manche 1", "Manche 2", "Total"])
        self.assertEqual(r["lignes"], [["Toi", 10, 30, 40], ["Ordinateur 1", 40, 5, 45]])

        e["penalites"] = [[40, 10], [30, 5]]
        r = vue(e, 0)["resultat"]
        self.assertEqual(r["titre"], "Fin de la partie — Ordinateur 1 gagne")
        e["penalites"] = [[10, 10]]
        self.assertEqual(vue(e, 0)["resultat"]["titre"], "Fin de la partie — égalité")

    def test_vue_ne_fuit_rien(self):
        rami = Rami()
        for graine in range(1, 31):
            nb = 2 + graine % 5
            e = partie(nb=nb, graine=graine, manches=2)
            etats = 0
            while rami.joueur_actif(e) is not None:
                self._verifier(e)
                j = rami.joueur_actif(e)
                if e["phase"] == "piocher":
                    coup = {"action": "piocher"}
                elif e["phase"] == "jouer":
                    coup = {"action": "defausser", "cartes": [e["mains"][j][0]]}
                else:
                    coup = {"action": "manche_suivante"}
                e, _ = rami.appliquer(e, j, coup)
                etats += 1
                self.assertLess(etats, 5000, f"graine {graine} : la partie ne finit pas")
            self._verifier(e)
            self.assertEqual(len(e["penalites"]), 2)

    def _verifier(self, etat):
        texte = json.dumps(vue(etat, 0))
        self.assertNotIn("graine", texte)
        fuites = ids_interdits(etat, 0) & set(_RE_CHAINE.findall(texte))
        self.assertEqual(fuites, set(), f"phase {etat['phase']}")
