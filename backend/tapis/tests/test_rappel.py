from django.test import SimpleTestCase

from tapis import registre

JEUX = ("rami", "huit", "dame", "president", "whist")


class TestRappelDesRegles(SimpleTestCase):
    def test_chaque_jeu_a_ses_regles(self):
        for code in JEUX:
            with self.subTest(code):
                regles = registre.obtenir(code).decrire()["regles"]
                self.assertGreater(len(regles), 0)
                for section in regles:
                    self.assertEqual(set(section), {"titre", "points"})
                    self.assertIsInstance(section["titre"], str)
                    self.assertTrue(section["titre"])
                    self.assertGreater(len(section["points"]), 0)
                    for point in section["points"]:
                        self.assertIsInstance(point, str)
                        self.assertTrue(point.strip())

    def test_les_options_sont_rappelees(self):
        # Chaque jeu termine par une section « Options » ; une option ajoutée sans rappel se voit.
        for code in JEUX:
            with self.subTest(code):
                jeu = registre.obtenir(code)
                options = jeu.decrire()["regles"][-1]
                self.assertEqual(options["titre"], "Options")
                self.assertEqual(len(options["points"]), len(jeu.options()))
