from django.test import SimpleTestCase

from tapis import registre
from tapis.jeu import CoupRefuse, Jeu, normaliser_coup
from tapis.options import Option


class JeuBidon(Jeu):
    code = "bidon"
    nom = "Bidon"
    min_joueurs = 2
    max_joueurs = 4

    def options(self):
        return [Option("n", "N", "entier", 1, minimum=0, maximum=2)]

    def nouvelle_partie(self, options, nb_joueurs, graine):
        return {}

    def joueur_actif(self, etat):
        return None

    def appliquer(self, etat, joueur, coup):
        return etat, ""

    def vue(self, etat, joueur):
        return {}

    def adversaire(self, etat, joueur):
        return {"action": "passer", "cartes": [], "cible": None}


class JeuA(JeuBidon):
    code = "a"
    nom = "Zèbre"


class JeuB(JeuBidon):
    code = "b"
    nom = "Abeille"


class TestRegistre(SimpleTestCase):
    def setUp(self):
        self.addCleanup(registre.retirer, "bidon")
        self.addCleanup(registre.retirer, "a")
        self.addCleanup(registre.retirer, "b")

    def test_registre(self):
        jeu = JeuBidon()
        registre.inscrire(jeu)
        with self.assertRaises(ValueError):
            registre.inscrire(JeuBidon())
        self.assertIs(registre.obtenir("bidon"), jeu)
        with self.assertRaises(KeyError):
            registre.obtenir("inconnu")
        registre.retirer("bidon")
        with self.assertRaises(KeyError):
            registre.obtenir("bidon")

    def test_tous_tries_par_nom(self):
        registre.inscrire(JeuA())
        registre.inscrire(JeuB())
        noms = [j.nom for j in registre.tous() if j.code in ("a", "b")]
        self.assertEqual(noms, ["Abeille", "Zèbre"])

    def test_decrire(self):
        d = JeuBidon().decrire()
        self.assertEqual(
            {k: d[k] for k in ("code", "nom", "min_joueurs", "max_joueurs")},
            {"code": "bidon", "nom": "Bidon", "min_joueurs": 2, "max_joueurs": 4},
        )
        self.assertEqual(d["options"][0]["code"], "n")
        self.assertEqual(d["regles"], [])

    def test_abstrait(self):
        with self.assertRaises(TypeError):
            Jeu()


class TestNormaliserCoup(SimpleTestCase):
    def test_defauts(self):
        self.assertEqual(
            normaliser_coup({"action": "x"}), {"action": "x", "cartes": [], "cible": None}
        )

    def test_complet(self):
        c = normaliser_coup({"action": "x", "cartes": ["7H-1"], "cible": "g1"})
        self.assertEqual(c, {"action": "x", "cartes": ["7H-1"], "cible": "g1"})

    def test_formes_mauvaises(self):
        for d in (
            None,
            [],
            {},
            {"action": ""},
            {"action": 3},
            {"action": "x", "cartes": "7H-1"},
            {"action": "x", "cartes": [1]},
            {"action": "x", "cible": 5},
        ):
            with self.assertRaises(CoupRefuse, msg=d):
                normaliser_coup(d)
