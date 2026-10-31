# CLAUDE.md

FoxHouse : site de jeux de cartes (Tarot, Rami…) contre l'ordinateur, de la flotte Foxugly.
Django (API JSON) dans `backend/`, Angular à venir. Conception : `docs/superpowers/specs/2026-10-31-foxhouse-design.md`.
Référence de la flotte : `D:\Projects\PycharmProjects\foxChess`. Code, commentaires et messages en français.

## Commandes (depuis `backend/`, PowerShell, `$env:DJANGO_DEBUG="True"`)

- Tests : `.\.venv\Scripts\python.exe manage.py test`
- Lint : `.\.venv\Scripts\python.exe -m ruff check .`
- Migrations oubliées : `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`
- Santé : `GET /health/` → 200 ou 503

## Règles

1. Les règles des jeux ne dépendent pas de Django (`tapis/`, `rami/` : pas d'import Django hors `apps.py` et modèles).
2. La vue d'un joueur ne fuit rien : jamais la main d'un autre, la pioche ni la graine.
3. Un jeu = une app inscrite au registre.

(À compléter à la tâche 8.)
