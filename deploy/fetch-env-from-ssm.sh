#!/usr/bin/env bash
#
# FoxHouse — récupère la configuration depuis SSM Parameter Store vers /run.
#
# Repris de foxChess (deploy/fetch-env-from-ssm.sh), même contrat : lancé au
# démarrage par foxhouse-env-fetch.service (root, oneshot), il écrit
# /run/foxhouse/.env (tmpfs : rien sur disque, rien dans un instantané EBS),
# atomiquement (fichier .tmp puis mv), et refuse de remplacer un .env valide
# par un fichier vide.
#
# Installé par le déploiement en /usr/local/sbin/foxhouse-env-fetch.sh
# (root:root 0755), depuis le miroir nu de root au SHA poussé — jamais exécuté
# depuis l'arborescence modifiable par django (OPERATIONS.md §3.10).
set -euo pipefail

PREFIX="${FOXHOUSE_SSM_PREFIX:-/foxhouse/prod}"
REGION="${FOXHOUSE_SSM_REGION:-eu-west-1}"
OUT_DIR="${FOXHOUSE_ENV_DIR:-/run/foxhouse}"
OUT_FILE="${FOXHOUSE_ENV_FILE:-$OUT_DIR/.env}"
OWNER="${FOXHOUSE_ENV_OWNER:-django:www-data}"

# Le rôle d'instance, jamais les clés statiques de /root/.aws (certbot-route53,
# sans droit SSM : OPERATIONS.md §3.19, piège 2).
export AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_CONFIG_FILE=/dev/null

echo "[fetch-env] prefix=$PREFIX region=$REGION out=$OUT_FILE"

mkdir -p "$OUT_DIR"
chmod 750 "$OUT_DIR"
chown root:www-data "$OUT_DIR"

TMP_FILE="$OUT_FILE.tmp"
: > "$TMP_FILE"
chmod 640 "$TMP_FILE"

OUT=$(aws ssm get-parameters-by-path \
  --region "$REGION" \
  --path "$PREFIX" \
  --recursive \
  --with-decryption \
  --output json)

python3 -c '
import json, sys
prefix, out_path, payload = sys.argv[1:4]
data = json.loads(payload)
n = 0
with open(out_path, "a", encoding="utf-8") as f:
    for p in data.get("Parameters", []):
        name = p["Name"]
        key = name[len(prefix) + 1:] if name.startswith(prefix + "/") else name.rsplit("/", 1)[-1]
        value = p["Value"]
        if "\n" in value or "\r" in value:
            print(f"ERREUR : la valeur de {key} contient un saut de ligne", file=sys.stderr)
            sys.exit(2)
        f.write(f"{key}={value}\n")
        n += 1
print(f"[fetch-env] {n} entrées écrites dans le fichier provisoire", file=sys.stderr)
' "$PREFIX" "$TMP_FILE" "$OUT"

COUNT=$(grep -c '=' "$TMP_FILE" || true)
if [ "$COUNT" -eq 0 ]; then
  echo "ERREUR : aucun paramètre sous $PREFIX — le .env en place n'est pas remplacé" >&2
  rm -f "$TMP_FILE"
  exit 3
fi

chown "$OWNER" "$TMP_FILE"
chmod 640 "$TMP_FILE"
mv -f "$TMP_FILE" "$OUT_FILE"
echo "[fetch-env] $OUT_FILE prêt ($COUNT entrées, propriétaire $OWNER, mode 0640)"
