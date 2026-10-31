"""Garde-fous de la mise en production, vérifiés sur les fichiers de `deploy/` et
`.github/workflows/` (comme Facilitation, OPERATIONS.md §3.22) : une erreur ici
ne se verrait qu'en production.
"""

import json
import os
import re
import textwrap
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

from config import settings as module_reglages

RACINE = Path(__file__).resolve().parents[2]

DURCISSEMENT = (
    "NoNewPrivileges=yes",
    "PrivateTmp=yes",
    "ProtectSystem=full",
    "ProtectKernelTunables=yes",
    "ProtectControlGroups=yes",
    "RestrictSUIDSGID=yes",
)


def lire(chemin):
    return (RACINE / chemin).read_text(encoding="utf-8").replace("\r\n", "\n")


def commandes_ssm():
    texte = lire(".github/workflows/deploy.yml")
    ouverture = "cat > ssm-params.json <<JSON\n"
    debut = texte.index(ouverture) + len(ouverture)
    fin = texte.index("\n          JSON", debut)
    # Les variables du shell ($A, $M…) restent telles quelles : seul l'ordre compte ici.
    return json.loads(textwrap.dedent(texte[debut:fin]).replace("\\$", "$"))["commands"]


class UnitesTests(SimpleTestCase):
    def test_les_unites_applicatives_sont_durcies(self):
        for unite in ("foxhouse-gunicorn.service", "foxhouse-purge.service"):
            texte = lire(f"deploy/{unite}")
            for directive in DURCISSEMENT:
                self.assertIn(directive, texte, unite)
            # Jamais `strict` : /var/www deviendrait en lecture seule.
            self.assertEqual(re.findall(r"^ProtectSystem=(\S+)$", texte, re.M), ["full"], unite)
            self.assertIn("User=django", texte, unite)
            self.assertIn("UMask=0027", texte, unite)
            self.assertIn("EnvironmentFile=/run/foxhouse/.env", texte, unite)
            self.assertIn("Requires=foxhouse-env-fetch.service", texte, unite)

    def test_gunicorn_sur_8013_avec_connexions_persistantes(self):
        texte = lire("deploy/foxhouse-gunicorn.service")
        self.assertIn("--bind 127.0.0.1:8013", texte)
        self.assertIn("config.wsgi:application", texte)
        self.assertIn('Environment="DB_CONN_MAX_AGE=60"', texte)

    def test_la_purge_garde_des_connexions_courtes(self):
        texte = lire("deploy/foxhouse-purge.service")
        self.assertIn("manage.py purger_parties", texte)
        self.assertNotIn("DB_CONN_MAX_AGE", texte)
        self.assertIn("OnCalendar=", lire("deploy/foxhouse-purge.timer"))

    def test_le_script_ssm_tourne_depuis_usr_local_sbin(self):
        texte = lire("deploy/foxhouse-env-fetch.service")
        self.assertIn("ExecStart=/usr/local/sbin/foxhouse-env-fetch.sh", texte)
        self.assertIn("RuntimeDirectoryMode=0750", texte)


class NginxTests(SimpleTestCase):
    def test_proxy_vers_8013_et_statiques_sur_disque(self):
        texte = lire("deploy/nginx/foxhouse.foxugly.com.conf")
        self.assertIn("server 127.0.0.1:8013;", texte)
        for emplacement in ("location = /health/", "location ^~ /api/", "location ^~ /admin/"):
            self.assertIn(emplacement, texte)
        self.assertIn("alias /var/www/django_websites/FoxHouse/backend/staticfiles/;", texte)
        self.assertIn("root /var/www/django_websites/FoxHouse/frontend/dist/frontend/browser;", texte)
        self.assertIn("try_files $uri $uri/ /index.html;", texte)
        self.assertIn("listen 443 ssl http2;", texte)
        self.assertIn("/etc/letsencrypt/live/foxugly.com/fullchain.pem", texte)

    def test_csp_sans_script_en_ligne(self):
        texte = lire("deploy/nginx/foxhouse.foxugly.com.conf")
        csp = re.search(r'map \$host \$foxhouse_csp \{\s*default "([^"]+)";', texte).group(1)
        self.assertIn("script-src 'self';", csp)
        self.assertNotIn("unsafe-inline';", csp.split("style-src")[0])
        self.assertIn("frame-ancestors 'none'", csp)
        # La CSP est posée sur les documents de la SPA (index.html et le repli).
        self.assertEqual(texte.count("add_header Content-Security-Policy $foxhouse_csp always;"), 2)


class DeploiementTests(SimpleTestCase):
    def test_root_n_installe_que_depuis_son_miroir(self):
        commandes = commandes_ssm()
        self.assertEqual(commandes[0], "set -eu")

        def position(motif):
            return next(i for i, c in enumerate(commandes) if motif in c)

        miroir = position("fetch --quiet --depth=1 https://github.com/Foxugly/FoxHouse.git")
        privilegie = position("/usr/local/sbin/foxhouse-deploy-privileged.sh $M")
        extraction = position("tar --no-same-owner")
        application = position("sudo -u django bash $A/.bundle-neuf/deploy/ssm-deploy.sh")
        redemarrage = position("systemctl restart foxhouse-gunicorn")
        self.assertLess(miroir, privilegie)
        self.assertLess(privilegie, extraction)
        self.assertLess(extraction, application)
        self.assertLess(application, redemarrage)
        self.assertIn("sudo -u django", commandes[extraction])
        self.assertIn("show $GITHUB_SHA:deploy/foxhouse-deploy-privileged.sh", commandes[position("show $GITHUB_SHA")])

    def test_le_script_privilegie_lit_tout_dans_le_miroir(self):
        texte = lire("deploy/foxhouse-deploy-privileged.sh")
        self.assertIn('git --git-dir="$M" show "$SHA:$1"', texte)
        self.assertNotIn("/var/www/django_websites", texte)

    def test_seul_un_push_vers_main_deploie(self):
        texte = lire(".github/workflows/deploy.yml")
        declencheurs = texte.split("\non:\n", 1)[1].split("\n\n", 1)[0]
        self.assertEqual(declencheurs.strip(), "push:\n    branches: [main]")
        self.assertIn("if: github.ref == 'refs/heads/main'", texte)
        self.assertIn("environment: production", texte)
        self.assertIn("uses: ./.github/workflows/ci.yml", texte)


class VersionTests(SimpleTestCase):
    def test_version_depuis_l_environnement_d_abord(self):
        with mock.patch.dict(os.environ, {"SENTRY_RELEASE": " abc123 "}):
            self.assertEqual(module_reglages._version_deployee(), "abc123")

    def test_version_depuis_le_fichier_release(self):
        with mock.patch.dict(os.environ, {"SENTRY_RELEASE": ""}), mock.patch.object(
            Path, "read_text", return_value="def456\n"
        ):
            self.assertEqual(module_reglages._version_deployee(), "def456")

    def test_version_vide_sans_rien(self):
        with mock.patch.dict(os.environ, {"SENTRY_RELEASE": ""}), mock.patch.object(
            Path, "read_text", side_effect=FileNotFoundError
        ):
            self.assertEqual(module_reglages._version_deployee(), "")
