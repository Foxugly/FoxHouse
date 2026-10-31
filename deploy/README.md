# Mise en service de FoxHouse sur la flotte (foxhouse.foxugly.com)

Référence : `OPERATIONS.md` (dépôt `Foxugly/foxugly-ops`), §3.12 « nouveau site ». Forme reprise de
foxChess ; transport par **bundle S3** comme foxugly_website (Django + Angular dans un même dépôt).
Port **8013**, gunicorn (WSGI), PostgreSQL 16 locale (base et rôle `foxhouse`), **pas de Redis ni de
Celery**. Application dans `/var/www/django_websites/FoxHouse` :

```
/var/www/django_websites/FoxHouse/
├── .venv/                 # créé au premier déploiement, gardé ensuite
├── backend/               # Django (RELEASE = SHA déployé, staticfiles/ = collectstatic)
├── frontend/dist/frontend/browser/   # servi par nginx
└── deploy/
```

**Installé par chaque déploiement** (root, depuis son miroir nu `/var/lib/fleet-deploy/FoxHouse.git`
au SHA poussé, jamais depuis l'arbre de django — §3.10/§3.11) : `/usr/local/sbin/foxhouse-env-fetch.sh`,
unités `foxhouse-env-fetch.service`, `foxhouse-gunicorn.service`, `foxhouse-purge.service|timer`, vhost
nginx. Voir `foxhouse-deploy-privileged.sh`.
**Installé une fois, à la main, par root** : base, dossier de l'application, sudoers.

Chaque étape touche la production : à faire avec l'accord de Renaud, dans cet ordre.

---

## 0. Vérifications préalables (root, sur la machine)

```bash
ss -lntp | grep -c ':8013 '                 # 0 : port libre
nginx -T 2>/dev/null | grep -c foxhouse     # 0 : aucun vhost existant
python3 --version                           # 3.12 (Ubuntu 24.04), comme la CI
nginx -V 2>&1 | grep -o brotli | head -1    # brotli : module présent (gzip_static suffit sinon)
```

## 1. DNS (administrateur, CloudShell)

Route 53, zone `foxugly.com` : `A foxhouse → 54.229.220.110`. Le certificat `foxugly.com` est un joker
(`*.foxugly.com`) : rien à émettre.

```bash
ZONE=$(aws route53 list-hosted-zones-by-name --dns-name foxugly.com \
  --query 'HostedZones[?Name==`foxugly.com.`].Id' --output text)
aws route53 change-resource-record-sets --hosted-zone-id "$ZONE" --change-batch '{
  "Comment": "FoxHouse",
  "Changes": [{"Action": "CREATE", "ResourceRecordSet": {
    "Name": "foxhouse.foxugly.com", "Type": "A", "TTL": 300,
    "ResourceRecords": [{"Value": "54.229.220.110"}]}}]}'
```

## 2. IAM (administrateur, CloudShell — jamais depuis la machine, §3.5)

```bash
bash deploy/iam-cloudshell.sh
```

Rôle `foxhouse-deploy` (OIDC, confiance épinglée sur `Foxugly/FoxHouse`, environnement `production`,
les deux formes de `sub`) : `ssm:SendCommand` sur l'instance + `AWS-RunShellScript`,
`ssm:GetCommandInvocation`, `s3:PutObject` sur `foxugly-deploy/builds/foxhouse/*`. Étend
`SsmReadFleetAppConfig` (rôle d'instance `foxugly-fleet-ec2`) avec `/foxhouse/prod` et
`/foxhouse/prod/*`. Affiche les instructions S3 et KMS du rôle d'instance (attendu : `s3:GetObject`
sur `foxugly-deploy/builds/*`, `kms:Decrypt` pour `aws/ssm`) et, à la fin, l'ARN du rôle.

## 3. Base PostgreSQL (root, sur la machine)

```bash
openssl rand -base64 33 | tr -d '\n' > /root/foxhouse-db-password && chmod 600 /root/foxhouse-db-password
sudo -u postgres psql <<SQL
CREATE ROLE foxhouse LOGIN PASSWORD '$(cat /root/foxhouse-db-password)';
CREATE DATABASE foxhouse OWNER foxhouse;
\c foxhouse
ALTER SCHEMA public OWNER TO foxhouse;
SQL
```

La sauvegarde hebdomadaire (`fleet-db-backup.timer`, §3.23) prend la nouvelle base d'elle-même.

## 4. Paramètres SSM `/foxhouse/prod/*` (administrateur, CloudShell)

Copier le mot de passe de l'étape 3 dans un fichier de CloudShell (`sudo cat /root/foxhouse-db-password`
sur la machine), puis :

```bash
bash deploy/ssm-cloudshell.sh ~/foxhouse-db-password [SENTRY_DSN_BACKEND] && rm ~/foxhouse-db-password
```

| Paramètre | Type | Valeur |
|---|---|---|
| `SECRET_KEY` | SecureString | générée par le script (jamais remplacée) |
| `DB_PASSWORD` | SecureString | celui de l'étape 3 |
| `ALLOWED_HOSTS` | String | `foxhouse.foxugly.com` |
| `CSRF_TRUSTED_ORIGINS` | String | `https://foxhouse.foxugly.com` |
| `DB_ENGINE` / `DB_NAME` / `DB_USER` | String | `postgresql` / `foxhouse` / `foxhouse` |
| `DB_HOST` / `DB_PORT` | String | `127.0.0.1` / `5432` |
| `SENTRY_ENVIRONMENT` | String | `production` |
| `SENTRY_DSN` | String | facultatif : projet `foxhouse-backend` |

Facultatifs : `RETENTION_PARTIES_JOURS` (30), `LOG_LEVEL` (WARNING), `SENTRY_TRACES_SAMPLE_RATE` (0).
**Ne pas poser** `SENTRY_RELEASE` ni `DB_CONN_MAX_AGE` : la version vient de `backend/RELEASE` (le
déploiement vérifie que `/health/` la rend) et `DB_CONN_MAX_AGE=60` est dans l'unité gunicorn seule.

## 5. Machine (root, une fois)

```bash
# Dossier de l'application, à django (le déploiement y extrait le bundle).
install -d -o django -g www-data -m 750 /var/www/django_websites/FoxHouse

# Miroir nu de root, et sudoers lu dedans (jamais depuis l'arbre de django, §3.10).
# Avant la fusion de la branche de mise en production : remplacer main par feat/production.
install -d -m 700 -o root -g root /var/lib/fleet-deploy
M=/var/lib/fleet-deploy/FoxHouse.git
[ -d $M ] || git init --quiet --bare $M
git --git-dir=$M fetch --quiet --depth=1 https://github.com/Foxugly/FoxHouse.git main
git --git-dir=$M show FETCH_HEAD:deploy/sudoers/foxhouse-deploy > /tmp/foxhouse-deploy
visudo -cf /tmp/foxhouse-deploy && install -o root -g root -m 0440 /tmp/foxhouse-deploy /etc/sudoers.d/foxhouse-deploy
rm -f /tmp/foxhouse-deploy; visudo -c
```

## 6. GitHub (Renaud, `gh`)

```bash
R=Foxugly/FoxHouse
gh repo edit $R --enable-auto-merge

# Protection de main : checks requis (noms des jobs sur une PR), administrateurs exemptés.
gh api -X PUT repos/$R/branches/main/protection --input - <<'JSON'
{
  "required_status_checks": {"strict": false, "contexts": [
    "tests", "lint", "pip-audit", "frontend", "codeql (python)", "codeql (javascript-typescript)"]},
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
JSON

# Environnement production, réservé aux branches protégées (donc à main).
gh api -X PUT repos/$R/environments/production --input - <<'JSON'
{"deployment_branch_policy": {"protected_branches": true, "custom_branch_policies": false}}
JSON
gh secret set AWS_DEPLOY_ROLE_ARN --env production --repo $R   # ARN affiché par l'étape 2
gh secret set EC2_INSTANCE_ID     --env production --repo $R --body i-0fe664678563bae5f

# Fusion automatique des PR Dependabot (§3.20) : même PAT que le reste de la flotte ;
# vérifier que son accès aux dépôts inclut FoxHouse.
gh secret set DEPENDABOT_AUTOMERGE_TOKEN --app dependabot --repo $R
```

## 7. Premier déploiement

Il n'y a pas d'amorçage séparé : le premier passage de `deploy.yml` crée tout le reste (miroir, script
SSM, unités, vhost, `.venv`, migrations, collectstatic, démarrage). Les étapes 1 à 6 doivent être faites
**avant** de fusionner la branche de mise en production dans `main` ; sinon le job `deploy` échoue
(pas de dossier, pas de `.env`…) et il suffit de le relancer (« Re-run failed jobs ») une fois l'étape
manquante faite.

Ce que fait chaque déploiement, dans l'ordre (`.github/workflows/deploy.yml`) : CI complète → build du
frontend (version injectée) → pré-compression → bundle `s3://foxugly-deploy/builds/foxhouse/` → SSM en
root : miroir au SHA, `foxhouse-deploy-privileged.sh` (script SSM, unités, `foxhouse-env-fetch` démarré,
minuterie activée, vhost + `nginx -t`) → django extrait le bundle dans `.bundle-neuf` → `ssm-deploy.sh`
en django (pip, collectstatic, migrate, `check --deploy`, bascule des dossiers) → `systemctl restart
foxhouse-gunicorn` → normalisation des droits → contrôle de `/health/` (200 et version = SHA).

Puis un administrateur (e-mail seul, §3.16) :

```bash
sudo -u django bash -c 'cd /var/www/django_websites/FoxHouse/backend &&
  while IFS="=" read -r k v; do case "$k" in ""|\#*) continue;; esac; export "$k=$v"; done < /run/foxhouse/.env &&
  ../.venv/bin/python manage.py createsuperuser'
```

Rotation d'un secret : modifier SSM, `systemctl restart foxhouse-env-fetch` **puis**
`systemctl restart foxhouse-gunicorn`.

## 8. Après la mise en service

- **Vérifications §3.12** (root) :
  - `curl -sS https://foxhouse.foxugly.com/health/` → 200, `"version"` = SHA de `main` ;
  - `curl -sSI https://foxhouse.foxugly.com/` montre la CSP, HSTS, `X-Frame-Options: DENY` ;
    `/admin/login/` s'affiche correctement (CSP de Django, styles et scripts sous `/static/`) ;
  - `systemctl show foxhouse-gunicorn -p NoNewPrivileges -p ProtectSystem -p PrivateTmp` → `yes`, `full`, `yes` ;
  - `sudo find /var/www/django_websites/FoxHouse ! -type l \( -perm /020 -o -perm /004 \)` vide ;
  - `sudo -l -U django` ne montre que les autorisations attendues ;
  - `systemctl list-timers foxhouse-purge.timer` planifié ; `systemctl start foxhouse-purge` réussit.
- **UptimeRobot** (tableau de bord) : moniteur mot-clé sur `https://foxhouse.foxugly.com/health/`,
  300 s, mot-clé `"status": "ok"`.
- **Sentry** (org `foxugly-srl`, de.sentry.io) : projets `foxhouse-backend` (DSN → SSM `SENTRY_DSN`, puis
  rotation ci-dessus) et `foxhouse-frontend` (DSN public → `frontend/src/app/core/sentry.config.ts`, par PR).
- **OPERATIONS.md** : ligne d'inventaire (§2), port 8013 pris et prochain libre **8014** (§3.4), ligne
  `Foxugly/FoxHouse | 1440831627 | foxhouse-deploy | main | SSM + S3` (§3.11) ; **`~/.claude/CLAUDE.md`** :
  ligne du tableau de la flotte, prochain port 8014 ; `D:\Projects\CLAUDE.md` : ligne FoxHouse.
