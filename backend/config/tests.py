from django.conf import settings
from django.test import SimpleTestCase, TestCase


class SanteTests(TestCase):
    def test_sante_ok(self):
        reponse = self.client.get("/health/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.json()["status"], "ok")
        self.assertTrue(reponse.json()["checks"]["db"]["ok"])


class ReglagesTests(SimpleTestCase):
    def test_csrf_lisible_par_angular(self):
        self.assertEqual(settings.CSRF_COOKIE_NAME, "XSRF-TOKEN")
        self.assertEqual(settings.CSRF_HEADER_NAME, "HTTP_X_XSRF_TOKEN")
        self.assertFalse(settings.CSRF_COOKIE_HTTPONLY)

    def test_la_session_dure_autant_que_les_parties(self):
        # La session porte le jeton du joueur : elle ne doit pas expirer avant ses parties,
        # et chaque requête la prolonge.
        self.assertEqual(settings.SESSION_COOKIE_AGE, settings.RETENTION_PARTIES_JOURS * 24 * 3600)
        self.assertEqual(settings.SESSION_COOKIE_AGE, 30 * 24 * 3600)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)
