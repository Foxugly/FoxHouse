#!/usr/bin/env bash
# Paramètres SSM de FoxHouse (/foxhouse/prod/*), à coller dans AWS CloudShell (eu-west-1).
#
# Usage :
#   bash ssm-cloudshell.sh <fichier-db-password> [SENTRY_DSN]
#   bash ssm-cloudshell.sh - [SENTRY_DSN]          # mot de passe demandé sans écho
#   DB_PASSWORD=… bash ssm-cloudshell.sh "" [SENTRY_DSN]
#
# - DB_PASSWORD : celui de la base créée sur la machine (`sudo cat /root/foxhouse-db-password`).
#   Un fichier ou la saisie sans écho évitent qu'il reste dans l'historique du shell.
# - SECRET_KEY est générée ici et n'est JAMAIS remplacée si elle existe déjà.
# - SENTRY_DSN facultatif (projet foxhouse-backend) ; sans lui, Sentry reste inactif.
#   SENTRY_ENVIRONMENT=production est posé dans tous les cas.
# - Ne PAS poser SENTRY_RELEASE ici : la version vient de backend/RELEASE (écrit par
#   la CI) et le contrôle de /health/ du déploiement compare cette version au SHA.
# - Aucune valeur secrète n'est affichée ; la fin liste les noms et les types.
#
# Ré-exécutable : les paramètres non secrets sont réécrits à l'identique.
set -euo pipefail

REGION=eu-west-1
P=/foxhouse/prod

SOURCE_MDP="${1-}"
SENTRY_DSN="${2-}"

if [ -n "$SOURCE_MDP" ] && [ "$SOURCE_MDP" != "-" ]; then
  DB_PASSWORD=$(tr -d '\r\n' < "$SOURCE_MDP")
elif [ "$SOURCE_MDP" = "-" ] || [ -z "${DB_PASSWORD-}" ]; then
  read -r -s -p "DB_PASSWORD (sortie de sudo cat /root/foxhouse-db-password) : " DB_PASSWORD; echo
fi
[ "${#DB_PASSWORD}" -ge 20 ] || { echo "Mot de passe trop court : mauvais copier-coller ?" >&2; exit 1; }

put() {  # put <nom> <type> <valeur>
  aws ssm put-parameter --region "$REGION" --name "$P/$1" --type "$2" --value "$3" \
    --overwrite --no-cli-pager >/dev/null
  echo "  $P/$1 ($2)"
}

echo "Écriture :"
if aws ssm get-parameter --region "$REGION" --name "$P/SECRET_KEY" >/dev/null 2>&1; then
  echo "  $P/SECRET_KEY existe déjà : conservée"
else
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
  aws ssm put-parameter --region "$REGION" --name "$P/SECRET_KEY" --type SecureString \
    --value "$SECRET_KEY" --no-cli-pager >/dev/null
  unset SECRET_KEY
  echo "  $P/SECRET_KEY (SecureString, générée)"
fi
put DB_PASSWORD          SecureString "$DB_PASSWORD"; unset DB_PASSWORD
put ALLOWED_HOSTS        String "foxhouse.foxugly.com"
put CSRF_TRUSTED_ORIGINS String "https://foxhouse.foxugly.com"
put DB_ENGINE            String "postgresql"
put DB_NAME              String "foxhouse"
put DB_USER              String "foxhouse"
put DB_HOST              String "127.0.0.1"
put DB_PORT              String "5432"
put SENTRY_ENVIRONMENT   String "production"
if [ -n "$SENTRY_DSN" ]; then
  put SENTRY_DSN         String "$SENTRY_DSN"
else
  echo "  (SENTRY_DSN non fourni : Sentry backend inactif ; relancer avec le DSN plus tard)"
fi

echo
echo "Contenu de $P (noms et types seulement) :"
aws ssm get-parameters-by-path --region "$REGION" --path "$P" --recursive \
  --query 'Parameters[].[Name,Type]' --output table --no-cli-pager
