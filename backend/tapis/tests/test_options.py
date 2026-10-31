from django.test import SimpleTestCase

from tapis.options import Option, OptionsInvalides, valider

OPTIONS = [
    Option("mode", "Mode", "choix", "a", choix=(("a", "A"), ("b", "B"))),
    Option("aide", "Aide", "booleen", True),
    Option("manches", "Manches", "entier", 3, minimum=1, maximum=5),
]


class TestOptions(SimpleTestCase):
    def test_defauts(self):
        self.assertEqual(valider(OPTIONS, {}), {"mode": "a", "aide": True, "manches": 3})

    def test_valeurs_valides(self):
        r = valider(OPTIONS, {"mode": "b", "aide": False, "manches": 5})
        self.assertEqual(r, {"mode": "b", "aide": False, "manches": 5})

    def test_refus(self):
        for donnees in (
            {"inconnue": 1},
            {"manches": 0},
            {"manches": 6},
            {"manches": "3"},
            {"manches": True},
            {"aide": "true"},
            {"aide": 1},
            {"mode": "c"},
        ):
            with self.assertRaises(OptionsInvalides, msg=donnees):
                valider(OPTIONS, donnees)

    def test_donnees_pas_un_dict(self):
        with self.assertRaises(OptionsInvalides):
            valider(OPTIONS, [])

    def test_decrire(self):
        d = OPTIONS[0].decrire()
        self.assertEqual(d["code"], "mode")
        self.assertEqual(d["type"], "choix")
        self.assertEqual(
            d["choix"], [{"valeur": "a", "libelle": "A"}, {"valeur": "b", "libelle": "B"}]
        )
        e = OPTIONS[2].decrire()
        self.assertEqual((e["minimum"], e["maximum"], e["defaut"]), (1, 5, 3))
