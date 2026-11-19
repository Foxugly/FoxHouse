"""La 2FA de l'administration (admin_2fa/) ne change rien pour l'API ni pour /health/.

Le jeu se joue sans compte : l'API doit répondre pareil au joueur anonyme et à un
membre de l'équipe connecté par mot de passe seul (second facteur non donné),
enrôlé ou non.
"""

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django_otp.plugins.otp_totp.models import TOTPDevice

from parties.tests.jeu_factice import AvecFactice


class ApiInchangeeTests(AvecFactice, TestCase):
    def clients(self):
        yield "anonyme", Client()
        for enrole in (False, True):
            membre = get_user_model().objects.create_user(
                email=f"equipe-{enrole}@example.com", password="sup3rSecret!", is_staff=True
            )
            if enrole:
                TOTPDevice.objects.create(user=membre, name="admin-2fa", confirmed=True)
            client = Client()
            client.force_login(membre)  # mot de passe seul : session non vérifiée
            yield f"équipe (enrôlé={enrole})", client

    def test_l_api_repond_sans_second_facteur(self):
        for nom, client in self.clients():
            with self.subTest(nom):
                self.assertEqual(client.get("/api/jeux/").status_code, 200)
                corps = {"jeu": "factice", "nb_joueurs": 2, "options": {}}
                reponse = client.post("/api/parties/", json.dumps(corps), content_type="application/json")
                self.assertEqual(reponse.status_code, 201, reponse.content)
                pk = reponse.json()["id"]
                self.assertEqual(client.get(f"/api/parties/{pk}/").status_code, 200)
                self.assertEqual(client.get("/api/parties/courante/").status_code, 200)

    def test_sante_reste_publique(self):
        self.assertEqual(Client().get("/health/").status_code, 200)
