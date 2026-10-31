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
