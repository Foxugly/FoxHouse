from django.test import SimpleTestCase

from tapis import cartes


class TestCartes(SimpleTestCase):
    def test_paquet_rami(self):
        p = cartes.paquet(2, 4)
        self.assertEqual(len(p), 108)
        self.assertEqual(len(set(p)), 108)
        self.assertIn("10H-2", p)
        self.assertIn("JK-4", p)

    def test_paquet_ordre_fixe(self):
        self.assertEqual(cartes.paquet(1, 2), cartes.paquet(1, 2))
        self.assertEqual(cartes.paquet(1, 0)[0], "AS-1")
        self.assertEqual(len(cartes.paquet(1, 0)), 52)

    def test_melanger_deterministe(self):
        origine = cartes.paquet(1, 0)
        copie = list(origine)
        a = cartes.melanger(origine, 42)
        b = cartes.melanger(origine, 42)
        self.assertEqual(a, b)
        self.assertEqual(origine, copie)
        self.assertEqual(sorted(a), sorted(origine))
        self.assertNotEqual(a, origine)
        self.assertNotEqual(a, cartes.melanger(origine, 43))

    def test_nature_et_decrire(self):
        self.assertEqual(cartes.nature("10H-2"), "10H")
        self.assertEqual(cartes.valeur("10H-2"), "10")
        self.assertEqual(cartes.enseigne("10H-2"), "H")
        self.assertEqual(cartes.valeur("AS-1"), "A")
        self.assertEqual(cartes.decrire("JK-1"), {"id": "JK-1", "joker": True})
        self.assertEqual(
            cartes.decrire("10H-2"), {"id": "10H-2", "valeur": "10", "enseigne": "H"}
        )
        self.assertTrue(cartes.est_joker("JK-3"))
        self.assertFalse(cartes.est_joker("KS-1"))
        self.assertEqual(cartes.CACHEE, {"cachee": True})

    def test_ids_inconnus(self):
        for mauvais in ("ZZ-9", "", "10H", "1H-1", "10X-1", "JK", "AS-x", None, 5):
            self.assertFalse(cartes.est_carte(mauvais), mauvais)
            with self.assertRaises(ValueError):
                cartes.decrire(mauvais)
        for f in (cartes.valeur, cartes.enseigne, cartes.nature):
            with self.assertRaises(ValueError):
                f("ZZ-9")
        self.assertTrue(cartes.est_carte("JK-1"))
        self.assertTrue(cartes.est_carte("10H-2"))
        self.assertTrue(all(cartes.est_carte(c) for c in cartes.paquet(2, 4)))
