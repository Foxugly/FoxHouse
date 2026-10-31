import json
import logging
from unittest import mock

from django.test import Client, TestCase

from parties.models import Partie
from parties.tests.jeu_factice import AvecFactice
from tapis.vue import valider_vue


class ApiTests(AvecFactice, TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Les 4xx attendus ne doivent pas encombrer la sortie des tests.
        cls.journaux = [logging.getLogger(n) for n in ("django.request", "django.security.csrf")]
        cls.niveaux = [j.level for j in cls.journaux]
        for journal in cls.journaux:
            journal.setLevel(logging.ERROR)

    @classmethod
    def tearDownClass(cls):
        for journal, niveau in zip(cls.journaux, cls.niveaux):
            journal.setLevel(niveau)
        super().tearDownClass()

    def creer(self, client=None, **corps):
        corps = {"jeu": "factice", "nb_joueurs": 2, "options": {}} | corps
        return (client or self.client).post(
            "/api/parties/", json.dumps(corps), content_type="application/json"
        )

    def agir(self, pk, version, client=None, **coup):
        coup = {"action": "retourner", "cartes": [], "cible": None} | coup
        return (client or self.client).post(
            f"/api/parties/{pk}/actions/",
            json.dumps({"version": version} | coup),
            content_type="application/json",
        )

    def test_liste_des_jeux(self):
        reponse = self.client.get("/api/jeux/")
        self.assertEqual(reponse.status_code, 200)
        codes = [j["code"] for j in reponse.json()]
        self.assertIn("rami", codes)
        self.assertIn("factice", codes)
        self.assertIn("XSRF-TOKEN", reponse.cookies)

    def test_creer_et_jouer_factice(self):
        reponse = self.creer()
        self.assertEqual(reponse.status_code, 201)
        donnees = reponse.json()
        self.assertEqual(donnees["etapes"], [])
        self.assertEqual(donnees["vue"]["version"], 0)
        valider_vue(donnees["vue"])
        pk = donnees["id"]
        for version in range(3):
            reponse = self.agir(pk, version)
            self.assertEqual(reponse.status_code, 200, reponse.content)
            donnees = reponse.json()
            self.assertEqual(len(donnees["etapes"]), 2)
            self.assertEqual(donnees["vue"]["version"], version + 1)
            for etape in donnees["etapes"]:
                valider_vue(etape["vue"])
        self.assertTrue(donnees["vue"]["terminee"])
        self.assertTrue(Partie.objects.get(pk=pk).terminee)
        reponse = self.agir(pk, 3)
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(reponse.json()["erreur"], "La partie est terminée.")
        self.assertIn("vue", reponse.json())

    def test_coup_refuse_400(self):
        pk = self.creer().json()["id"]
        reponse = self.agir(pk, 0, action="tricher")
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(reponse.json()["erreur"], "Action impossible maintenant.")
        self.assertEqual(reponse.json()["vue"]["version"], 0)
        self.assertEqual(Partie.objects.get(pk=pk).version, 0)

    def test_creer_rami_avec_options(self):
        reponse = self.creer(jeu="rami", nb_joueurs=4, options={"manches": 2})
        self.assertEqual(reponse.status_code, 201, reponse.content)
        donnees = reponse.json()
        self.assertEqual(len(donnees["vue"]["sieges"]), 4)
        valider_vue(donnees["vue"])
        for etape in donnees["etapes"]:
            valider_vue(etape["vue"])
        partie = Partie.objects.get(pk=donnees["id"])
        self.assertEqual([s["type"] for s in partie.sieges],
                         ["humain", "machine", "machine", "machine"])
        self.assertEqual(partie.etat["options"]["manches"], 2)

    def test_options_invalides_400(self):
        reponse = self.creer(jeu="rami", nb_joueurs=2, options={"manches": "beaucoup"})
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("erreur", reponse.json())
        reponse = self.creer(jeu="rami", nb_joueurs=2, options={"inconnue": 1})
        self.assertEqual(reponse.status_code, 400)
        self.assertFalse(Partie.objects.exists())

    def test_nb_joueurs_hors_bornes_400(self):
        for nb in (1, 7, "3", True, None):
            reponse = self.creer(jeu="rami", nb_joueurs=nb)
            self.assertEqual(reponse.status_code, 400, nb)
            self.assertIn("erreur", reponse.json())
        self.assertFalse(Partie.objects.exists())

    def test_jeu_inconnu_400(self):
        reponse = self.creer(jeu="belote")
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(reponse.json()["erreur"], "Jeu inconnu.")

    def test_partie_d_un_autre_joueur_404(self):
        pk = self.creer().json()["id"]
        autre = Client()
        self.assertEqual(autre.get(f"/api/parties/{pk}/").status_code, 404)
        self.assertEqual(self.agir(pk, 0, client=autre).status_code, 404)
        self.creer(client=autre)
        reponse = autre.get(f"/api/parties/{pk}/")
        self.assertEqual(reponse.status_code, 404)
        self.assertIn("erreur", reponse.json())
        self.assertEqual(self.client.get(f"/api/parties/{pk}/").status_code, 200)

    def test_partie_inconnue_404(self):
        self.creer()
        reponse = self.client.get("/api/parties/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(reponse.status_code, 404)

    def test_detail(self):
        pk = self.creer().json()["id"]
        self.agir(pk, 0)
        reponse = self.client.get(f"/api/parties/{pk}/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.json()["id"], pk)
        self.assertEqual(reponse.json()["vue"]["version"], 1)

    def test_version_perimee_409(self):
        pk = self.creer().json()["id"]
        self.assertEqual(self.agir(pk, 0).status_code, 200)
        reponse = self.agir(pk, 0)
        self.assertEqual(reponse.status_code, 409)
        self.assertIn("erreur", reponse.json())
        self.assertEqual(reponse.json()["vue"]["version"], 1)
        self.assertEqual(Partie.objects.get(pk=pk).version, 1)

    def test_json_illisible_400(self):
        reponse = self.client.post("/api/parties/", "{", content_type="application/json")
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("erreur", reponse.json())
        pk = self.creer().json()["id"]
        reponse = self.client.post(
            f"/api/parties/{pk}/actions/", "{", content_type="application/json"
        )
        self.assertEqual(reponse.status_code, 400)

    def test_json_trop_imbrique_400(self):
        corps = "[" * 100_000 + "]" * 100_000
        for url in ("/api/parties/", f"/api/parties/{self.creer().json()['id']}/actions/"):
            with self.subTest(url=url):
                reponse = self.client.post(url, corps, content_type="application/json")
                self.assertEqual(reponse.status_code, 400)
                self.assertEqual(
                    reponse.json()["erreur"], "Le corps de la requête n'est pas du JSON valide."
                )

    def test_graine_de_128_bits(self):
        graine = (1 << 128) - 1
        with mock.patch("parties.views.secrets.randbits", return_value=graine) as tirage:
            reponse = self.creer(jeu="rami")
        tirage.assert_called_once_with(128)
        self.assertEqual(reponse.status_code, 201)
        pk = reponse.json()["id"]
        self.assertEqual(Partie.objects.get(pk=pk).etat["graine"], graine)
        reponse = self.agir(pk, 0, action="piocher")
        self.assertEqual(reponse.status_code, 200, reponse.content)
        self.assertEqual(Partie.objects.get(pk=pk).etat["graine"], graine)
        self.assertNotIn(str(graine), reponse.content.decode())

    def test_version_manquante_400(self):
        pk = self.creer().json()["id"]
        reponse = self.client.post(
            f"/api/parties/{pk}/actions/", json.dumps({"action": "retourner"}),
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(Partie.objects.get(pk=pk).version, 0)

    def test_courante_204_puis_200(self):
        self.assertEqual(self.client.get("/api/parties/courante/").status_code, 204)
        pk = self.creer().json()["id"]
        reponse = self.client.get("/api/parties/courante/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.json()["id"], pk)
        self.assertEqual(reponse.json()["vue"]["version"], 0)
        self.assertIn("XSRF-TOKEN", reponse.cookies)

    def test_nouvelle_partie_remplace_l_ancienne(self):
        ancienne = self.creer().json()["id"]
        nouvelle = self.creer().json()["id"]
        self.assertNotEqual(ancienne, nouvelle)
        self.assertEqual(Partie.objects.count(), 1)
        self.assertEqual(str(Partie.objects.get().pk), nouvelle)
        self.assertEqual(self.client.get(f"/api/parties/{ancienne}/").status_code, 404)

    def test_methode_non_permise_405(self):
        reponse = self.client.get("/api/parties/")
        self.assertEqual(reponse.status_code, 405)
        self.assertIn("erreur", reponse.json())

    def test_csrf_exige(self):
        client = Client(enforce_csrf_checks=True)
        corps = json.dumps({"jeu": "factice", "nb_joueurs": 2, "options": {}})
        reponse = client.post("/api/parties/", corps, content_type="application/json")
        self.assertEqual(reponse.status_code, 403)
        self.assertIn("erreur", reponse.json())
        jeton = client.get("/api/jeux/").cookies["XSRF-TOKEN"].value
        reponse = client.post(
            "/api/parties/", corps, content_type="application/json", HTTP_X_XSRF_TOKEN=jeton
        )
        self.assertEqual(reponse.status_code, 201)
