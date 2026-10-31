#!/usr/bin/env bash
#
# FoxHouse — étape PRIVILÉGIÉE du déploiement (tourne en ROOT).
#
# Modèle de foxugly_website (foxugly-deploy-privileged.sh), OPERATIONS.md §3.10 /
# §3.11 : root n'exécute aucun script de l'arborescence modifiable par django et
# n'installe aucun fichier qu'il chargera (unité systemd, vhost nginx, script de
# /usr/local/sbin) depuis cette arborescence. Le pipeline SSM :
#   1. alimente le MIROIR NU DE ROOT (/var/lib/fleet-deploy/FoxHouse.git,
#      root:root 700) depuis GitHub au SHA poussé ;
#   2. installe CE script en /usr/local/sbin (root:root 0755) depuis ce miroir ;
#   3. le lance avec <miroir> <sha>.
# Tout ce que ce script installe est lu dans le miroir (`git show $SHA:…`),
# jamais dans le bundle extrait par django.
#
# Ce qu'il fait, idempotent :
#   - /usr/local/sbin/foxhouse-env-fetch.sh ;
#   - unités foxhouse-* (daemon-reload seulement si l'une a changé) ;
#   - foxhouse-env-fetch démarré (premier déploiement : écrit /run/foxhouse/.env) ;
#   - foxhouse-gunicorn activé au démarrage (le pipeline le redémarre APRÈS
#     l'étape applicative) ; minuterie de purge activée et démarrée ;
#   - vhost nginx, avec copie de secours et retour arrière si `nginx -t` échoue.
set -euo pipefail
umask 022

M="${1:?usage : $0 <miroir-git> <sha>}"
SHA="${2:?usage : $0 <miroir-git> <sha>}"
blob() { git --git-dir="$M" show "$SHA:$1"; }

# Installe le blob $1 en $2 (root:root, mode $3) s'il diffère ; rend 0 si changé.
installer() {
    local source="$1" cible="$2" mode="$3" neuf
    neuf=$(mktemp)
    blob "$source" > "$neuf"
    if cmp -s "$neuf" "$cible"; then
        rm -f "$neuf"
        return 1
    fi
    install -o root -g root -m "$mode" "$neuf" "$cible"
    rm -f "$neuf"
    echo "  installé : $cible"
}

# --- Script de configuration (root, lancé par foxhouse-env-fetch) -------------
installer deploy/fetch-env-from-ssm.sh /usr/local/sbin/foxhouse-env-fetch.sh 0755 || true

# --- Unités systemd ------------------------------------------------------------
unites_changees=0
for unite in foxhouse-env-fetch.service foxhouse-gunicorn.service \
             foxhouse-purge.service foxhouse-purge.timer; do
    if installer "deploy/$unite" "/etc/systemd/system/$unite" 0644; then
        unites_changees=1
    fi
done
if [ "$unites_changees" = 1 ]; then
    systemctl daemon-reload
fi
# start (pas restart) : un .env déjà en place n'est pas relu à chaque déploiement ;
# une rotation de secret se fait à la main (deploy/README.md).
systemctl enable --now foxhouse-env-fetch.service
test -s /run/foxhouse/.env || { echo "ERREUR : /run/foxhouse/.env vide (SSM ?)" >&2; exit 1; }
systemctl enable foxhouse-gunicorn.service
systemctl enable --now foxhouse-purge.timer

# --- nginx ---------------------------------------------------------------------
VHOST=/etc/nginx/sites-available/foxhouse.foxugly.com
neuf=$(mktemp)
blob deploy/nginx/foxhouse.foxugly.com.conf > "$neuf"
if ! cmp -s "$neuf" "$VHOST"; then
    if [ -e "$VHOST" ]; then
        cp -a "$VHOST" "$VHOST.deploybak"
    fi
    install -o root -g root -m 0644 "$neuf" "$VHOST"
    ln -sfn "$VHOST" /etc/nginx/sites-enabled/foxhouse.foxugly.com
    if nginx -t; then
        systemctl reload nginx
        echo "  vhost nginx installé et rechargé"
    else
        echo "ERREUR : nginx -t refuse le vhost ; retour à la version précédente." >&2
        if [ -e "$VHOST.deploybak" ]; then
            mv -f "$VHOST.deploybak" "$VHOST"
        else
            rm -f /etc/nginx/sites-enabled/foxhouse.foxugly.com "$VHOST"
        fi
        nginx -t && systemctl reload nginx
        rm -f "$neuf"
        exit 1
    fi
fi
rm -f "$neuf"

echo "[privilégié] FoxHouse ${SHA:0:7} : unités, script de configuration et vhost à jour."
