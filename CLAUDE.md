# CLAUDE.md

FoxHouse : site de jeux de cartes contre l'ordinateur, de la flotte Foxugly. La v1 ne livre que le rami 51.
Django (API JSON) dans `backend/`, Angular à venir. Conception : `docs/superpowers/specs/2026-10-31-foxhouse-design.md`.
Référence de la flotte : `D:\Projects\PycharmProjects\foxChess`. Code, commentaires et messages en français.

## Commandes (depuis `backend/`, PowerShell, `$env:DJANGO_DEBUG="True"`)

- Tests : `.\.venv\Scripts\python.exe manage.py test` (≈ 40 s : le rami rejoue 200 parties complètes)
- Lint : `.\.venv\Scripts\python.exe -m ruff check .`
- Migrations oubliées : `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`
- Purge RGPD : `.\.venv\Scripts\python.exe manage.py purger_parties` — efface les parties non modifiées
  depuis `RETENTION_PARTIES_JOURS` (30) jours et les sessions expirées ; à planifier en production.
- Santé : `GET /health/` → 200 ou 503

## Architecture (`backend/`)

- `tapis/` — le commun, sans Django : interface `Jeu` (`jeu.py`, avec `CoupRefuse` et
  `normaliser_coup`), registre des jeux (`registre.py`), options (`options.py`), cartes (`cartes.py`),
  schéma de la vue de table et son validateur `valider_vue` (`vue.py`).
- `rami/` — le rami 51, sans Django hors `apps.py` ; s'inscrit au registre dans `RamiConfig.ready()`.
- `parties/` — le seul code Django du jeu, commun à tous les jeux :
  - `models.Partie` : `jeu`, `joueur` (jeton du créateur), `sieges`, `etat` (JSON du jeu), `version`, `terminee` ;
  - `sieges` dit qui occupe chaque siège : `{"type": "humain", "joueur": <jeton>}` ou `{"type": "machine"}`.
    Aujourd'hui le siège 0 est l'humain qui crée la partie, les autres sont la machine ; le jeu entre
    humains n'aura qu'à remplir d'autres sièges humains ;
  - `joueur.py` : le joueur anonyme, un jeton aléatoire gardé dans la session (`foxhouse_joueur`) ;
    la session dure `RETENTION_PARTIES_JOURS` (`SESSION_COOKIE_AGE`) et chaque requête la prolonge
    (`SESSION_SAVE_EVERY_REQUEST`) ;
  - `deroulement.py` : `jouer` (coup d'un humain puis la machine), `avancer` (la machine joue tant que
    c'est le tour d'un siège machine, 2 000 coups au plus). Un coup refusé de la machine est un bug
    (`RuntimeError` → 500, Sentry), jamais un 400. Un coup privé (le jeu rend un message `None`,
    p. ex. le brouillon du rami) ne fait d'étape que pour son auteur, avec `Jeu.message_prive` ;
  - `views.py` / `urls.py` : l'API ; `retention.py` + `purger_parties` : la purge.
- `accounts/` — utilisateur de la flotte (administrateurs seulement), `config/` — réglages, `/health/`.

## API (`/api/`, JSON)

Tout est calculé pour le siège de celui qui demande. Les erreurs valent `{"erreur": "…"}` en français.
Les POST exigent l'en-tête `X-XSRF-TOKEN` (cookie `XSRF-TOKEN`, posé par les deux GET marqués CSRF).
Une étape vaut `{"message", "vue"}` : le tapis les rejoue avant d'afficher la vue finale.

| Méthode et chemin | Corps | Réponse |
|---|---|---|
| `GET jeux/` (CSRF) | — | 200 `[jeu.decrire()]` |
| `POST parties/` | `{"jeu", "nb_joueurs", "options"}` | 201 `{"id", "vue", "etapes"}` ; remplace la partie précédente du joueur. 400 jeu inconnu, `nb_joueurs` hors bornes, option invalide |
| `GET parties/courante/` (CSRF) | — | 200 `{"id", "vue"}` ou 204 |
| `GET parties/<uuid>/` | — | 200 `{"id", "vue"}` |
| `POST parties/<uuid>/actions/` | `{"version", "action", "cartes", "cible"}` | 200 `{"vue", "etapes"}`, version + 1. 409 `{"erreur", "vue"}` version périmée ; 400 `{"erreur", "vue"}` coup refusé, pas ton tour, partie terminée |

- Une partie d'un autre joueur, inconnue ou d'un jeu retiré répond **404**, jamais 403.
- Chaque action est jouée sous `transaction.atomic()` + `select_for_update()`.
- `vue.version` vaut toujours `Partie.version`. JSON illisible → 400 ; mauvaise méthode → 405.

## Ajouter un jeu

1. Créer l'app (`manage.py startapp <jeu>`) ; ses règles n'importent pas Django.
2. Implémenter `tapis.jeu.Jeu` : `options`, `nouvelle_partie` (graine de 128 bits), `joueur_actif`,
   `appliquer` (sur une copie de l'état, `CoupRefuse` pour un coup interdit, message `None` pour un coup
   privé, alors `message_prive` donne celui de son auteur), `vue` (conforme à `valider_vue`), `adversaire`.
3. L'inscrire dans `ready()` de son `AppConfig` (`registre.inscrire(MonJeu())`, comme `rami/apps.py`).
4. L'ajouter à `INSTALLED_APPS` ; l'en retirer fait disparaître le jeu.
5. Écrire son test de fuite (comme `rami/tests/test_vue.py::test_vue_ne_fuit_rien`) : sur des parties
   rejouées, la vue d'un joueur ne contient ni les cartes des autres, ni la pioche, ni la graine.

Ni `parties` ni le tapis Angular ne changent : `parties/tests/jeu_factice.py` le prouve.

## Règles

1. Les règles des jeux ne dépendent pas de Django (`tapis/`, `rami/` : pas d'import Django hors `apps.py` et modèles).
2. La vue d'un joueur ne fuit rien : jamais la main d'un autre, la pioche ni la graine.
3. Un jeu = une app inscrite au registre.
