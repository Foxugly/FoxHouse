import copy

from django.test import SimpleTestCase

from tapis.vue import VueInvalide, valider_vue


def vue_minimale():
    return {
        "schema": 1,
        "jeu": "rami",
        "version": 0,
        "terminee": False,
        "sieges": [
            {
                "id": 0, "nom": "Toi", "actif": True,
                "compteurs": [{"libelle": "Cartes", "valeur": 14}],
            },
            {"id": 1, "nom": "Ordinateur 1", "actif": False, "compteurs": []},
        ],
        "zones": [
            {
                "id": "main", "type": "main", "siege": 0, "libelle": "Ta main",
                "cartes": [
                    {"id": "7H-1", "valeur": "7", "enseigne": "H"},
                    {"id": "JK-1", "joker": True},
                    {"id": "JK-2", "joker": True, "represente": "8H"},
                ],
                "nombre": None, "groupes": [],
            },
            {
                "id": "pioche", "type": "pile", "siege": None, "libelle": "Pioche",
                "cartes": [{"cachee": True}], "nombre": 50, "groupes": [],
            },
            {
                "id": "table", "type": "combinaisons", "siege": None, "libelle": "Table",
                "cartes": [], "nombre": None,
                "groupes": [
                    {
                        "id": "g1",
                        "cartes": [{"id": "7H-1", "valeur": "7", "enseigne": "H"}],
                        "provisoire": False, "ciblable": True,
                    },
                ],
            },
        ],
        "menu": [{"libelle": "Manche", "valeur": 1}],
        "actions": [
            {"id": "defausser", "libelle": "Défausser", "cartes_min": 1, "cartes_max": 1,
             "cible": None},
            {"id": "ajouter", "libelle": "Ajouter", "cartes_min": 1, "cartes_max": 3,
             "cible": "groupe"},
        ],
        "resultat": None,
    }


class TestVue(SimpleTestCase):
    def test_vue_valide(self):
        valider_vue(vue_minimale())

    def test_regardeur_n_est_pas_forcement_le_siege_0(self):
        v = vue_minimale()
        v["sieges"][0]["id"] = 2
        v["sieges"][1]["id"] = 3
        v["zones"][0]["siege"] = 2
        valider_vue(v)

    def test_resultat_valide(self):
        v = vue_minimale()
        v["resultat"] = {"titre": "Fin", "colonnes": ["Joueur", "Points"], "lignes": [["Toi", 0]]}
        valider_vue(v)

    def _refuse(self, modif):
        v = copy.deepcopy(vue_minimale())
        modif(v)
        with self.assertRaises(VueInvalide):
            valider_vue(v)

    def test_vue_invalide(self):
        self._refuse(lambda v: v["zones"][0].update(type="truc"))
        self._refuse(lambda v: v["zones"][0].update(siege=9))
        self._refuse(
            lambda v: v["zones"][1]["cartes"].__setitem__(0, {"cachee": True, "id": "7H-1"})
        )
        self._refuse(lambda v: v["zones"][2]["groupes"].append(dict(v["zones"][2]["groupes"][0])))

    def test_autres_invalides(self):
        self._refuse(lambda v: v.update(schema=2))
        self._refuse(lambda v: v.pop("menu"))
        self._refuse(lambda v: v["sieges"].clear())
        self._refuse(lambda v: v["sieges"][1].update(id=0))
        self._refuse(lambda v: v["zones"].append(dict(v["zones"][0])))
        self._refuse(
            lambda v: v["zones"][0]["cartes"].append(
                {"id": "ZZ-9", "valeur": "Z", "enseigne": "Q"}
            )
        )
        self._refuse(lambda v: v["zones"][0]["cartes"].append({"id": "7H-1"}))
        self._refuse(lambda v: v["actions"][0].update(cible="autre"))
        self._refuse(lambda v: v["actions"][1].update(cartes_min=5))
        self._refuse(lambda v: v.update(resultat={"titre": "x"}))
        self._refuse(lambda v: v.update(terminee="non"))
        self._refuse(
            lambda v: v["zones"][0]["cartes"].append(
                {"id": "JK-3", "joker": True, "represente": 5}
            )
        )
