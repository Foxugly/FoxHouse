# FoxHouse — plan 2/3 : le tapis Angular

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un frontend Angular qui affiche n'importe quelle vue de table du serveur sur un tapis ovale et permet de jouer une partie complète de rami 51, sur ordinateur et sur téléphone.

**Architecture:** Une SPA Angular 21 dans `frontend/`, en composants autonomes et signaux. Un module `tapis` générique (disposition, cartes, mains, table, menu) n'affiche que la vue reçue et ne contient aucun code propre à un jeu. Deux pages : l'accueil (choix du jeu, formulaire d'options généré, nombre de joueurs) et la partie (orchestration des actions, relecture des étapes des adversaires). Les cartes passent par un habillage interchangeable, d'abord celui de webisso/playing-cards.

**Tech Stack:** Angular 21.2.x (composants autonomes, signaux, `HttpClient`), TypeScript ~5.9, Vitest (`ng test`), angular-eslint, Prettier, `@sentry/browser`. Versions alignées sur `D:\Projects\PycharmProjects\foxugly_website\frontend\package.json`. Node 24 en local et en CI.

**Spec:** `docs/superpowers/specs/2026-10-31-foxhouse-design.md` (§3 le tapis, §4.3 la vue de table, §4.4 l'API, §5 le frontend). La maquette validée par Renaud est https://claude.ai/artifact/HpaRq9T1V5dsh9MjTPZMmH, et sa source `tapis-maquettes.html` est la référence pour le calcul de l'ovale et du chevauchement. Le contrat réel de l'API est décrit dans `CLAUDE.md`, section « API ».

## Global Constraints

- Code dans `frontend/`. Commandes lancées depuis `frontend/` : `npm ci`, `npm run lint`, `npm test` (Vitest, sans mode surveillance), `npm run build`.
- **Le tapis n'a aucun code propre à un jeu.** Le mot « rami » et les noms d'actions du rami (`piocher`, `poser`…) n'apparaissent ni dans `src/app/tapis/` ni dans `src/app/core/`. Seules les données de test peuvent les contenir.
- Le frontend n'a aucune règle. Il affiche `vue` et envoie `{version, action, cartes, cible}`. Il active un bouton seulement si `cartes_min ≤ sélection ≤ cartes_max` et si la cible demandée est choisie. Le serveur revérifie tout.
- Interface **en français**, sans i18n (spec §5). Les libellés d'actions et du menu viennent du serveur.
- Thème clair et sombre selon `prefers-color-scheme`, avec des couleurs en variables CSS. Pas de bouton de thème en v1.
- Pas de PrimeNG : la table est faite de composants sur mesure, et les quelques contrôles de l'accueil sont des éléments HTML natifs stylés.
- CSRF : Angular envoie de lui-même `X-XSRF-TOKEN` à partir du cookie `XSRF-TOKEN`, ce qui correspond aux réglages du serveur. Ne rien changer à ces noms.
- Aucune ressource externe au moment de l'exécution (CSP de la flotte) : polices système, cartes copiées dans `public/`.
- Écran de 360 px de large minimum, sans défilement horizontal de la page. Les cartes de la main restent sélectionnables au doigt.
- Messages de commit terminés par les deux lignes d'attribution de la session.

## Review Focus

1. **Double clic sur un bouton d'action** : le second envoi est bloqué côté client tant qu'une réponse est en attente. Si un 409 arrive quand même, la vue est rechargée sans message d'erreur effrayant. *(Tâche 7, `envoi unique pendant une requête`.)*
2. **Relecture des étapes interrompue** par un nouveau clic, ou par un rechargement de la page : la vue finale s'affiche toujours, et les actions restent bloquées tant que la relecture n'est pas finie ou passée. *(Tâche 7, `passer la relecture`.)*
3. **Main de 22 cartes sur un écran de 360 px** : passage sur deux rangées, et le coin de chaque carte reste visible et cliquable. *(Tâche 4, `pasCartes` ; tâche 5, `main de 22 cartes`.)*
4. **Partie sans partie en cours** (204), partie expirée ou d'un autre navigateur (404) : retour à l'accueil avec un message clair. *(Tâche 7.)*
5. **Une vue d'un autre jeu** (la vue factice) s'affiche sans erreur, ce qui prouve que le tapis est générique. *(Tâche 8.)*

---

### Task 1: Nettoyages du serveur reportés du plan 1

**Files:**
- Modify: `backend/rami/vue.py` (`actions_permises`)
- Move: la classe `BrouillonRamiTests`, de `backend/parties/tests/test_deroulement.py` vers `backend/rami/tests/test_brouillon_prive.py`
- Test: `backend/rami/tests/test_jeu.py`

**Interfaces:** aucun changement de contrat.

- [ ] **Step 1: Test qui échoue** `test_joker_recupere_masque_defausse` : tant que `joker_recupere` est dans la main du joueur actif, `actions_permises` ne propose ni `defausser` ni `rendre_defausse`, mais propose toujours `poser` et `ajouter`.
- [ ] **Step 2:** Implémenter la règle, déplacer la classe de test, puis lancer `manage.py test` (≈ 42 s) → PASS. Vérifier que `grep -r "rami" backend/parties/tests` ne trouve plus rien, hors `jeu_factice` qui n'importe pas le rami.
- [ ] **Step 3: Commit** — `"rami : pas de défausse proposée tant qu'un joker récupéré attend"`.

---

### Task 2: Squelette Angular, CI et Dependabot

**Files:**
- Create: `frontend/` avec `ng new frontend --style=scss --routing --ssr=false --skip-git`, puis :
  - `angular-eslint` et Prettier, en reprenant `eslint.config.js` et `.prettierrc` de foxugly_website ;
  - `@sentry/browser` ;
  - `proxy.conf.json` : `/api` et `/health` vers `http://127.0.0.1:8000` ;
  - le script `start` lancé avec le proxy.
- Create: `frontend/src/app/core/sentry.config.ts` et `sentry.ts`, repris de foxugly_website avec `SENTRY_DSN = ''` (le DSN arrive au plan 3).
- Create: `frontend/src/styles.scss` : variables de couleur (feutre, bord, cartes, accent, texte) en clair et en sombre, `html, body { height: 100% }`.
- Modify: `.github/workflows/ci.yml` : nouveau job `frontend` (Node 24, cache npm, `npm ci`, `npm run lint`, `npm test`, `npm run build`) avec `working-directory: frontend`.
- Modify: `.github/dependabot.yml` : écosystème `npm` dans `/frontend`, mises à jour groupées, **majeures d'Angular ignorées** comme dans la flotte.
- Modify: `.gitignore` (`frontend/node_modules`, `frontend/dist`, `frontend/.angular`).

- [ ] **Step 1:** Générer le projet et épingler les versions sur celles de foxugly_website (`@angular/*` ^21.2.25, `@angular/build` et `@angular/cli` ^21.2.28, `vitest` ^4.1.12, `typescript` ~5.9.2). Si `npm audit` signale une faille, la corriger sans changer de version majeure.
- [ ] **Step 2: Test** `app.spec.ts` : l'application démarre et affiche `<router-outlet>`. Lancer `npm test`, puis `npm run lint` et `npm run build` → tout réussit.
- [ ] **Step 3: Commit** — `"frontend : squelette Angular 21, CI, Dependabot"`.

---

### Task 3: Types de la vue, client de l'API, vues d'exemple

**Files:**
- Create: `frontend/src/app/core/vue.ts`, `frontend/src/app/core/api.service.ts`
- Create: `frontend/src/testing/vues/rami-debut.json`, `rami-brouillon.json`, `rami-fin-manche.json`, `factice.json`
- Create: `backend/tapis/tests/test_vues_du_frontend.py`
- Test: `frontend/src/app/core/api.service.spec.ts`

**Interfaces — Produces** (`core/vue.ts`) : des types TypeScript qui reflètent exactement le schéma `tapis/vue.py` :
- `Carte = CarteVisible | Joker | CarteCachee` :
  - `CarteVisible` : `{ id, valeur, enseigne }` ;
  - `Joker` : `{ id, joker: true, represente?: string }` ;
  - `CarteCachee` : `{ cachee: true }` ;
- `Siege`, `Groupe`, `Zone` (`type: 'main'|'pile'|'combinaisons'|'pli'|'annonces'|'mises'|'communes'`, `siege: number|null`), `LigneMenu`, `Action` (`cible: null|'groupe'`), `Resultat` ;
- `VueTable { schema, jeu, version, terminee, sieges, zones, menu, actions, resultat }` ;
- `Etape { message: string, vue: VueTable }` ;
- `DescriptionJeu`, `DescriptionOption`, `Coup { version, action, cartes, cible }`.

**Interfaces — Produces** (`core/api.service.ts`), dont toutes les méthodes rendent des `Observable` :
- `jeux() → DescriptionJeu[]` ;
- `creer(jeu, nbJoueurs, options) → {id, vue, etapes}` ;
- `courante() → {id, vue} | null` (un 204 donne `null`) ;
- `partie(id) → {id, vue}` ;
- `agir(id, coup) → {vue, etapes}`.

Une erreur HTTP est convertie en `ErreurApi { statut: number, message: string, vue?: VueTable }`, où le message vient de `erreur` et vaut « Le serveur ne répond pas. » quand il n'y a pas de corps.

- [ ] **Step 1: Vues d'exemple.** Les produire depuis le vrai serveur (`runserver` + `curl`) : début de partie à 4, brouillon en attente au tour de l'humain, fin de manche avec `resultat`. `factice.json` est écrit à la main : 3 sièges, une `main` par siège, une `pile` au centre, une action `retourner` 0/0.
- [ ] **Step 2: Test de contrat côté serveur** `test_vues_du_frontend` : charge chaque fichier de `frontend/src/testing/vues/` et appelle `valider_vue`. Ce test garde les exemples du frontend conformes au schéma.
- [ ] **Step 3: Tests qui échouent** (`HttpTestingController`) :
  - `courante` rend `null` sur un 204 ;
  - `agir` poste le corps exact ;
  - un 409 donne `ErreurApi{statut: 409, vue}` ;
  - une erreur réseau donne le message par défaut.
- [ ] **Step 4:** Implémenter. `provideHttpClient(withXsrfConfiguration({cookieName: 'XSRF-TOKEN', headerName: 'X-XSRF-TOKEN'}))` dans `app.config.ts`. → PASS (frontend et `manage.py test tapis`).
- [ ] **Step 5: Commit** — `"frontend : types de la vue, client de l'API, vues d'exemple"`.

---

### Task 4: Calculs de disposition et de sélection (fonctions pures)

**Files:**
- Create: `frontend/src/app/tapis/disposition.ts`, `frontend/src/app/tapis/selection.ts`
- Test: `disposition.spec.ts`, `selection.spec.ts`

**Interfaces — Produces :**
- `positionsSieges(n: number, largeur: number, hauteur: number): {x: number, y: number}[]` : l'index 0 est en bas au centre, les suivants vont dans le sens des aiguilles d'une montre à intervalles égaux sur l'ellipse. Rayons `rx = largeur/2 − max(40, 0.08·largeur)` et `ry = hauteur/2 − max(40, 0.12·hauteur)` (maquette).
- `largeurCarte(largeur: number, hauteur: number): number` : `clamp(34, min(largeur, hauteur·1.4)/15, 62)`.
- `pasCartes(nb: number, cw: number, largeurDispo: number): {pas: number, rangees: 1|2, parRangee: number}` : pas maximal `1.08·cw`, pas minimal `0.42·cw`. Si une rangée ne suffit pas avec le pas minimal, on passe à deux rangées.
- `indexRenforce(pas: number, cw: number): boolean` : vrai si `pas < 0.6·cw`. Le composant carte affiche alors un index lisible par-dessus (spec §5).
- `actionActivable(action: Action, selection: {cartes: string[], cible: string|null}): boolean`.
- `basculer(selection, idCarte)`, `choisirCible(selection, idGroupe|null)` : des fonctions pures qui rendent une nouvelle sélection.

- [ ] **Step 1: Tests qui échouent :**
  - `positionsSieges(4, 1000, 600)` place le siège 0 en `(500, y_bas)`, le siège 2 en haut et le siège 1 à gauche ;
  - avec 1 à 10 sièges, toutes les positions sont dans le rectangle ;
  - `pasCartes(7, 50, 600).rangees == 1` ;
  - `pasCartes(22, 40, 330)` donne 2 rangées, avec un pas d'au moins `0.42·40·0.8` (règle de la maquette en deux rangées) ;
  - `actionActivable` sur une action 3/13 : faux avec 2 cartes, vrai avec 3. Sur une action à cible `groupe` : faux sans cible ;
  - `basculer` ajoute puis retire une carte.
- [ ] **Step 2:** Implémenter → PASS. **Step 3: Commit** — `"tapis : disposition de la table et sélection"`.

---

### Task 5: Cartes, habillage webisso et mains superposées

**Files:**
- Create: `frontend/public/cartes/webisso/` : les 54 SVG de https://github.com/webisso/playing-cards (dossier `svg/`), plus son `LICENSE` (MIT) copié tel quel. Ne pas copier les variantes `*2.svg`.
- Create: `frontend/src/app/tapis/habillage.ts`, `tapis/carte/carte.component.{ts,html,scss}`, `tapis/main/main.component.{ts,html,scss}`
- Test: `habillage.spec.ts`, `carte.component.spec.ts`, `main.component.spec.ts`

**Interfaces — Produces :**
- `interface Habillage { nom: string; image(carte: CarteVisible | Joker): string; }` ;
- `HABILLAGE_WEBISSO` : les valeurs `A J Q K` deviennent `ace jack queen king`, les chiffres restent ; les enseignes `S H D C` deviennent `spades hearts diamonds clubs`. `JK-1` et `JK-3` donnent `black_joker`, `JK-2` et `JK-4` `red_joker`. Exemples : `/cartes/webisso/10_of_hearts.svg`, `/cartes/webisso/queen_of_spades.svg`.
- Le jeton d'injection `HABILLAGE` vaut par défaut `HABILLAGE_WEBISSO`. Changer de jeu de cartes = fournir un autre `Habillage`.
- `<app-carte [carte] [largeur] [indexRenforce] [selectionnee] [provisoire]>` :
  - une carte cachée affiche un dos dessiné en CSS (motif aux couleurs du site) ;
  - une carte visible affiche l'image avec un `alt` lisible (« 10 de cœur », « joker ») ;
  - un joker qui a `represente` porte un petit badge de la carte remplacée ;
  - avec `indexRenforce`, un index (valeur + symbole) s'affiche dans le coin.
- `<app-main [cartes] [largeurDispo] [cw] [selectionnable] [selection] (basculer)>` : place les cartes en absolu avec `pasCartes`. Une carte sélectionnée se soulève. Une carte se sélectionne au clic, ou au clavier avec Entrée ou Espace (`tabindex=0`, `role="button"`, `aria-pressed`).

- [ ] **Step 1: Tests qui échouent :**
  - `HABILLAGE_WEBISSO.image` donne les chemins ci-dessus et les deux jokers ;
  - chaque fichier visé existe dans `public/cartes/webisso/`, vérifié par un test Node avec `fs` ;
  - une carte cachée n'a pas d'`<img>` ;
  - **main de 22 cartes** dans 330 px : chaque carte reste dans la boîte, sur 2 rangées, et `indexRenforce` est vrai ;
  - un clic émet `basculer('7H-1')` ;
  - la touche Entrée fait de même.
- [ ] **Step 2:** Implémenter → PASS. **Step 3: Commit** — `"tapis : cartes webisso, habillage interchangeable, mains superposées"`.

---

### Task 6: La table et le menu

**Files:**
- Create: `frontend/src/app/tapis/table/table.component.{ts,html,scss}`, `tapis/menu/menu.component.{ts,html,scss}`
- Test: `table.component.spec.ts`, `menu.component.spec.ts`

**Interfaces — Produces :**
- `<app-table [vue] [selection] (basculer) (choisirCible)>` :
  - table ovale qui occupe son conteneur, mesuré par `ResizeObserver` ;
  - chaque siège est placé par `positionsSieges` : nom (mis en avant si `actif`) et compteurs ;
  - les zones `main` sont posées sur leur siège. La main de `sieges[0]` est sélectionnable seulement si `vue.actions` contient une action avec `cartes_max > 0` ;
  - les zones à `siege: null` sont au centre, dans l'ordre reçu :
    - `pile` : la carte du dessus, ou un dos, plus le nombre ;
    - `combinaisons` : un bloc par groupe. Un groupe `provisoire` est tireté et marqué « en attente ». Un groupe `ciblable` se choisit au clic ; recliquer le désélectionne ;
  - les types `pli`, `annonces`, `mises` et `communes` reçoivent un rendu générique : un libellé et les cartes en ligne, sans logique propre ;
  - si `vue.resultat` existe, un panneau superposé montre le titre et le tableau.
- `<app-menu [vue] [selection] [occupe] (agir)>` : les lignes `menu` (libellé, valeur), puis un bouton par action. Un bouton est actif si `actionActivable(...)` est vrai et `!occupe`. Le clic émet l'`Action`.
- Mise en page de la page de partie : la table à gauche et le menu à droite au-delà de 760 px ; en dessous, le menu passe au-dessus (maquette).

- [ ] **Step 1: Tests qui échouent**, avec `rami-debut.json` et `rami-brouillon.json` :
  - 4 sièges sont rendus et le siège actif est mis en avant ;
  - la main du joueur est cliquable, celle des autres ne l'est pas ;
  - un groupe provisoire porte la classe « en attente » ;
  - un clic sur un groupe ciblable émet `choisirCible('g1')` ;
  - le menu désactive « Poser la combinaison » avec 2 cartes et l'active avec 3 ;
  - avec `rami-fin-manche.json`, le panneau du résultat affiche ses lignes.
- [ ] **Step 2:** Implémenter → PASS. **Step 3: Commit** — `"tapis : table ovale, zones du centre, menu d'actions"`.

---

### Task 7: Pages — accueil et partie

**Files:**
- Create: `frontend/src/app/pages/accueil/accueil.page.{ts,html,scss}`, `pages/partie/partie.page.{ts,html,scss}`, `pages/partie/relecture.ts`
- Modify: `app.routes.ts` (`''` → accueil, `'partie'` → partie, `'**'` → accueil)
- Test: `accueil.page.spec.ts`, `partie.page.spec.ts`, `relecture.spec.ts`

**Comportement :**
- **Accueil :**
  - charge `jeux()` et `courante()` ;
  - s'il existe une partie en cours, affiche « Reprendre la partie » ;
  - sinon, affiche la liste des jeux (pour l'instant le seul rami, présenté de façon générique) ;
  - le formulaire d'options est **généré** : `choix` donne un `<select>`, `booleen` une case à cocher, `entier` un champ numérique borné. S'y ajoute un « Nombre de joueurs » borné par `min_joueurs`/`max_joueurs`, et la valeur par défaut est le minimum + 1 ;
  - « Commencer » appelle `creer`, puis navigue vers `/partie` en passant les étapes à rejouer ;
  - les erreurs 400 s'affichent sous le formulaire.
- **Partie :**
  - charge `courante()`. Si la réponse est `null` ou 404, retour à l'accueil avec « Aucune partie en cours. » ;
  - garde les signaux `vue`, `selection`, `occupe` et `erreur` ;
  - `agir(action)` envoie `{version: vue.version, action: action.id, cartes, cible}`, met `occupe` à vrai et vide la sélection après la réponse ;
  - un 400 affiche `erreur` et la `vue` reçue ;
  - un 409 recharge simplement la vue reçue, sans message.
- **Relecture** (`relecture.ts`, fonction pure plus une minuterie) :
  - les étapes s'affichent une à une : chaque `message` dans un bandeau et sa `vue` sur la table, une étape toutes les 700 ms ;
  - un bouton « Passer » ou un nouveau clic sur la table saute directement à la vue finale ;
  - les actions restent bloquées pendant la relecture.
- « Nouvelle partie » dans le menu de la page renvoie à l'accueil, après confirmation dans la page elle-même.

- [ ] **Step 1: Tests qui échouent** (`HttpTestingController` et minuteries simulées) :
  - le formulaire est généré depuis `DescriptionJeu`, et `creer` reçoit les valeurs ;
  - « Reprendre » apparaît quand `courante` rend une partie ;
  - **envoi unique pendant une requête** : deux clics ne donnent qu'un seul `POST` ;
  - un 409 met à jour la vue sans afficher d'erreur ; un 400 affiche le message ;
  - **passer la relecture** : avec 3 étapes, « Passer » affiche la vue finale et débloque les actions ;
  - un 204 sur la partie renvoie à l'accueil.
- [ ] **Step 2:** Implémenter → PASS. **Step 3: Commit** — `"frontend : accueil, partie, relecture des étapes"`.

---

### Task 8: Preuve de généricité et essai de bout en bout

**Files:**
- Test: `frontend/src/app/tapis/genericite.spec.ts`
- Modify: `CLAUDE.md` (section frontend : commandes, architecture, habillage), `README.md`

- [ ] **Step 1: `genericite.spec.ts`** :
  - `<app-table>` et `<app-menu>` rendent `factice.json` sans erreur, et l'action « retourner » est cliquable ;
  - un test lit les fichiers de `src/app/tapis/` et `src/app/core/` (avec `fs`) et vérifie qu'aucun ne contient `rami`, `piocher`, `poser`, `defausse` ni `brouillon`.
- [ ] **Step 2: Essai réel.** Lancer le serveur (`runserver`) et `npm start`, puis jouer avec Playwright :
  - créer un rami à 3 joueurs, piocher, défausser, regarder la relecture des adversaires, puis jouer jusqu'à une fin de manche (options `manches=1`) ;
  - faire des captures d'écran sur ordinateur (1280×800) et sur téléphone (390×844), en clair et en sombre ;
  - vérifier qu'il n'y a aucune erreur dans la console et que la page ne défile pas sur le côté ;
  - corriger ce qui casse, puis enregistrer les captures dans `docs/captures/`.
- [ ] **Step 3:** Compléter `CLAUDE.md` et `README.md`, puis lancer `npm run lint && npm test && npm run build` et `manage.py test` → tout réussit.
- [ ] **Step 4: Commit** — `"tapis : preuve de généricité, essai de bout en bout, documentation"`.
