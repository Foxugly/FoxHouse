from django.test import SimpleTestCase

from rami.combinaisons import (
    Combinaison,
    ajouter,
    analyser,
    depuis_dict,
    penalite,
    points,
    recuperer_joker,
    vers_dict,
)

BAS1_HAUT11 = "bas1_haut11"


def ids(texte: str) -> list[str]:
    """« 7H 8H JK » -> ["7H-1", "8H-1", "JK-1"] ; un id complet reste tel quel."""
    return [c if "-" in c else f"{c}-1" for c in texte.split()]


class TestSuites(SimpleTestCase):
    def test_suites_valides(self):
        for texte in ("7H 8H 9H", "AS 2S 3S", "QD KD AD"):
            with self.subTest(texte):
                comb = analyser(ids(texte))
                self.assertEqual(comb, Combinaison("suite", tuple(ids(texte)), ()))

    def test_ordre_quelconque_rendu_du_bas_vers_le_haut(self):
        comb = analyser(ids("9H 7H 8H"))
        self.assertEqual(comb.cartes, tuple(ids("7H 8H 9H")))
        comb = analyser(ids("AD QD KD"))
        self.assertEqual(comb.cartes, tuple(ids("QD KD AD")))

    def test_joker_en_haut(self):
        comb = analyser(ids("5C 6C JK"))
        self.assertEqual(comb.type, "suite")
        self.assertEqual(comb.cartes, tuple(ids("5C 6C JK")))
        self.assertEqual(comb.jokers, (("JK-1", "7C"),))

    def test_joker_en_bas_quand_rien_au_dessus(self):
        comb = analyser(ids("QC KC JK"))
        self.assertEqual(comb.cartes, tuple(ids("JK QC KC")))
        self.assertEqual(comb.jokers, (("JK-1", "JC"),))

    def test_joker_dans_un_trou(self):
        comb = analyser(ids("4H JK 6H"))
        self.assertEqual(comb.cartes, tuple(ids("4H JK 6H")))
        self.assertEqual(comb.jokers, (("JK-1", "5H"),))

    def test_suites_refusees(self):
        for texte in (
            "KS AS 2S",
            "7H 8H",
            "7H 8H 9S",
            "7H 7H-2 8H",
            "5C JK-1 JK-2",
            "JK-1 JK-2 JK-3",
            "4H JK 7H",
        ):
            with self.subTest(texte):
                self.assertIsNone(analyser(ids(texte)))

    def test_quatorze_cartes_refusees(self):
        cartes = [f"{v}S-1" for v in ("A 2 3 4 5 6 7 8 9 10 J Q K".split())]
        self.assertIsNotNone(analyser(cartes))
        self.assertIsNone(analyser(cartes + ["AS-2"]))

    def test_as_en_haut_douze_cartes(self):
        cartes = [f"{v}S-1" for v in ("3 4 5 6 7 8 9 10 J Q K A".split())]
        self.assertEqual(analyser(list(reversed(cartes))).cartes, tuple(cartes))

    def test_suite_complete_lue_as_en_bas(self):
        # As..roi se lit dans les deux sens ; la lecture « as en bas » l'emporte.
        cartes = [f"{v}S-1" for v in ("K Q J 10 9 8 7 6 5 4 3 2 A".split())]
        self.assertEqual(analyser(cartes).cartes[0], "AS-1")

    def test_carte_inconnue_ou_en_double(self):
        self.assertIsNone(analyser(["7H-1", "8H-1", "XX-1"]))
        self.assertIsNone(analyser(["7H-1", "8H-1", "8H-1"]))


class TestBrelans(SimpleTestCase):
    def test_brelan_valide(self):
        comb = analyser(ids("9C 9S 9D"))
        self.assertEqual(comb, Combinaison("brelan", tuple(ids("9S 9D 9C")), ()))

    def test_meme_enseigne_refusee(self):
        self.assertIsNone(analyser(ids("9S 9S-2 9D")))

    def test_joker_dans_un_brelan(self):
        comb = analyser(ids("KH KS JK"))
        self.assertEqual(comb.type, "brelan")
        self.assertEqual(comb.cartes, tuple(ids("KS KH JK")))
        self.assertEqual(comb.jokers, (("JK-1", "K*"),))

    def test_joker_dans_un_carre(self):
        comb = analyser(ids("KH KS KD JK"))
        self.assertEqual(comb.type, "brelan")
        self.assertEqual(comb.jokers, (("JK-1", "KC"),))
        self.assertEqual(comb.cartes, tuple(ids("KS KH KD JK")))

    def test_carre_sans_joker(self):
        self.assertEqual(analyser(ids("7C 7D 7H 7S")).cartes, tuple(ids("7S 7H 7D 7C")))

    def test_cinq_cartes_refusees(self):
        self.assertIsNone(analyser(ids("9S 9H 9D 9C 9S-2")))
        self.assertIsNone(analyser(ids("9S 9H 9D 9C JK")))


class TestPoints(SimpleTestCase):
    def test_exemples_de_la_spec(self):
        self.assertEqual(points(analyser(ids("7H 8H 9H")), BAS1_HAUT11), 24)
        self.assertEqual(points(analyser(ids("9S 9D 9C")), BAS1_HAUT11), 27)
        self.assertEqual(points(analyser(ids("AS 2S 3S")), BAS1_HAUT11), 6)
        self.assertEqual(points(analyser(ids("QD KD AD")), BAS1_HAUT11), 31)
        self.assertEqual(points(analyser(ids("AS AH AD")), "toujours1"), 3)

    def test_regles_de_l_as(self):
        self.assertEqual(points(analyser(ids("AS AH AD")), BAS1_HAUT11), 33)
        self.assertEqual(points(analyser(ids("AS 2S 3S")), "toujours11"), 16)
        self.assertEqual(points(analyser(ids("QD KD AD")), "toujours1"), 21)

    def test_joker_vaut_la_carte_representee(self):
        self.assertEqual(points(analyser(ids("5C 6C JK")), BAS1_HAUT11), 18)
        self.assertEqual(points(analyser(ids("KH KS JK")), BAS1_HAUT11), 30)
        self.assertEqual(points(analyser(ids("QC KC JK")), BAS1_HAUT11), 30)

    def test_regle_inconnue(self):
        with self.assertRaises(ValueError):
            points(analyser(ids("AS 2S 3S")), "nimporte")


class TestAjouter(SimpleTestCase):
    def test_ajout_au_bout(self):
        comb = ajouter(analyser(ids("5C 6C JK")), ["8C-1"])
        self.assertEqual(comb.cartes, tuple(ids("5C 6C JK 8C")))
        self.assertEqual(comb.jokers, (("JK-1", "7C"),))

    def test_le_joker_ne_se_deplace_pas(self):
        self.assertIsNone(ajouter(analyser(ids("5C 6C JK")), ["7C-1"]))

    def test_ajout_par_le_bas(self):
        comb = ajouter(analyser(ids("5C 6C JK")), ["4C-2"])
        self.assertEqual(comb.cartes, ("4C-2", "5C-1", "6C-1", "JK-1"))

    def test_brelan_devient_carre(self):
        comb = ajouter(analyser(ids("KH KS JK")), ["KD-1"])
        self.assertEqual(comb.type, "brelan")
        self.assertEqual(comb.jokers, (("JK-1", "KC"),))

    def test_brelan_enseigne_deja_presente(self):
        self.assertIsNone(ajouter(analyser(ids("KH KS JK")), ["KH-2"]))

    def test_joker_fixe_incompatible(self):
        self.assertIsNone(analyser(ids("5C 6C JK"), {"JK-1": "8C"}))
        self.assertIsNone(analyser(ids("KH KS JK"), {"JK-1": "Q*"}))
        self.assertIsNone(analyser(ids("4C 5C JK"), {"JK-1": "K*"}))


class TestRecupererJoker(SimpleTestCase):
    def test_carte_exacte(self):
        resultat = recuperer_joker(analyser(ids("5C 6C JK")), "7C-2")
        self.assertEqual(resultat, (Combinaison("suite", ("5C-1", "6C-1", "7C-2"), ()), "JK-1"))

    def test_mauvaise_carte(self):
        self.assertIsNone(recuperer_joker(analyser(ids("5C 6C JK")), "8C-1"))

    def test_roi_d_une_enseigne_absente(self):
        comb, joker = recuperer_joker(analyser(ids("KH KS JK")), "KC-1")
        self.assertEqual(joker, "JK-1")
        self.assertEqual(comb.cartes, tuple(ids("KS KH KC")))
        self.assertEqual(comb.jokers, ())

    def test_roi_d_une_enseigne_presente(self):
        self.assertIsNone(recuperer_joker(analyser(ids("KH KS JK")), "KH-2"))

    def test_sans_joker(self):
        self.assertIsNone(recuperer_joker(analyser(ids("7H 8H 9H")), "7H-2"))


class TestPenalite(SimpleTestCase):
    def test_penalites(self):
        self.assertEqual(penalite("AS-1", BAS1_HAUT11, 20), 11)
        self.assertEqual(penalite("AS-1", "toujours1", 20), 1)
        self.assertEqual(penalite("AS-1", "toujours11", 20), 11)
        self.assertEqual(penalite("JK-2", BAS1_HAUT11, 20), 20)
        self.assertEqual(penalite("QH-1", BAS1_HAUT11, 20), 10)
        self.assertEqual(penalite("7D-2", BAS1_HAUT11, 20), 7)


class TestDict(SimpleTestCase):
    def test_aller_retour(self):
        for texte in ("7H 8H 9H", "5C 6C JK", "KH KS JK"):
            with self.subTest(texte):
                comb = analyser(ids(texte))
                self.assertEqual(depuis_dict(vers_dict(comb)), comb)

    def test_dict_json(self):
        import json

        d = vers_dict(analyser(ids("5C 6C JK")))
        self.assertEqual(json.loads(json.dumps(d)), d)
        self.assertEqual(
            d, {"type": "suite", "cartes": ["5C-1", "6C-1", "JK-1"], "jokers": {"JK-1": "7C"}}
        )

    def test_hachable(self):
        self.assertEqual(len({analyser(ids("5C 6C JK")), analyser(ids("5C 6C JK"))}), 1)
