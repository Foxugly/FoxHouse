# CLAUDE.md

FoxHouse : site de jeux de cartes contre l'ordinateur, de la flotte Foxugly. Jeux : rami 51, 8 américain,
dame de pique, président, whist à la couleur ; les suivants sont dans `docs/backlog.md`.
Django (API JSON) dans `backend/`, Angular 21 dans `frontend/`. Conception : `docs/superpowers/specs/2026-10-31-foxhouse-design.md`.
Référence de la flotte : `D:\Projects\PycharmProjects\foxChess`. Code, commentaires et messages en français.

## Commandes backend (depuis `backend/`, PowerShell, `$env:DJANGO_DEBUG="True"`)

- Dépendances : `.\.venv\Scripts\python.exe -m pip install -r requirements.in -r requirements-dev.txt` —
  `requirements.txt` est le verrou haché de la production (Linux / 3.14, généré par uv, commande dans son
  en-tête) ; il ne s'installe pas sous Windows (pas de `tzdata`). Détails : `README.md`.
- Tests : `.\.venv\Scripts\python.exe manage.py test` (≈ 40 s : le rami rejoue 200 parties complètes)
- Lint : `.\.venv\Scripts\python.exe -m ruff check .`
- Migrations oubliées : `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`
- Purge RGPD : `.\.venv\Scripts\python.exe manage.py purger_parties` — efface les parties non modifiées
  depuis `RETENTION_PARTIES_JOURS` (30) jours et les sessions expirées ; planifiée en production chaque jour à 04:40 UTC par `foxhouse-purge.timer` (`deploy/`).
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
| `GET jeux/` (CSRF) | — | 200 `[jeu.decrire()]` (code, nom, bornes, options, `regles`) |
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
- `tapis/` — la table, commune à tous les jeux : `table/` (tapis en stade, sièges sur une ellipse,
  zones du centre, panneau de résultat). **Toutes les cartes de la table ont la même largeur** : la
  plus grande (de 1/12 du côté utile, 96 px au plus, à 34 px au moins) pour laquelle les sièges
  restent sur le feutre, ne se recouvrent pas et laissent la place au centre — elle suit donc
  l'écran, le nombre de joueurs et de cartes. Dernier recours sur un petit écran : les cartes du
  joueur gardent 34 px, celles des autres rétrécissent. Les textes de la table grandissent avec les
  cartes (`--echelle-texte`, ×1 à ×1,4). `main/` (cartes superposées, en autant de rangées qu'il
  faut pour que le coin de chaque carte reste visible ; une carte n'est jamais recouverte à plus de
  75 %), `carte/`, `menu/` (le panneau d'informations, lignes du menu seulement, **aucune
  action**), `actions/` (la barre sous la table : « À toi de jouer » et un bouton par action quand
  le jeu attend le joueur, sinon « En attente des autres joueurs… » ; place toujours réservée pour
  que la table ne change pas de taille ; ce qui manque à la sélection écrit sous un bouton
  inactif), `selection.ts` (cartes choisies et
  cible ; un bouton n'est actif que si `cartes_min ≤ sélection ≤ cartes_max` et la cible demandée
  est choisie ; une action `direct` n'a pas de bouton : le clic sur une carte l'envoie avec cette
  seule carte, et la barre l'écrit en consigne), `disposition.ts` (calculs de placement, sans Angular).
  Quand c'est au joueur, sa main s'entoure de l'accent (`aToi` de la table).
- `pages/` — `accueil` (formulaire généré depuis `GET jeux/`, reprise de la partie courante),
  `partie` (table + barre d'actions + panneau, envoi des actions, relecture des `etapes` avant la
  vue finale ; **plis** dans `partie/plis.ts` : un pli est terminé quand chaque zone `pli` a sa
  carte — l'étape reste alors `DELAI_PLI` (5 s) au lieu de 700 ms, la vue finale le ramasse après
  5 s ou d'un clic, et « Revoir le dernier pli » le remontre avec le message de son étape) et `regles`
  (un onglet par jeu, `?jeu=<code>`, texte tiré de `regles` de `GET jeux/`).
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
rendue par `/health/`. Le venv `/var/www/django_websites/FoxHouse/.venv` tourne sur `/usr/bin/python3.14`
(deadsnakes ; le `python3` du système reste 3.12) : `ssm-deploy.sh` le reconstruit sur place s'il est sur une
autre version (l'ancien gardé en `.venv.prev`, remis en place si la reconstruction échoue).

## 2FA de l'administration

`/admin/` exige un second facteur TOTP pour **tous** les comptes de l'équipe (django-otp 1.7.5 +
qrcode 8.2, app `backend/admin_2fa/`, copie de l'implémentation de référence de la flotte, Poker_server).
L'API et `/health/` n'en voient rien (`parties/tests/test_admin_2fa_api_inchangee.py`).

- **Câblage** : `"admin_2fa.apps.OTPAdminConfig"` *remplace* `"django.contrib.admin"` (il fait de
  `admin.site` un `Admin2FASite`, dont `has_permission` exige aussi `user.is_verified()`) ; plus
  `django_otp`, `otp_totp`, `otp_static`, `admin_2fa` dans INSTALLED_APPS et
  `django_otp.middleware.OTPMiddleware` juste après `AuthenticationMiddleware`. `OTP_TOTP_ISSUER` est
  le libellé dans l'application d'authentification. Une pièce manquante fait échouer
  `manage.py check` (`admin_2fa.E001-E004`).
- **Parcours** : mot de passe sur `/admin/login/` → `/admin/2fa/setup/` (la 1re fois : QR + clé, un
  code pour confirmer, 10 codes de secours affichés **une seule fois**) ou `/admin/2fa/verify/` (code
  TOTP ou code de secours). Pages rendues par Django, CSRF, `never_cache`, aucun script ni style en ligne.
- **Force brute** : django-otp freine chaque appareil (1 s, 2 s, 4 s… après chaque mauvais code) et
  nginx met `/admin/2fa/` dans la même zone `foxhouse_admin_login` que le login (10 r/min par IP).
- **Téléphone perdu / bloqué** (sur la machine, comme l'unité gunicorn) :

  ```bash
  sudo systemd-run --wait --pipe --quiet --uid=django --gid=www-data \
    -p EnvironmentFile=/run/foxhouse/.env -p WorkingDirectory=/var/www/django_websites/FoxHouse/backend \
    /var/www/django_websites/FoxHouse/.venv/bin/python manage.py admin_2fa_reset <email>
  ```

  efface les appareils du compte (nouvel enrôlement au prochain login) ; `--unlock` vide seulement le délai.
- **Tests des pages d'admin** : `admin_2fa.testing.force_admin_login(client, user)`, pas
  `client.force_login` (l'admin renverrait vers le second facteur).
- **Secrets** : jamais dans un journal ni dans Sentry la clé TOTP, le QR ou un code de secours — les
  vues les gardent dans des `Redacted` et le champ s'appelle `token` (nettoyé par Sentry).

## Ajouter un jeu

1. Créer l'app (`manage.py startapp <jeu>`) ; ses règles n'importent pas Django.
2. Implémenter `tapis.jeu.Jeu` : `options`, `nouvelle_partie` (graine de 128 bits), `joueur_actif`,
   `appliquer` (sur une copie de l'état, `CoupRefuse` pour un coup interdit, message `None` pour un coup
   privé, alors `message_prive` donne celui de son auteur), `vue` (conforme à `valider_vue`), `adversaire`,
   et `regles` : le rappel affiché par la page « Règles », dans `<jeu>/rappel.py` (sections
   `{"titre", "points"}`, la dernière « Options » avec une phrase par option ; `tapis/tests/test_rappel.py`).
3. L'inscrire dans `ready()` de son `AppConfig` (`registre.inscrire(MonJeu())`, comme `rami/apps.py`).
4. L'ajouter à `INSTALLED_APPS` ; l'en retirer fait disparaître le jeu.
5. Écrire son test de fuite (comme `rami/tests/test_vue.py::test_vue_ne_fuit_rien`) : sur des parties
   rejouées, la vue d'un joueur ne contient ni les cartes des autres, ni la pioche, ni la graine.

Ni `parties` ni le tapis Angular ne changent : `parties/tests/jeu_factice.py` le prouve.

## Règles

1. Les règles des jeux ne dépendent pas de Django (`tapis/`, `rami/` : pas d'import Django hors `apps.py` et modèles).
2. La vue d'un joueur ne fuit rien : jamais la main d'un autre, la pioche ni la graine.
3. Un jeu = une app inscrite au registre.
