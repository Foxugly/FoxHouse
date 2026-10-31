"""Garde les vues d'exemple du frontend conformes au schéma de la vue."""

import json
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from tapis.vue import valider_vue

DOSSIER = Path(settings.BASE_DIR).parent / "frontend" / "src" / "testing" / "vues"


class VuesDuFrontendTests(SimpleTestCase):
    def test_le_dossier_n_est_pas_vide(self):
        self.assertTrue(list(DOSSIER.glob("*.json")), f"aucune vue d'exemple dans {DOSSIER}")

    def test_chaque_vue_d_exemple_respecte_le_schema(self):
        for fichier in sorted(DOSSIER.glob("*.json")):
            with self.subTest(fichier=fichier.name):
                valider_vue(json.loads(fichier.read_text(encoding="utf-8")))
