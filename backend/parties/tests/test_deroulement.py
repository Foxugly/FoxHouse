from django.test import SimpleTestCase

from parties import deroulement
from parties.tests.jeu_factice import Retourner
from rami.jeu import Rami
from rami.tests.test_jeu import SUITE, etat_jouer, partie
from tapis.jeu import CoupRefuse

HUMAIN_MACHINE = [{"type": "humain", "joueur": "a" * 32}, {"type": "machine"}]
MACHINE_HUMAIN = [{"type": "machine"}, {"type": "humain", "joueur": "a" * 32}]
DEUX_HUMAINS = [{"type": "humain", "joueur": "a" * 32}, {"type": "humain", "joueur": "b" * 32}]


class SansFin(Retourner):
    """L'adversaire (siège 1) joue sans jamais rendre la main."""

    def joueur_actif(self, etat):
        return 1

    def appliquer(self, etat, joueur, coup):
        return etat, "Encore."


class Discret(Retourner):
    """Tous les coups sont privés : `appliquer` ne rend pas de message."""

    def appliquer(self, etat, joueur, coup):
        etat, _ = super().appliquer(etat, joueur, coup)
        return etat, None

    def message_prive(self, etat, joueur, coup):
        return "Tu retournes une carte en secret."


class SansFinDiscret(SansFin):
    def appliquer(self, etat, joueur, coup):
        return etat, None


class AdversaireTricheur(Retourner):
    def adversaire(self, etat, joueur):
        return {"action": "tricher"}


class DeroulementTests(SimpleTestCase):
    def setUp(self):
        self.jeu = Retourner()
        self.etat = self.jeu.nouvelle_partie({}, 2, 0)

    def test_jouer_rend_le_coup_humain_puis_celui_de_l_adversaire(self):
        etat, etapes = deroulement.jouer(
            self.jeu, self.etat, HUMAIN_MACHINE, 0, {"action": "retourner"}
        )
        self.assertEqual(len(etapes), 2)
        self.assertEqual(etapes[0]["message"], "Le joueur 0 retourne une carte.")
        self.assertEqual(etapes[1]["message"], "Le joueur 1 retourne une carte.")
        self.assertEqual(self.jeu.joueur_actif(etat), 0)
        # Chaque étape est vue depuis le siège humain.
        self.assertEqual(etapes[1]["vue"]["sieges"][0]["id"], 0)
        self.assertEqual(etapes[1]["vue"]["actions"][0]["id"], "retourner")

    def test_avancer_s_arrete_sur_un_siege_humain(self):
        etat, etapes = deroulement.jouer(
            self.jeu, self.etat, DEUX_HUMAINS, 0, {"action": "retourner"}
        )
        self.assertEqual(len(etapes), 1)
        self.assertEqual(self.jeu.joueur_actif(etat), 1)

    def test_avancer_calcule_les_vues_pour_le_siege_demande(self):
        etat, etapes = deroulement.avancer(self.jeu, self.etat, MACHINE_HUMAIN, pour=1)
        self.assertEqual(len(etapes), 1)
        self.assertEqual(etapes[0]["vue"]["sieges"][0]["id"], 1)
        self.assertEqual(self.jeu.joueur_actif(etat), 1)

    def test_avancer_sans_machine_a_jouer_ne_fait_rien(self):
        etat, etapes = deroulement.avancer(self.jeu, self.etat, HUMAIN_MACHINE, pour=0)
        self.assertEqual(etapes, [])
        self.assertEqual(etat, self.etat)

    def test_avancer_borne_le_nombre_de_coups(self):
        with self.assertRaises(RuntimeError):
            deroulement.avancer(SansFin(), self.etat, HUMAIN_MACHINE, pour=0)

    def test_coup_refuse_de_l_adversaire_est_un_bug(self):
        with self.assertRaises(RuntimeError) as ctx:
            deroulement.jouer(
                AdversaireTricheur(), self.etat, HUMAIN_MACHINE, 0, {"action": "retourner"}
            )
        self.assertNotIsInstance(ctx.exception, CoupRefuse)

    def test_pas_ton_tour(self):
        with self.assertRaisesMessage(CoupRefuse, "Ce n'est pas ton tour."):
            deroulement.jouer(self.jeu, self.etat, DEUX_HUMAINS, 1, {"action": "retourner"})

    def test_partie_terminee(self):
        etat = dict(self.etat, coups=6)
        with self.assertRaisesMessage(CoupRefuse, "La partie est terminée."):
            deroulement.jouer(self.jeu, etat, HUMAIN_MACHINE, 0, {"action": "retourner"})

    def test_coup_prive_de_la_machine_sans_etape(self):
        # Ni le message ni l'existence d'un coup privé n'atteignent les autres joueurs.
        etat, etapes = deroulement.jouer(
            Discret(), self.etat, HUMAIN_MACHINE, 0, {"action": "retourner"}
        )
        self.assertEqual([e["message"] for e in etapes], ["Tu retournes une carte en secret."])
        self.assertEqual(etat["coups"], 2)  # la machine a bien joué
        self.assertEqual(etapes[0]["vue"]["zones"][1]["cartes"][0]["id"], "3S-1")

    def test_message_prive_par_defaut(self):
        class SansMessagePrive(Discret):
            message_prive = Retourner.message_prive

        _, etapes = deroulement.jouer(
            SansMessagePrive(), self.etat, DEUX_HUMAINS, 0, {"action": "retourner"}
        )
        self.assertEqual(etapes[0]["message"], "Coup joué.")

    def test_avancer_borne_aussi_les_coups_prives(self):
        with self.assertRaises(RuntimeError):
            deroulement.avancer(SansFinDiscret(), self.etat, HUMAIN_MACHINE, pour=0)


class BrouillonRamiTests(SimpleTestCase):
    def test_brouillon_de_la_machine_jamais_rejoue(self):
        rami = Rami()
        for graine in range(1, 6):
            with self.subTest(graine=graine):
                e = partie(nb=3, graine=graine, manches=1)
                # La même partie, coup par coup : combien de coups publics, combien de privés ?
                publics = prives = 0
                rejouee = e
                while (j := rami.joueur_actif(rejouee)) is not None:
                    rejouee, message = rami.appliquer(rejouee, j, rami.adversaire(rejouee, j))
                    publics, prives = publics + (message is not None), prives + (message is None)
                self.assertGreater(prives, 0, "aucun brouillon : le test ne prouve rien")
                sieges = [{"type": "machine"}] * 3
                fin, etapes = deroulement.avancer(rami, e, sieges, pour=0)
                self.assertEqual(fin, rejouee)
                self.assertEqual(len(etapes), publics)
                for etape in etapes:
                    self.assertNotIn("attente", etape["message"])
                    self.assertNotIn("reprend", etape["message"])

    def test_le_brouillon_de_l_humain_fait_son_etape(self):
        e = etat_jouer(SUITE + ["2S-2", "3D-1"])
        etat, etapes = deroulement.jouer(
            Rami(), e, HUMAIN_MACHINE, 0, {"action": "poser", "cartes": SUITE}
        )
        self.assertEqual([x["message"] for x in etapes], ["Tu mets une suite en attente."])
        self.assertEqual(len(etat["brouillon"]), 1)
        etat, etapes = deroulement.jouer(Rami(), etat, HUMAIN_MACHINE, 0, {"action": "annuler"})
        self.assertEqual([x["message"] for x in etapes], ["Tu reprends les cartes en attente."])
