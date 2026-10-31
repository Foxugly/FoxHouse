# FoxHouse — plan 1/3 : le serveur (tapis commun, parties, rami)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un backend Django qui fait jouer une partie complète de rami 51 contre des adversaires de la machine, à travers une API JSON générique qu'un tapis Angular pourra afficher sans rien savoir du rami.

**Architecture:** Trois apps. `tapis` définit le commun (cartes, options, interface `Jeu`, registre, schéma de la vue de table). `rami` est un jeu : Python pur, sans modèle ni vue HTTP, inscrit au registre dans `AppConfig.ready()`. `parties` stocke l'état JSON d'une partie, la rattache à un joueur anonyme et expose l'API ; c'est elle qui fait jouer les adversaires.

**Tech Stack:** Python 3.12 (serveur et CI ; 3.14 accepté en local), Django 6.1, PostgreSQL 16 (SQLite en local avec `DJANGO_DEBUG=True`), vues JSON Django sans DRF, ruff 0.16.10, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-31-foxhouse-design.md` (lire §2, §3, §4, §6, §7).

**Les trois plans :** 1/3 ce serveur ; 2/3 le tapis Angular (`frontend/`), écrit après celui-ci, contre l'API livrée ici ; 3/3 la mise en production (DNS, SSM, systemd, nginx, deploy.yml, protection de `main`), dont chaque étape hors dépôt attend l'accord de Renaud.

## Global Constraints

- Dépôt `D:\Projects\PycharmProjects\FoxHouse` ; Django dans `backend/` (`manage.py` à `backend/manage.py`), venv `backend/.venv`. Toutes les commandes ci-dessous se lancent depuis `backend/` en PowerShell, avec `$env:DJANGO_DEBUG="True"`.
- Commande de test : `.\.venv\Scripts\python.exe manage.py test` ; lint : `.\.venv\Scripts\python.exe -m ruff check .`.
- **Référence de la flotte : `D:\Projects\PycharmProjects\foxChess`.** Quand une étape dit « repris de foxChess », copier le fichier et remplacer `foxchess`/`foxChess` par `foxhouse`/`FoxHouse`, retirer ce qui concerne Stockfish et les gabarits HTML.
- Code, noms, commentaires, messages d'erreur et libellés en **français** (comme foxChess et Chronos).
- Les règles des jeux (`tapis/cartes.py`, `tapis/options.py`, `tapis/jeu.py`, `tapis/vue.py`, tout `rami/` sauf `apps.py`) **n'importent pas Django** ; leurs tests héritent de `django.test.SimpleTestCase`.
- Un état de partie est un `dict` sérialisable en JSON. `Jeu.appliquer` ne modifie jamais l'état reçu : il travaille sur `copy.deepcopy`.
- Le joueur humain est toujours le joueur **0**. Les adversaires sont 1 … n-1, nommés « Ordinateur 1 » … ; l'humain « Toi ».
- Identifiants de cartes : `<valeur><enseigne>-<paquet>` avec valeurs `A 2 3 4 5 6 7 8 9 10 J Q K`, enseignes `S H D C` (pique, cœur, carreau, trèfle), paquet `1` ou `2` ; jokers `JK-1` … `JK-4`. Exemple : `10H-2`.
- La vue d'un joueur ne contient **jamais** : une carte d'une autre main ou du brouillon d'un autre joueur, une carte de la pioche, la graine.
- Une partie d'un autre joueur répond **404**, jamais 403 (comme foxChess).
- Pas de Redis, pas de Celery, pas de WebSocket.

## Review Focus

1. **Double clic ou deux onglets** : deux actions envoyées sur la même `version` → la seconde reçoit **409** avec la vue courante et n'est pas appliquée. *(Tâche 8, `test_version_perimee_409`.)*
2. **Requête mal formée** (JSON illisible, carte inconnue, carte qui n'est pas dans la main, action inexistante, cible absente) → **400** avec un message en français, jamais 500, état inchangé. *(Tâche 6, `test_coups_malformes_refuses` ; tâche 8, `test_json_illisible_400`.)*
3. **Pioche vide avec une défausse d'une seule carte** → la manche se termine proprement, sans exception. *(Tâche 4, `test_pioche_vide_defausse_d_une_carte`.)*
4. **As aux deux bouts et jokers ambigus** : A-2-3 et Q-K-A valides, K-A-2 refusé, deux jokers refusés, 5-6-joker lu 5-6-7, Q-K-joker lu J-Q-K. *(Tâche 3.)*
5. **Garder une carte pour la défausse** : avec « terminer par une défausse », une pose ou un ajout qui viderait la main est refusé, y compris par le brouillon d'ouverture. *(Tâche 5, `test_garder_une_carte_pour_la_defausse`.)*

---

### Task 1: Squelette du dépôt, réglages, `/health/`, CI

**Files:**
- Create: `.gitignore`, `README.md`, `CLAUDE.md`, `.github/workflows/ci.yml`, `.github/dependabot.yml`
- Create: `backend/manage.py`, `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/ruff.toml`
- Create: `backend/config/{__init__,settings,urls,wsgi,sante,sentry_filtres}.py`
- Create: `backend/accounts/` (repris de foxChess : utilisateur par e-mail pour les administrateurs, OPERATIONS.md §3.16), avec sa migration `0001_initial`
- Create: `backend/tapis/`, `backend/parties/`, `backend/rami/` (apps vides : `__init__.py`, `apps.py`, `tests/__init__.py`)
- Test: `backend/config/tests.py`

**Interfaces:**
- Produces: `GET /health/` → `{"status": "ok"|"degraded", "version": str, "checks": {"db": {"ok": bool}}}`, 200 ou 503. Réglage `RETENTION_PARTIES_JOURS = 30`.

- [ ] **Step 1: `git init`, `.gitignore`** (Python, `.venv/`, `db.sqlite3`, `.env`, `node_modules/`, `frontend/dist/`, `.superpowers/`, `.playwright-mcp/`). Le fichier de conception et ce plan sont déjà dans `docs/` : ils font partie du premier commit.

- [ ] **Step 2: Dépendances.** `requirements.txt` : `Django>=6.1.2,<6.2`, `psycopg[binary]>=3.3.6,<3.4`, `gunicorn==23.0.0`, `sentry-sdk[django]==2.73.0`. `requirements-dev.txt` et `ruff.toml` : repris de foxChess tels quels. Créer `backend/.venv` et installer les deux fichiers.

- [ ] **Step 3: Écrire le test qui échoue** dans `config/tests.py` :

```python
class SanteTests(TestCase):
    def test_sante_ok(self):
        reponse = self.client.get("/health/")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.json()["status"], "ok")
        self.assertTrue(reponse.json()["checks"]["db"]["ok"])

class ReglagesTests(SimpleTestCase):
    def test_csrf_lisible_par_angular(self):
        self.assertEqual(settings.CSRF_COOKIE_NAME, "XSRF-TOKEN")
        self.assertEqual(settings.CSRF_HEADER_NAME, "HTTP_X_XSRF_TOKEN")
        self.assertFalse(settings.CSRF_COOKIE_HTTPONLY)
```

- [ ] **Step 4: Lancer** `manage.py test config` → échec (projet absent).

- [ ] **Step 5: Réglages et santé.** `config/settings.py`, `sentry_filtres.py`, `wsgi.py`, `manage.py` repris de foxChess. Changements :
  - `INSTALLED_APPS` : apps Django sans `messages` ni gabarits applicatifs, puis `accounts`, `tapis`, `parties`, `rami` ;
  - CSRF pour Angular (valeurs du test ci-dessus) ; `RETENTION_PARTIES_JOURS = 30` ;
  - garder intacts la logique « sûr par défaut » (`DJANGO_DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`), la base (SQLite seulement en DEBUG, sinon `DB_*`), Sentry sans données personnelles ;
  - `config/sante.py` : celui de foxChess sans le contrôle Stockfish ;
  - `config/urls.py` : `health/`, `admin/`, et `api/` → `parties.urls` (fichier créé vide ici, `urlpatterns = []`).

- [ ] **Step 6: Lancer** `manage.py test config` → PASS ; `manage.py makemigrations --check --dry-run` → « No changes detected » ; `manage.py check` → aucune erreur ; `ruff check .` → propre.

- [ ] **Step 7: CI et Dependabot.**
  - `ci.yml` : repris de foxChess, avec `defaults.run.working-directory: backend`, la base `foxhouse`, sans Stockfish ; les jobs `tests`, `lint` et `pip-audit` ; la suite lancée par `python manage.py test -v 2`.
  - `dependabot.yml` : celui de foxChess, avec `directory: "/backend"` pour pip.

- [ ] **Step 8: `CLAUDE.md` et `README.md`.** `CLAUDE.md` décrit ce qu'est le projet (lien vers la spec), les commandes ci-dessus, et trois règles : les règles ne dépendent pas de Django ; la vue ne fuit rien ; un jeu = une app inscrite au registre. Il sera complété à la tâche 8.

- [ ] **Step 9: Commit** — `git add -A && git commit -m "Squelette FoxHouse : réglages, /health/, CI"`.

---

### Task 2: `tapis` — cartes, options, interface d'un jeu, registre, schéma de vue

**Files:**
- Create: `backend/tapis/cartes.py`, `options.py`, `jeu.py`, `registre.py`, `vue.py`
- Test: `backend/tapis/tests/test_cartes.py`, `test_options.py`, `test_registre.py`, `test_vue.py`

**Interfaces:**
- Produces, `tapis/cartes.py` :
  - `VALEURS: list[str]` (`"A"` … `"K"`), `ENSEIGNES: list[str]` (`"S","H","D","C"`) ;
  - `paquet(nb_jeux: int, nb_jokers: int) -> list[str]`, dans un ordre fixe ;
  - `melanger(cartes: list[str], graine: int) -> list[str]`, qui passe par `random.Random(graine)` et rend une nouvelle liste ;
  - `est_joker(c) -> bool`, `valeur(c) -> str`, `enseigne(c) -> str`, `nature(c) -> str` (`"10H-2"` → `"10H"`) ;
  - `decrire(c) -> dict` : `{"id","valeur","enseigne"}` ou `{"id","joker": True}` ; `CACHEE = {"cachee": True}`.
- Produces, `tapis/options.py` :
  - `@dataclass(frozen=True) Option(code, libelle, type, defaut, choix=(), minimum=None, maximum=None)`, où `type` vaut `"choix"`, `"booleen"` ou `"entier"` et `choix` est un tuple de `(valeur, libelle)` ;
  - `Option.decrire() -> dict` ;
  - `class OptionsInvalides(ValueError)` ;
  - `valider(options: list[Option], donnees: dict) -> dict`, qui complète les valeurs absentes par les valeurs par défaut.
- Produces, `tapis/jeu.py` :
  - `class CoupRefuse(Exception)`, dont le message est en français et destiné au joueur ;
  - `normaliser_coup(donnees) -> dict` : rend `{"action": str, "cartes": list[str], "cible": str | None}` et lève `CoupRefuse` si la forme est mauvaise ;
  - `class Jeu(ABC)`, avec les attributs `code`, `nom`, `min_joueurs`, `max_joueurs` et les méthodes abstraites :
    - `options() -> list[Option]` ;
    - `nouvelle_partie(options: dict, nb_joueurs: int, graine: int) -> dict` ;
    - `joueur_actif(etat) -> int | None` (`None` = partie terminée) ;
    - `appliquer(etat, joueur: int, coup: dict) -> tuple[dict, str]`, qui rend le nouvel état et un message public, ou lève `CoupRefuse` ;
    - `vue(etat, joueur: int) -> dict` ;
    - `adversaire(etat, joueur: int) -> dict`, qui rend un coup ;
  - méthode concrète `decrire() -> dict` : `{code, nom, min_joueurs, max_joueurs, options: [Option.decrire()]}`.
- Produces, `tapis/registre.py` : `inscrire(jeu)` (`ValueError` si le code existe déjà), `obtenir(code) -> Jeu` (`KeyError`), `tous() -> list[Jeu]` triés par nom, `retirer(code)` (pour les tests).
- Produces, `tapis/vue.py` : `SCHEMA = 1`, `TYPES_ZONES`, `class VueInvalide(ValueError)`, `valider_vue(vue: dict) -> None`. La vue que tout jeu doit produire :

```text
{ "schema": 1, "jeu": str, "version": int, "terminee": bool,
  "sieges": [ {"id": int, "nom": str, "actif": bool,
               "compteurs": [{"libelle": str, "valeur": str|int}]} ],      # sieges[0] = celui qui regarde
  "zones":  [ {"id": str, "type": "main"|"pile"|"combinaisons"|"pli"|"annonces"|"mises"|"communes",
               "siege": int|None,            # None = centre
               "libelle": str,
               "cartes": [carte],            # main, pile (carte du dessus), pli, communes
               "nombre": int|None,           # pile
               "groupes": [ {"id": str, "cartes": [carte], "provisoire": bool, "ciblable": bool} ] } ],
  "menu":   [ {"libelle": str, "valeur": str|int|None} ],
  "actions":[ {"id": str, "libelle": str, "cartes_min": int, "cartes_max": int,
               "cible": None|"groupe"} ],
  "resultat": None | {"titre": str, "colonnes": [str], "lignes": [[str|int]]} }
carte = {"id","valeur","enseigne"} | {"id","joker": true, "represente"?: str} | {"cachee": true}
```

- [ ] **Step 1: Écrire les tests qui échouent**, entre autres :
  - `test_paquet_rami` : `len(paquet(2, 4)) == 108`, ids uniques, `"10H-2" in`, `"JK-4" in` ;
  - `test_melanger_deterministe` : même graine → même ordre, et la liste d'origine reste inchangée ;
  - `test_nature_et_decrire` : `nature("10H-2") == "10H"`, `decrire("JK-1") == {"id": "JK-1", "joker": True}` ;
  - `test_options_par_defaut_et_refus` : une clé inconnue, un entier hors bornes, un booléen donné en chaîne et un choix hors liste lèvent `OptionsInvalides` ; `{}` rend toutes les valeurs par défaut ;
  - `test_normaliser_coup` : `{"action": "x"}` donne `cartes=[]` et `cible=None` ; `{"cartes": "7H-1"}` lève `CoupRefuse` ;
  - `test_registre` : inscrire deux fois le même code lève `ValueError`, `obtenir("inconnu")` lève `KeyError` ;
  - `test_vue_valide` / `test_vue_invalide` : un exemple minimal passe ; un type de zone inconnu, un `siege` qui ne nomme aucun siège, une carte cachée qui porte un `id` et deux groupes de même id lèvent `VueInvalide`.
- [ ] **Step 2: Lancer** `manage.py test tapis` → échecs à l'import.
- [ ] **Step 3: Implémenter** les cinq modules selon les interfaces ci-dessus.
- [ ] **Step 4: Lancer** `manage.py test tapis` → PASS ; `ruff check .` propre.
- [ ] **Step 5: Commit** — `"tapis : cartes, options, interface Jeu, registre, schéma de vue"`.

---

### Task 3: `rami.combinaisons` — suites, brelans, jokers, points

**Files:**
- Create: `backend/rami/combinaisons.py`
- Test: `backend/rami/tests/test_combinaisons.py`

**Interfaces:**
- Consumes: `tapis.cartes` (`valeur`, `enseigne`, `nature`, `est_joker`, `VALEURS`).
- Produces :
  - `@dataclass(frozen=True) Combinaison(type: str, cartes: tuple[str, ...], jokers: tuple[tuple[str, str], ...])`, où `type` vaut `"suite"` ou `"brelan"` (le carré compte comme un brelan) ;
  - `cartes` est dans l'ordre d'affichage : une suite va du bas vers le haut ;
  - `jokers` associe chaque joker à ce qu'il représente : `"7H"` pour une carte précise, `"K*"` pour « un roi d'une enseigne manquante » ;
  - `analyser(cartes: list[str], jokers_fixes: dict[str, str] | None = None) -> Combinaison | None` ;
  - `ajouter(comb: Combinaison, cartes: list[str]) -> Combinaison | None`, qui appelle `analyser` sur l'ensemble avec les jokers déjà fixés ;
  - `recuperer_joker(comb: Combinaison, carte: str) -> tuple[Combinaison, str] | None`, qui rend la nouvelle combinaison et l'id du joker libéré ;
  - `points(comb: Combinaison, regle_as: str) -> int` ;
  - `penalite(carte: str, regle_as: str, penalite_joker: int) -> int` ;
  - `vers_dict(comb) -> dict` et `depuis_dict(d) -> Combinaison`, pour l'état JSON.

Règles, d'après la spec §6.1 et §6.3 :
- Une combinaison a au moins 3 cartes, au plus 1 joker et au moins 2 cartes qui ne sont pas des jokers.
- **Brelan** : 3 ou 4 cartes de même valeur, d'enseignes toutes différentes. Un joker dans un brelan de 3 représente `"<valeur>*"` ; dans un carré, il représente l'unique enseigne manquante.
- **Suite** : même enseigne, valeurs consécutives, sans doublon de nature. L'as est en bas (A-2-3) ou en haut (Q-K-A), jamais des deux côtés à la fois ; la suite ne fait pas le tour (pas de K-A-2) et compte au plus 13 cartes.
- Un joker qui comble un trou est déterminé. Un joker à une extrémité se place **en haut** s'il le peut (5-6-JK → 7), sinon **en bas** (Q-K-JK → J, car rien n'existe au-dessus de l'as).
- `jokers_fixes` : un joker déjà posé garde ce qu'il représente. Un `"K*"` peut seulement devenir une enseigne précise quand le brelan devient carré ; tout autre changement rend `None`.
- `recuperer_joker` réussit si la carte a exactement la nature représentée, ou, pour `"K*"`, si c'est un roi d'une enseigne absente du brelan.
- **`points`** :
  - de 2 à 10, la valeur du chiffre ; J, Q et K valent 10 ; un joker vaut la carte qu'il représente ;
  - l'as dépend de la règle :
    - `"bas1_haut11"` : 1 en bas d'une suite, 11 en haut d'une suite ou dans un brelan ;
    - `"toujours1"` : 1 ;
    - `"toujours11"` : 11.
- **`penalite`** : même barème pour les cartes ordinaires. Un as en main vaut 1 avec `"toujours1"` et 11 sinon ; un joker vaut `penalite_joker`.

- [ ] **Step 1: Écrire les tests qui échouent**, avec ces cas exacts :
  - suites valides : `7H 8H 9H`, `AS 2S 3S`, `QD KD AD`, `5C 6C JK-1` (le joker vaut `"7C"`), `QC KC JK-1` (le joker vaut `"JC"`), `4H JK-1 6H` (le joker vaut `"5H"`) ;
  - refusées : `KS AS 2S`, `7H 8H` (trop courte), `7H 8H 9S`, `7H 7H 8H` (même nature en double), `5C JK-1 JK-2`, `JK-1 JK-2 JK-3`, `AS 2S … KS AS` (14 cartes) ;
  - brelans : `9S 9D 9C` valide ; `9S 9S 9D` (même enseigne) refusé ; `KH KS JK-1` (le joker vaut `"K*"`) ; `KH KS KD JK-1` (le joker vaut `"KC"`) ; 5 cartes refusées ;
  - points, d'après l'exemple de la spec : `points(7H 8H 9H) == 24`, `points(9S 9D 9C) == 27`, et `points(AS 2S 3S, "bas1_haut11") == 6`, `points(QD KD AD, "bas1_haut11") == 31`, `points(AS AH AD, "toujours1") == 3` ;
  - ajout : `ajouter(5C 6C JK(7C), [8C])` → 5-6-JK-8 ; `ajouter(5C 6C JK(7C), [7C])` → `None` (le joker ne se déplace pas) ; `ajouter(KH KS JK(K*), [KD])` → carré, le joker devient `"KC"` ;
  - récupération : `recuperer_joker(5C 6C JK(7C), "7C-2")` → 5-6-7, `"JK-1"` ; avec `"8C-1"` → `None` ; `recuperer_joker(KH KS JK(K*), "KC-1")` → réussit ; avec `"KH-2"` → `None` ;
  - pénalités : `penalite("AS-1", "bas1_haut11", 20) == 11`, `penalite("JK-2", …, 20) == 20`, `penalite("QH-1", …) == 10`.
- [ ] **Step 2: Lancer** `manage.py test rami.tests.test_combinaisons` → échec.
- [ ] **Step 3: Implémenter `combinaisons.py`.**
- [ ] **Step 4: Lancer** → PASS.
- [ ] **Step 5: Commit** — `"rami : combinaisons, jokers et points"`.

---

### Task 4: `rami` — options, état, déroulement d'une manche et des manches

**Files:**
- Create: `backend/rami/options.py`, `backend/rami/manche.py`
- Test: `backend/rami/tests/test_manche.py`

**Interfaces:**
- Consumes: `tapis.options.Option`, `tapis.cartes.paquet`/`melanger`, `rami.combinaisons.penalite`.
- Produces, `rami/options.py` : `OPTIONS: list[Option]`, dans cet ordre, avec ces codes et ces valeurs par défaut (spec §6.2) :
  - `as` (choix `bas1_haut11` « 1 en bas de suite, 11 ailleurs », `toujours1` « Toujours 1 », `toujours11` « Toujours 11 » ; `bas1_haut11`) ;
  - `ouverture_suite_sans_joker` (booléen ; `False`) ;
  - `recuperation_joker` (choix `apres_ouverture` « Après sa propre ouverture », `jamais` « Jamais » ; `apres_ouverture`) ;
  - `penalite_joker` (entier 0–50 ; `20`) ;
  - `finir_par_defausse` (booléen ; `True`) ;
  - `defausse_a_poser` (booléen ; `False`) ;
  - `manches` (entier 1–10 ; `5`).
- Produces, l'état (un `dict`) :

```text
options, graine, nb, manche (1…), premier, actif,
phase: "piocher" | "jouer" | "fin_manche" | "terminee",
pioche: [ids] (dessus = dernier), defausse: [ids] (dessus = dernier),
mains: [[ids]], ouvert: [bool],
table: [ {"id": "g1", "auteur": int, **vers_dict(comb)} ], prochain_groupe: int,
brouillon: [vers_dict(comb)]        # du joueur actif seulement
prise: id|None, joker_recupere: id|None, reconstitutions: int,
penalites: [[int par joueur] par manche]
```

- Produces, `rami/manche.py` (fonctions qui modifient l'état reçu ; c'est l'appelant qui le copie) :
  - `nouvel_etat(options: dict, nb: int, graine: int) -> dict`, qui appelle `distribuer` ;
  - `distribuer(etat) -> None` : mélange `paquet(2, 4)` avec la graine `graine * 100 + manche`, donne 13 cartes à chacun en commençant par `premier`, retourne une carte sur la défausse, puis met `phase="piocher"` et `actif=premier` ;
  - `piocher(etat, j) -> str`, `prendre_defausse(etat, j) -> str`, `defausser(etat, j, carte) -> str` : chacune rend le message public ;
  - `reconstituer_pioche(etat) -> bool` ;
  - `fin_de_manche(etat, gagnant: int | None) -> None` ;
  - `manche_suivante(etat) -> None`.

Règles :
- `defausser` passe la main au joueur suivant, `(j + 1) % nb`, en phase `piocher`, et remet `prise` et `joker_recupere` à zéro. Si la main est vide après la défausse, la manche est finie : `fin_de_manche(etat, j)`.
- Pioche vide au moment de piocher :
  - si `reconstitutions == 3` ou si la défausse n'a qu'une carte → `fin_de_manche(etat, None)` (spec §6.3) ;
  - sinon, la défausse sauf sa carte du dessus est mélangée (graine `graine * 100 + manche + 1000 * (reconstitutions + 1)`) pour refaire la pioche, et `reconstitutions` augmente de 1.
- `fin_de_manche` :
  - chacun reçoit la somme des `penalite` de sa main et de son brouillon, sauf `gagnant`, qui reçoit 0 ;
  - on ajoute cette ligne à `penalites` et on vide le brouillon ;
  - `phase="fin_manche"` si `manche < options["manches"]`, sinon `"terminee"` ;
  - `actif = 0` : c'est l'humain qui lance la manche suivante.
- `manche_suivante` : `manche += 1`, `premier = (premier + 1) % nb` ; vide la table et le brouillon, remet `ouvert` à faux et `reconstitutions` à 0, puis appelle `distribuer`.

- [ ] **Step 1: Écrire les tests qui échouent** :
  - `test_distribution` : avec 4 joueurs, chaque main a 13 cartes, la défausse 1, la pioche 108 − 52 − 1 = 55 ; aucun doublon ; même graine → même donne ;
  - `test_tour_piocher_defausser` : la main passe de 13 à 14 puis à 13, et `actif` passe au joueur suivant ;
  - `test_prendre_defausse` : la carte du dessus de la défausse arrive dans la main et `prise` la retient ;
  - `test_reconstitution_pioche` : pioche vide et défausse de 5 cartes → la pioche en reçoit 4, la défausse garde sa carte du dessus, `reconstitutions == 1` ;
  - `test_pioche_vide_defausse_d_une_carte` : la manche se termine, `penalites[-1]` a une valeur par joueur et aucune à 0 ;
  - `test_quatrieme_epuisement_finit_la_manche` : `reconstitutions = 3` et pioche vide → `phase` vaut `fin_manche` ;
  - `test_fin_de_manche_penalites` : gagnant 1 ; joueur 0 avec `AS-1 JK-1 QH-1` → 11 + 20 + 10 = 41 ; joueur 1 → 0 ;
  - `test_derniere_manche_terminee` : avec `manches=1`, la fin de manche donne `phase == "terminee"` ;
  - `test_manche_suivante_change_le_premier`.
- [ ] **Step 2: Lancer** → échec. **Step 3: Implémenter.** **Step 4: Lancer** → PASS.
- [ ] **Step 5: Commit** — `"rami : distribution, pioche, défausse, fin de manche"`.

---

### Task 5: `rami.poses` — ouverture en brouillon, ajouts, jokers

**Files:**
- Create: `backend/rami/poses.py`
- Test: `backend/rami/tests/test_poses.py`

**Interfaces:**
- Consumes: l'état de la tâche 4 ; `combinaisons.analyser`/`ajouter`/`recuperer_joker`/`points`/`vers_dict`/`depuis_dict`.
- Produces : `poser(etat, j, cartes) -> str`, `valider_ouverture(etat, j) -> str`, `annuler(etat, j) -> str`, `ajouter_a(etat, j, cartes, groupe_id) -> str`, `recuperer(etat, j, carte, groupe_id) -> str`. Chacune lève `CoupRefuse` avec un message en français.

Règles (spec §6.1, §6.3, §6.4) :
- Toutes ces fonctions demandent `phase == "jouer"` et des cartes présentes dans la main de `j`.
- `poser` :
  - si `j` n'a pas ouvert, la combinaison va dans `brouillon` ;
  - sinon elle va sur `table` avec un id `g<prochain_groupe>`, et le compteur augmente.
- `valider_ouverture` :
  - refusé si la somme des `points` du brouillon (avec `options["as"]`) est inférieure à 51 → « Il faut au moins 51 points pour ouvrir (tu en as N). » ;
  - refusé aussi si `ouverture_suite_sans_joker` est actif et que le brouillon ne contient aucune suite sans joker ;
  - sinon, le brouillon passe sur la table et `ouvert[j] = True`.
- `annuler` rend les cartes du brouillon à la main.
- `ajouter_a` et `recuperer` demandent que `j` ait ouvert. `recuperer` demande en plus `recuperation_joker == "apres_ouverture"`. Le joker récupéré va dans la main et `joker_recupere` le retient.
- **Garder une carte** : si `finir_par_defausse` est actif, toute pose ou tout ajout qui laisserait la main vide est refusé → « Garde une carte pour la défausse. ». Si l'option est inactive, une main vidée par `valider_ouverture`, par `poser` après l'ouverture ou par `ajouter_a` termine la manche : `fin_de_manche(etat, j)`.
- Règles de `defausser` qui dépendent des poses : elles sont vérifiées dans `Rami.appliquer` (tâche 6), qui appelle `annuler` avant de défausser quand le brouillon n'est pas vide :
  - refusé si `joker_recupere` est encore en main → « Utilise d'abord le joker récupéré. » ;
  - refusé si `defausse_a_poser` est actif et que `prise` est encore en main → « Pose d'abord la carte prise à la défausse. ».

- [ ] **Step 1: Écrire les tests qui échouent** :
  - `test_ouverture_51` : `7H 8H 9H` puis `9S 9D 9C` vont dans le brouillon ; la validation réussit (24 + 27 = 51) ; la table contient deux groupes ;
  - `test_ouverture_insuffisante` : avec seulement `7H 8H 9H`, la validation est refusée et le message contient « 24 » ;
  - `test_annuler_rend_les_cartes` ;
  - `test_suite_sans_joker_obligatoire` : avec l'option active, un brouillon `5C 6C JK` + brelan de rois + brelan de dames est refusé ;
  - `test_ajout_avant_ouverture_refuse` ;
  - `test_ajout_au_groupe_d_un_adversaire` : le joueur 0 a ouvert, et il ajoute `10H` au groupe `7H 8H 9H` posé par le joueur 1 ;
  - `test_recuperer_joker` : le joker passe dans la main et `joker_recupere` le retient ; l'option `jamais` le refuse ;
  - `test_garder_une_carte_pour_la_defausse` : une main de 3 cartes qui forment une suite est refusée en `poser`. Avec `finir_par_defausse=False` et un joueur déjà ouvert, la même pose termine la manche avec le joueur 0 gagnant.
- [ ] **Step 2: Lancer** → échec. **Step 3: Implémenter.** **Step 4: Lancer** → PASS.
- [ ] **Step 5: Commit** — `"rami : ouverture en brouillon, ajouts, récupération du joker"`.

---

### Task 6: `rami.jeu` et `rami.vue` — le jeu branché sur le tapis

**Files:**
- Create: `backend/rami/jeu.py`, `backend/rami/vue.py`
- Modify: `backend/rami/apps.py` (`ready()` → `registre.inscrire(Rami())`)
- Test: `backend/rami/tests/test_jeu.py`, `backend/rami/tests/test_vue.py`

**Interfaces:**
- Consumes : tâches 2 à 5.
- Produces : `class Rami(Jeu)` avec `code="rami"`, `nom="Rami 51"`, `min_joueurs=2`, `max_joueurs=6`, et `actions_permises(etat, j) -> list[dict]`, des descripteurs d'action au format de la vue. Produit aussi `rami.vue.vue(etat, j) -> dict`. `Rami.adversaire` est branché à la tâche 7 ; jusque-là, il lève `NotImplementedError`.

**Actions permises** (`id` — libellé — `cartes_min`/`cartes_max` — `cible`). Il n'y en a aucune si `actif != j`.

| Phase | Actions |
|---|---|
| `piocher` | `piocher` — « Piocher » — 0/0 ; `prendre_defausse` — « Prendre la défausse » — 0/0 |
| `jouer` | `poser` — « Poser la combinaison » — 3/13 ; `defausser` — « Défausser » — 1/1. Avant l'ouverture : `valider_ouverture` — « Valider l'ouverture » — 0/0 et `annuler` — « Annuler » — 0/0, seulement si le brouillon n'est pas vide. Après l'ouverture : `ajouter` — « Ajouter à la combinaison » — 1/12, cible `"groupe"` ; `recuperer_joker` — « Récupérer le joker » — 1/1, cible `"groupe"`, si l'option le permet |
| `fin_manche` | `manche_suivante` — « Manche suivante » — 0/0 |

`appliquer` :
- copie l'état ;
- refuse une action absente des actions permises → « Action impossible maintenant. » ;
- vérifie le nombre de cartes ;
- refuse une carte absente de la main → « Cette carte n'est pas dans ta main. » ;
- refuse un `groupe` inconnu → « Combinaison introuvable. » ;
- puis appelle la fonction de `manche` ou de `poses` qui correspond.

`joueur_actif` vaut `None` en phase `terminee`, et `etat["actif"]` sinon.

**Vue** pour le joueur `j` (schéma de la tâche 2) :
- `sieges` : de `j` à `j + nb - 1` (modulo `nb`). Noms « Toi » / « Ordinateur k ». Compteurs : « Cartes », c'est-à-dire la main plus le brouillon, pour ne rien révéler d'un brouillon ; et « Pénalités », le total.
- `zones` :
  - une `main` par siège : visible pour `j`, sinon `CACHEE` répété autant de fois que de cartes ;
  - `pile` id `pioche` : `nombre` et aucune carte ;
  - `pile` id `defausse` : `nombre` et la carte du dessus ;
  - `combinaisons` id `table` : les groupes de la table, avec `ciblable` vrai si `ajouter` ou `recuperer_joker` est permis. Si `actif == j`, on y ajoute les groupes du brouillon de `j`, avec `provisoire: true` et les ids `b0`, `b1`… Chaque joker porte un champ `represente`.
- `menu` : « Manche » (`"2 / 5"`) ; « Ouverture » (« faite » ou « pas encore ») ; « Points en attente » quand il y a un brouillon.
- `resultat` en phase `fin_manche` ou `terminee` : titre « Fin de la manche N » ou « Fin de la partie — X gagne ». Colonnes « Joueur », « Manche 1 »… « Total ». Une ligne par joueur.
- `terminee` vaut `phase == "terminee"`, et `version` vaut 0 (c'est `parties` qui la remplit).

- [ ] **Step 1: Écrire les tests qui échouent** :
  - `test_inscrit_au_registre` : `registre.obtenir("rami")` est une instance de `Rami` ;
  - `test_actions_par_phase` : les ids attendus pour chaque phase du tableau ;
  - `test_appliquer_ne_modifie_pas_l_etat` : on compare un `deepcopy` d'avant à l'état après l'appel ;
  - `test_coups_malformes_refuses` : action inconnue, carte d'une autre main, `"ZZ-9"`, groupe `"g99"`, deux cartes pour `defausser` ; chaque cas lève `CoupRefuse` ;
  - `test_vue_conforme` : `valider_vue(vue(etat, 0))` passe en phases `piocher`, `jouer` avec brouillon, `fin_manche` et `terminee` ;
  - **`test_vue_ne_fuit_rien`** : on joue 30 parties complètes (graines 1–30, de 2 à 6 joueurs), en faisant jouer tous les sièges par `adversaire` dès que la tâche 7 est faite. Jusque-là, on joue des coups `piocher`/`defausser` de la première carte. À chaque état, `json.dumps(vue(etat, 0))` ne contient :
    - aucun id d'une autre main, du brouillon d'un autre joueur ou de la pioche ;
    - ni la chaîne `"graine"`.
- [ ] **Step 2: Lancer** → échec. **Step 3: Implémenter.** **Step 4: Lancer** → PASS.
- [ ] **Step 5: Commit** — `"rami : le jeu et sa vue de table"`.

---

### Task 7: `rami.adversaire` — des adversaires qui font avancer la partie

**Files:**
- Create: `backend/rami/adversaire.py`
- Modify: `backend/rami/jeu.py` (`adversaire()` → `adversaire.choisir`), `backend/rami/tests/test_vue.py` (la fuite est testée avec de vrais adversaires)
- Test: `backend/rami/tests/test_adversaire.py`

**Interfaces:**
- Produces : `choisir(etat, j) -> dict` (un coup), déterministe, et `plan(main: list[str], regle_as: str) -> list[Combinaison]`, qui rend des combinaisons sans joker et disjointes.

Comportement (spec §6.5). Le coup choisi doit toujours être accepté par `Rami.appliquer` :
- **`plan`** : énumère les brelans (même valeur, jusqu'à 4 enseignes distinctes) et les suites maximales (par enseigne, as en bas ou en haut). Il les trie par points décroissants, puis id de la première carte, et les retient de façon gloutonne sans réutiliser une carte.
- **Phase `piocher`** : `prendre_defausse` si le joueur a ouvert et que la carte du dessus entre dans le `plan` de main + carte, ou s'ajoute à un groupe de la table, en laissant au moins 2 cartes en main. Sinon `piocher`.
- **Phase `jouer`, avant l'ouverture** :
  - si le brouillon plus le plan atteint 51 points et que le plan n'est pas vide → `poser` la première combinaison du plan, en gardant au moins une carte si `finir_par_defausse` ;
  - sinon, si le brouillon atteint 51 → `valider_ouverture` ;
  - sinon, si le brouillon n'est pas vide → `annuler` ;
  - sinon → `defausser`.
- **Phase `jouer`, après l'ouverture** : `poser` la première combinaison du plan. Sinon, `ajouter` la première carte, par id, qui va sur un groupe de la table. Sinon `defausser`. Toujours en gardant une carte si l'option l'exige.
- **Défausse** : la carte de plus forte pénalité qui n'est ni dans le plan ni un joker, et pas la carte `prise` si `defausse_a_poser` est actif. En cas d'égalité, l'id le plus petit. S'il ne reste que des jokers, un joker.
- **Phase `fin_manche`** : `manche_suivante`.
- Pas de récupération de joker.

- [ ] **Step 1: Écrire les tests qui échouent** :
  - `test_plan_trouve_suite_et_brelan` : la main `7H 8H 9H 9S 9D 9C 2C` donne deux combinaisons ; le `9H` n'est utilisé qu'une fois ;
  - `test_adversaire_ouvre` : un état où le joueur 1 a `7H 8H 9H 9S 9D 9C KS` en phase `jouer` donne la suite `poser`, `poser`, `valider_ouverture`, `defausser KS` ;
  - **`test_toutes_les_parties_finissent`** : 200 parties entre adversaires (graines 1–200, `nb = 2 + graine % 5`) et 6 jeux d'options : les valeurs par défaut, puis chaque option booléenne inversée, `as=toujours11` et `manches=2`. Chaque coup est accepté, et chaque partie atteint `terminee` en moins de 5 000 coups.
- [ ] **Step 2: Lancer** → échec. **Step 3: Implémenter.** **Step 4: Lancer** `manage.py test rami` → PASS. Le test de fuite de la tâche 6 utilise maintenant les adversaires.
- [ ] **Step 5: Commit** — `"rami : adversaires de la machine"`.

---

### Task 8: `parties` — joueur anonyme, déroulement, API, purge

**Files:**
- Create: `backend/parties/models.py` (+ migration), `joueur.py`, `deroulement.py`, `views.py`, `urls.py`, `retention.py`, `management/commands/purger_parties.py`
- Create: `backend/parties/tests/jeu_factice.py`, `test_deroulement.py`, `test_api.py`, `test_purge.py`
- Modify: `CLAUDE.md` (architecture finale, API, commandes)

**Interfaces:**
- Consumes : `tapis.registre`, `tapis.jeu` (`Jeu`, `CoupRefuse`, `normaliser_coup`), `tapis.options.valider`.
- Produces :
  - `Partie(models.Model)` : `id` UUID clé primaire, `jeu` `CharField(30)`, `joueur` `CharField(32, db_index=True)`, `etat` `JSONField`, `version` `PositiveIntegerField(default=0)`, `terminee` `BooleanField(default=False)`, `cree_le` (`auto_now_add`), `modifie_le` (`auto_now`) ;
  - `parties.joueur.jeton_du_joueur(request, creer=False)`, repris de foxChess avec `CLE_SESSION = "foxhouse_joueur"` ;
  - `deroulement.avancer(jeu, etat) -> tuple[dict, list[dict]]` et `deroulement.jouer(jeu, etat, coup) -> tuple[dict, list[dict]]`. Une étape vaut `{"message": str, "vue": dict}`. `avancer` fait jouer les adversaires tant que `joueur_actif` n'est ni 0 ni `None`, avec au plus 2 000 coups ; au-delà, `RuntimeError`. Un `CoupRefuse` d'un adversaire est un bug : il remonte, Sentry le voit et la réponse est un 500 ;
  - `parties.retention.purger() -> int` (parties non modifiées depuis `RETENTION_PARTIES_JOURS`, plus les sessions expirées), repris de foxChess.

**API** (toutes les réponses en JSON ; les erreurs ont la forme `{"erreur": "…"}` en français) :

| Méthode et chemin | Corps | Réponse |
|---|---|---|
| `GET /api/jeux/` | — | 200 `[jeu.decrire()]`. Pose le cookie CSRF (`ensure_csrf_cookie`). |
| `POST /api/parties/` | `{"jeu", "nb_joueurs", "options"}` | 201 `{"id", "vue", "etapes"}`. Supprime d'abord les parties du même joueur. Graine tirée par `secrets.randbits(31)`. Joue les adversaires si le premier joueur n'est pas l'humain. 400 si le jeu est inconnu, `nb_joueurs` hors bornes ou une option invalide. |
| `GET /api/parties/courante/` | — | 200 `{"id", "vue"}`, ou 204 s'il n'y a pas de partie. Pose le cookie CSRF. |
| `GET /api/parties/<uuid>/` | — | 200 `{"id", "vue"}` ; 404 si la partie appartient à un autre joueur ou n'existe pas. |
| `POST /api/parties/<uuid>/actions/` | `{"version", "action", "cartes", "cible"}` | 200 `{"vue", "etapes"}` et `version + 1`. 409 `{"erreur", "vue"}` si la version ne correspond pas. 400 `{"erreur", "vue"}` si le coup est refusé. 404 comme ci-dessus. |

- Une action se traite sous `transaction.atomic()` + `select_for_update()`, comme dans foxChess.
- La `vue` renvoyée porte toujours `version` = `Partie.version`.

- [ ] **Step 1: Jeu factice** (`jeu_factice.py`) : `Retourner(Jeu)`, code `"factice"`, 2 joueurs, aucune option.
  - Chaque joueur a une pile de 3 cartes. L'unique action `retourner` (0/0) pose la carte du dessus dans sa `main`, visible de tous, puis passe au joueur suivant.
  - La partie est finie après 6 coups. `adversaire` rend `{"action": "retourner"}`.
  - Les tests l'inscrivent dans `setUpClass` et le retirent dans `tearDownClass`. **Il n'utilise rien du rami** : c'est la preuve demandée par la spec §7.
- [ ] **Step 2: Écrire les tests qui échouent** :
  - `test_deroulement.py` : `jouer(Retourner(), …)` rend 2 étapes (l'humain, puis l'adversaire) ; `avancer` s'arrête sur `RuntimeError` avec un faux jeu dont l'adversaire joue sans fin.
  - `test_api.py` :
    - `test_creer_et_jouer_factice` : 201, puis 3 actions jusqu'à `vue.terminee`, puis 400 à l'action suivante ;
    - `test_creer_rami_avec_options` : `{"jeu": "rami", "nb_joueurs": 4, "options": {"manches": 2}}` → 201, 4 sièges, et `valider_vue(vue)` passe ;
    - `test_options_invalides_400`, `test_nb_joueurs_hors_bornes_400`, `test_jeu_inconnu_400` ;
    - `test_partie_d_un_autre_joueur_404` : avec un second `Client` ;
    - **`test_version_perimee_409`** : on envoie deux fois la même `version` ; la seconde reçoit 409 et la base n'a avancé que d'une version ;
    - **`test_json_illisible_400`** : le corps `"{"` → 400 ;
    - `test_courante_204_puis_200` ; `test_nouvelle_partie_remplace_l_ancienne` ;
    - `test_csrf_exige` : avec `Client(enforce_csrf_checks=True)`, un POST sans en-tête `X-XSRF-TOKEN` → 403 ; avec le cookie relu de `GET /api/jeux/` → 201.
  - `test_purge.py` : une partie modifiée il y a 31 jours est supprimée, une de 29 jours est gardée.
- [ ] **Step 3: Lancer** `manage.py test parties` → échec.
- [ ] **Step 4: Implémenter** le modèle, puis `makemigrations parties`, `joueur.py`, `deroulement.py`, les vues, `urls.py`, la rétention et la commande.
- [ ] **Step 5: Lancer** toute la suite, `manage.py test` → PASS ; `makemigrations --check --dry-run` → aucun changement ; `ruff check .` → propre.
- [ ] **Step 6: Essai de bout en bout** : lancer `runserver`. Avec `curl` et un fichier de cookies, faire `GET /api/jeux/`, `POST /api/parties/` pour le rami à 3 joueurs, puis `piocher` et `defausser` une carte. La réponse contient des étapes des deux adversaires, et c'est de nouveau à l'humain de jouer.
- [ ] **Step 7: Compléter `CLAUDE.md`** : architecture, contrat de l'API, comment ajouter un jeu (créer l'app, implémenter `Jeu`, l'inscrire dans `ready()`, l'ajouter à `INSTALLED_APPS`, ajouter son test de fuite), commande `purger_parties`.
- [ ] **Step 8: Commit** — `"parties : joueur anonyme, API, adversaires, purge"`.

---

### Task 9: Publication sur GitHub (avec l'accord de Renaud)

- [ ] **Step 1: Demander à Renaud** de confirmer explicitement la création du dépôt `Foxugly/FoxHouse`, et s'il est public ou privé. Tout le reste de la flotte est public, sauf Chronos.
- [ ] **Step 2:** `gh repo create Foxugly/FoxHouse --<visibilité> --source . --push`.
- [ ] **Step 3:** Vérifier la CI avec `gh run watch`. Les jobs `tests`, `lint` et `pip-audit` doivent être **exécutés** et réussis, pas `skipped`.
