# CLAUDE.md

FoxHouse : site de jeux de cartes contre l'ordinateur, de la flotte Foxugly. Jeux : rami 51, 8 américain,
dame de pique, président, whist à la couleur ; les suivants sont dans `docs/backlog.md`.
Django (API JSON) dans `backend/`, Angular 21 dans `frontend/`. Conception : `docs/superpowers/specs/2026-10-31-foxhouse-design.md`.
Référence de la flotte : `D:\Projects\PycharmProjects\foxChess`. Code, commentaires et messages en français.

## Commandes backend (depuis `backend/`, PowerShell, `$env:DJANGO_DEBUG="True"`)

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
- `huit/`, `dame/`, `president/` — 8 américain, dame de pique, président, bâtis comme le rami.
  Règles : `docs/superpowers/specs/2026-10-31-jeux-huit-dame-president.md`.
- `whist/` — whist à la couleur (4 joueurs, enchères, emballage, trou, abondances, misères).
  Règles : `docs/superpowers/specs/2026-11-01-whist-couleur.md`.
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

## Frontend (`frontend/`, Angular 21, Node 24)

Commandes (depuis `frontend/`) : `npm ci`, `npm run lint`, `npm test` (Vitest, une passe),
`npm run build`, `npm run format` (Prettier).

Développement local, deux terminaux :

1. `backend/` : `$env:DJANGO_DEBUG="True"`, `manage.py migrate` puis `manage.py runserver` (port 8000) ;
2. `frontend/` : `npm start` → http://localhost:4200. `proxy.conf.json` renvoie `/api` et `/health`
   vers `127.0.0.1:8000` avec `changeOrigin: false` : Django voit alors `Host` et `Origin` égaux
   à `localhost:4200` et le contrôle CSRF passe sans `CSRF_TRUSTED_ORIGINS`.

Architecture (`src/app/`) :

- `core/` — types de la vue (`vue.ts`, miroir du schéma `tapis/vue.py`), client de l'API
  (`api.service.ts`, erreurs en `ErreurApi`), Sentry.
- `tapis/` — la table, commune à tous les jeux : `table/` (sièges sur une ellipse, zones du centre,
  panneau de résultat), `main/` (cartes superposées, en autant de rangées qu'il faut pour que le
  coin de chaque carte reste visible), `carte/`, `menu/` (lignes du menu et un bouton par action,
  ce qui manque à la sélection écrit sous un bouton inactif), `selection.ts` (cartes choisies et
  cible ; un bouton n'est actif que si `cartes_min ≤ sélection ≤ cartes_max` et la cible demandée
  est choisie ; une action `direct` n'a pas de bouton : le clic sur une carte l'envoie avec cette
  seule carte, et le menu l'écrit en consigne), `disposition.ts` (calculs de placement, sans Angular).
- `pages/` — `accueil` (formulaire généré depuis `GET jeux/`, reprise de la partie courante) et
  `partie` (table + menu, envoi des actions, relecture des `etapes` avant la vue finale).
- `src/testing/` — vues d'exemple (`vues.ts`) tirées du serveur, dont `factice.json`.

Habillage : l'image d'une carte vient du jeton `HABILLAGE` (`tapis/habillage.ts`), par défaut
`HABILLAGE_WEBISSO` (SVG copiés dans `public/cartes/webisso/`, aucune ressource externe). Un autre
jeu de cartes = un autre `Habillage` fourni à la place, sans toucher la table.

Règle : le frontend n'a aucune règle de jeu. Il affiche `vue` et renvoie `{version, action, cartes,
cible}` ; les libellés viennent du serveur. Aucun mot propre à un jeu (« rami », « piocher »,
« poser », « défausse », « brouillon ») dans `src/app/tapis`, `src/app/core` ni `src/app/pages` :
`tapis/genericite.spec.ts` le vérifie et rend la vue du jeu factice. Seules les données de
`src/testing/` peuvent les contenir. Thème clair/sombre par `prefers-color-scheme` (variables CSS),
écran de 360 px minimum sans défilement horizontal. Captures : `docs/captures/`.

## Production (`foxhouse.foxugly.com`)

gunicorn `127.0.0.1:8013` (WSGI, pas de Redis), PostgreSQL `foxhouse`, SSM `/foxhouse/prod` →
`/run/foxhouse/.env`, dossier `/var/www/django_websites/FoxHouse`. Un push vers `main` lance
`deploy.yml` : la CI (`ci.yml`, appelée) puis le déploiement par bundle S3 + SSM. Mise en service,
étapes hors dépôt et vérifications : `deploy/README.md`. Garde-fous des unités, du vhost et du
pipeline : `backend/config/test_deploiement.py`. Version déployée : `backend/RELEASE` (écrit par la CI),
rendue par `/health/`.

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
