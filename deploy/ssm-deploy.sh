#!/usr/bin/env bash
#
# FoxHouse — étape APPLICATIVE du déploiement, lancée par SSM en tant que django
# (`sudo -u django bash …/ssm-deploy.sh <sha>`), après l'étape privilégiée de root.
#
# Le bundle de la CI (backend/, frontend/dist/, deploy/) vient d'être extrait par
# django dans $APP/.bundle-neuf. Ce script :
#   1. installe les dépendances dans $APP/.venv (hors du bundle : il survit aux
#      déploiements) ;
#   2. dans le NOUVEAU backend : collectstatic, migrate, check --deploy — avec la
#      configuration de production (/run/foxhouse/.env) ;
#   3. bascule : backend/, frontend/ et deploy/ sont remplacés d'un bloc par ceux
#      du bundle. Contrairement à une extraction par-dessus l'arbre en place, un
#      fichier retiré du dépôt (module, migration, ancien asset) disparaît aussi
#      du serveur.
# Le redémarrage de gunicorn est fait ensuite par root dans le pipeline SSM.
set -euo pipefail
umask 027

SHA="${1:?usage : $0 <sha attendu>}"
APP=/var/www/django_websites/FoxHouse
NEUF="$APP/.bundle-neuf"
ENV_FILE=/run/foxhouse/.env

cd "$APP"
[ -d "$NEUF/backend" ] || { echo "ERREUR : $NEUF/backend absent (extraction du bundle ?)" >&2; exit 1; }
# Le bundle est bien celui du commit déployé (backend/RELEASE écrit par la CI).
if [ "$(cat "$NEUF/backend/RELEASE" 2>/dev/null)" != "$SHA" ]; then
  echo "ERREUR : le bundle ne porte pas la version $SHA" >&2
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  # Premier déploiement : Python 3.12 d'Ubuntu 24.04, comme la CI.
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r "$NEUF/backend/requirements.txt"

if [ ! -s "$ENV_FILE" ]; then
  echo "ERREUR : $ENV_FILE absent ou vide — foxhouse-env-fetch a-t-il tourné ? (systemctl status foxhouse-env-fetch)" >&2
  exit 1
fi

# Lecture littérale (clé=valeur), jamais `source` : une valeur contenant $( )
# ou des guillemets ne doit pas être interprétée par le shell (§3.11).
while IFS='=' read -r cle valeur || [ -n "$cle" ]; do
  case "$cle" in ''|\#*) continue ;; esac
  export "$cle=$valeur"
done < "$ENV_FILE"

cd "$NEUF/backend"
"$APP/.venv/bin/python" manage.py collectstatic --noinput --verbosity 0
"$APP/.venv/bin/python" manage.py migrate --noinput
"$APP/.venv/bin/python" manage.py check --deploy --fail-level ERROR
cd "$APP"

# Bascule : deux renommages par dossier, l'ancien supprimé ensuite.
for d in backend frontend deploy; do
  rm -rf "$d.ancien"
  if [ -e "$d" ]; then
    mv "$d" "$d.ancien"
  fi
  mv "$NEUF/$d" "$d"
done
rm -rf backend.ancien frontend.ancien deploy.ancien "$NEUF"

echo "[ssm-deploy] FoxHouse ${SHA:0:7} en place (dépendances, collectstatic, migrate)."
