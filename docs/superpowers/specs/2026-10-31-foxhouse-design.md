# FoxHouse — conception

*31 octobre 2026. Rédigé à partir d'une discussion avec Renaud. Ce qui vient de lui est signalé comme
tel ; le reste est marqué **(choix de conception)** et peut être contesté.*

## 1. Intention

FoxHouse est un site de jeux de cartes (`foxhouse.foxugly.com`) où l'on joue **seul contre des
joueurs gérés par la machine**. Il doit accueillir à terme beaucoup de jeux — Texas hold'em, whist,
belote, dame de pique, président, rami, blackjack… — ajoutés **un par un** (Renaud : « scalable et
incrémental »).

La pièce maîtresse est le **tapis de jeu** : un environnement d'affichage commun, « suffisamment
souple et simple pour s'adapter aux différentes configurations de jeu » (Renaud). C'est sur lui que
s'affichent les joueurs, les cartes, les plis, les annonces et les mises. Les jeux se branchent sur le
tapis ; le tapis ne connaît aucune règle.

Le premier jeu est le **rami 51**, choisi par Renaud. Il sert d'abord à mettre le tapis à l'épreuve.

Maquette validée par Renaud (« J'aime bien ») : https://claude.ai/artifact/HpaRq9T1V5dsh9MjTPZMmH

## 2. Objectifs, non-objectifs, anti-objectifs

**Objectifs de la première version**
- Un tapis Angular générique, piloté uniquement par une description de table envoyée par le serveur.
- Un moteur Django générique dans lequel un jeu se branche en fournissant ses règles et ses options.
- Le rami 51 complet, jouable de la première distribution au classement final, contre 1 à 5
  adversaires de la machine.
- En production sur `foxhouse.foxugly.com`, selon les conventions de la flotte (§8).

**Critère de réussite (choix de conception — Renaud n'a pas précisé)** : sur ordinateur et sur
téléphone, on ouvre le site, on choisit le rami, ses options et le nombre de joueurs, on joue une
partie entière jusqu'au tableau des scores ; un rechargement en cours de partie la reprend où elle
était.

**Non-objectifs (pour l'instant)**
- Une vraie intelligence artificielle : Renaud : « On ne s'occupe pas de cette partie là maintenant. »
  Les adversaires jouent des coups permis, sans stratégie (§6.5).
- Les comptes : Renaud : « Pas pour le moment. »
- L'apparence personnalisable des cartes et du tapis : Renaud : « oui plus tard ».
- Les autres jeux. L'architecture doit les permettre sans toucher au tapis, mais aucun n'est livré.
- Le jeu entre humains et le temps réel. **Évolution prévue** (Renaud : « Potentiellement les
  adversaires pourraient être des humains ») : rien ne doit la fermer. Concrètement, dès la première
  version, une partie sait **qui occupe chaque siège** (un humain identifié ou la machine) et le
  serveur fait jouer la machine tant que c'est le tour d'un siège machine ; la vue est toujours
  calculée pour le siège de celui qui la demande. Le jour venu, il restera à ajouter l'invitation à
  une table et un canal WebSocket (daphne + Channels, comme Poker et Facilitation) qui pousse cette
  même vue à chaque joueur.
- Les statistiques, le classement public.

**Anti-objectifs — ce qui serait un échec même si ça marche**
- Du code propre au rami dans le tapis Angular (un composant « RamiTable », un `if jeu == 'rami'`).
  Le jour où l'on branche la belote, le tapis ne doit pas changer.
- Le navigateur qui reçoit des informations qu'il ne devrait pas voir : cartes des adversaires,
  ordre de la pioche, graine du mélange. Ouvrir les outils du navigateur ne doit pas permettre de
  tricher.
- Une table inutilisable sur téléphone : cartes illisibles, impossibles à sélectionner, ou page qui
  défile sur le côté.

## 3. Le tapis (décidé avec Renaud)

- **L'écran est la table** : un ovale qui occupe tout l'espace disponible. Le joueur humain est
  toujours en bas ; les autres sièges sont répartis à intervalles égaux autour de l'ovale, dans le
  sens des aiguilles d'une montre. Le nombre de joueurs varie (Renaud : « disposés en cercle. Le
  nombre de joueurs peut varier »).
- **Un menu contextuel** à droite sur grand écran, au-dessus sur écran étroit (Renaud : « Ok pour un
  menu à droite ou au-dessus en fonction du contexte »). Il affiche l'état du jeu (atout, pot,
  scores…) et les boutons d'action.
- **Cartes superposées** autant que la place le permet, mais toujours identifiables et
  sélectionnables (Renaud : « superposer les cartes, tout en pouvant les différencier et les
  identifier/sélectionner en fonction de l'espace disponible »). Le pas entre deux cartes est
  calculé d'après la largeur disponible, sans jamais descendre sous un minimum qui laisse lire le
  coin (valeur et enseigne) ; au-delà, la main passe sur deux rangées. La maquette en donne un
  calcul de départ.
- **La sélection** se fait au clic ou au clavier ; une carte sélectionnée se soulève.

**Catalogue des zones** (choix de conception, illustré dans la maquette) — c'est le seul vocabulaire
que le tapis connaît :

| Zone | Contenu | Où le tapis la place |
|---|---|---|
| `siege` | un joueur : nom, tour actif, compteurs libres (cartes, points, solde…) | sur l'ovale |
| `main` | les cartes d'un joueur ; chaque carte visible ou cachée | sur son siège ; un siège peut en avoir plusieurs |
| `pile` | pioche ou défausse : nombre de cartes et carte du dessus si visible | au centre |
| `combinaisons` | des groupes de cartes posés, chacun ciblable | au centre (au rami) |
| `pli` | une carte par joueur, orientée vers celui qui l'a jouée | au centre |
| `annonces` | atout, contrat, enchères : texte et symboles | dans le menu |
| `mises` | jetons, pot, solde | au centre ou sur le siège |
| `communes` | cartes communes (hold'em) | au centre |

Le jeu ne donne **jamais de coordonnées** : il dit quelles zones existent, à quel siège elles
appartiennent ou si elles sont au centre, et dans quel ordre. Le tapis calcule la disposition. Seuls
`siege`, `main`, `pile`, `combinaisons` et le menu sont nécessaires au rami ; les autres types sont
décrits pour vérifier que le format tient, et peuvent être implémentés au moment où un jeu en a
besoin.

## 4. Architecture

**Pile technique** (Renaud : « une stack alignée sur la flotte : angular et django »). Angular 21
(la flotte ignore les montées de version majeure d'Angular) et Django 6.x avec PostgreSQL.
**Un seul dépôt `Foxugly/FoxHouse`** avec `backend/` et `frontend/` (choix de conception, accepté par
Renaud : « Ok go »), comme Fabric.

**Principe** : toute la logique de jeu est sur le serveur. Le navigateur ne fait qu'afficher une
**vue de table** et renvoyer des **actions**. Les adversaires de la machine jouent sur le serveur.

### 4.1 Les apps Django (décidé avec Renaud)

**Chaque jeu est une app Django.** Le projet (réglages dans `config/`, comme foxChess) contient :

```
backend/
  config/          réglages du projet (settings, urls, /health/)
  tapis/           le commun : interface d'un jeu, registre, format de la vue, brouillon de tour
  parties/         modèle Partie, API, session anonyme, tour des adversaires
  rami/            le premier jeu
    apps.py        s'inscrit au registre dans AppConfig.ready()
    regles.py      les règles, en Python pur
    options.py     les variantes et leurs valeurs par défaut
    vue.py         ce que chaque joueur voit de la table
    adversaire.py  le coup d'un joueur de la machine
    tests/
```

Une app de jeu n'a **ni modèle, ni migration, ni vue HTTP** : l'état de la partie est stocké par
`parties` (JSON) et l'API est commune. Ajouter un jeu = créer son app et l'ajouter à
`INSTALLED_APPS` ; l'en retirer fait disparaître le jeu. Ni `parties` ni le tapis Angular ne
changent.

### 4.2 L'interface d'un jeu

Chaque app de jeu implémente une interface commune définie dans `tapis`. Le code des règles ne
dépend pas de Django (testable sans base de données) :

- `options` : la liste des options de la variante, avec types, bornes et valeurs par défaut
  (sert à générer le formulaire de création de partie).
- `nouvelle_partie(options, joueurs, graine) → état`
- `actions_permises(état, joueur) → [action]`
- `appliquer(état, joueur, action) → (état, [événement])` — refuse toute action non permise.
- `vue(état, joueur) → vue de table` — ne contient **que** ce que ce joueur a le droit de voir.
- `adversaire(état, joueur) → action` — le coup d'un joueur de la machine (§6.5).
- `terminee(état)`, `scores(état)`.

L'état est un document JSON sérialisable, sauvé tel quel. Le mélange utilise une graine stockée
dans l'état, pour pouvoir rejouer une partie dans les tests et en cas de bug.

### 4.3 La vue de table (le contrat entre serveur et tapis)

Format JSON versionné. Le serveur l'envoie après chaque action. Elle contient :

- `sieges` : dans l'ordre de jeu, en commençant par le joueur humain ; pour chacun nom, tour actif,
  compteurs à afficher.
- `zones` : chaque zone avec son type (§3), son propriétaire (un siège ou le centre), son contenu.
- `cartes` : une carte visible est `{id, valeur, enseigne}` ou un joker ; une carte cachée est
  `{cachee: true}` **sans identifiant stable** (sinon on pourrait suivre une carte d'une main à
  l'autre). Les identifiants des cartes visibles distinguent les deux paquets (`7C-1`, `7C-2`).
- `menu` : lignes de contexte (texte court, éventuellement une valeur mise en avant).
- `actions` : les actions possibles maintenant, chacune avec un identifiant, un libellé, et ses
  **contraintes de sélection** : nombre de cartes de la main (min, max), et éventuellement une
  cible (une zone ou un groupe de `combinaisons`). Le tapis active un bouton seulement quand la
  sélection respecte ses contraintes ; le serveur revérifie tout de toute façon.
- `version` : un compteur qui augmente à chaque action, pour refuser une action envoyée sur un état
  périmé (double clic, deux onglets).

### 4.4 API (choix de conception)

- `GET /api/jeux/` — jeux disponibles et leurs options.
- `POST /api/parties/` — crée une partie (jeu, options, nombre d'adversaires) → vue.
- `GET /api/parties/courante/` — la partie en cours de cette session, s'il y en a une.
- `GET /api/parties/{id}/` → vue.
- `POST /api/parties/{id}/actions/` `{version, action, cartes, cible}` → les événements qui ont
  suivi (l'action du joueur, puis les coups des adversaires jusqu'à son prochain tour) et la vue
  finale. Le tapis rejoue les événements avec un court délai, pour qu'on voie les adversaires jouer.
- `GET /health/`.

Pas de WebSocket : il n'y a qu'un seul humain par partie, chaque requête renvoie tout ce qui s'est
passé jusqu'à son prochain tour.

### 4.5 Sans compte

Une partie est rattachée à la **session Django anonyme** (cookie). Recharger la page la reprend ;
changer d'appareil ou effacer ses cookies la perd. Une session n'a qu'une partie en cours ; en créer
une nouvelle abandonne l'ancienne. Les parties abandonnées ou inactives depuis 30 jours sont
supprimées par une commande planifiée (choix de conception).

## 5. Le frontend

- Un module `tapis` générique : la table ovale, les sièges, les mains superposées, les zones du
  centre, le menu, la sélection, la relecture des événements. **Aucun composant propre à un jeu.**
- Un écran d'accueil : choix du jeu, formulaire d'options généré depuis `GET /api/jeux/`, nombre de
  joueurs.
- Un écran de fin de manche et de fin de partie (tableau des scores), lui aussi générique : la vue
  de table peut porter un `resultat` (lignes et colonnes) que le tapis affiche par-dessus la table.
- Pour ajouter une carte à une combinaison posée : sélectionner la ou les cartes, puis cliquer sur le
  groupe visé. Pas de glisser-déposer dans la première version (choix de conception).
- Interface en français ; le texte de la vue (libellés d'actions, menu) vient du serveur.
- **Dessin des cartes (décidé par Renaud)** : on commence avec le jeu SVG
  [webisso/playing-cards](https://github.com/webisso/playing-cards) (licence MIT, 54 cartes). Les
  images sont copiées dans le frontend avec leur licence, jamais chargées depuis GitHub (CSP de la
  flotte). Il n'a que deux jokers : `JK-1`/`JK-3` noirs, `JK-2`/`JK-4` rouges. Il n'a pas de dos :
  celui-ci est dessiné par le site. Un seul composant `carte` affiche une carte à partir de son
  identifiant à travers un **habillage** (dossier d'images + correspondance), pour pouvoir changer
  de jeu de cartes plus tard sans toucher au tapis. À vérifier sur téléphone : si l'index devient
  illisible quand les cartes se chevauchent, le site superpose un index plus grand.

## 6. Le rami 51

Règles fournies par Renaud (« Règles du rami classique (51 points) »), reprises ici.

### 6.1 Règles fixes
- 2 jeux de 52 cartes et 4 jokers (108 cartes). De 2 à 6 joueurs. 13 cartes chacun.
- Le reste forme la pioche, face cachée ; une carte est retournée pour commencer la défausse.
- On joue dans le sens des aiguilles d'une montre. Un tour : piocher (pioche ou carte visible de la
  défausse), poser éventuellement, se défausser d'une carte face visible.
- **Suite** : au moins 3 cartes consécutives de la même enseigne. **Brelan ou carré** : 3 ou 4
  cartes de même valeur, d'enseignes différentes. Un joker remplace une carte manquante.
- **Première pose** : au moins 51 points posés en une seule fois. 2 à 10 : leur valeur ; valet,
  dame, roi : 10 ; joker : la valeur de la carte qu'il remplace.
- **Après la première pose** : poser de nouvelles combinaisons, compléter celles de la table (y
  compris celles des adversaires), récupérer un joker en le remplaçant par la carte correspondante.
  Plus de minimum de 51 points.
- **Fin de manche** : quand un joueur n'a plus de cartes. Les autres comptent les cartes qui leur
  restent en main comme pénalités ; celui qui termine n'en a aucune.
- **Fin de partie** : pénalités additionnées manche après manche ; le moins de points gagne.

### 6.2 Options de la variante
Renaud a listé les règles « à convenir avant de jouer ». Elles deviennent des options choisies à la
création de la partie. **Les valeurs par défaut sont des choix de conception** :

| Option | Valeurs | Par défaut |
|---|---|---|
| Valeur de l'as | « 1 en bas de suite, 11 ailleurs » / « toujours 1 » / « toujours 11 » | 1 en bas de suite (A-2-3), 11 ailleurs (Q-K-A, brelan d'as) |
| Suite sans joker obligatoire pour ouvrir | oui / non | non |
| Récupération d'un joker | après sa propre ouverture / jamais | après sa propre ouverture, contre la carte exacte qu'il représente |
| Joker resté en main | points | 20 |
| Terminer par une défausse | obligatoire / facultatif | obligatoire |
| Carte prise à la défausse à poser dans le tour | oui / non | non |
| Nombre de manches | 1 à 10 | 5 |

### 6.3 Points laissés ouverts par les règles et tranchés ici (choix de conception)
- Une suite ne fait pas le tour (pas de K-A-2). Un as en main compte 11 en pénalité (1 si l'option
  « toujours 1 » est choisie).
- Au plus un joker par combinaison.
- Pas de brelan de jokers ; une combinaison contient au moins deux cartes qui ne sont pas des jokers.
- Quand on récupère un joker, il doit être utilisé dans une pose pendant le même tour.
- Si la pioche est vide, la défausse sauf sa carte du dessus est mélangée pour refaire la pioche.
- Si la carte retournée au départ est un joker, elle reste la carte du dessus de la défausse.
- Avec « terminer par une défausse » obligatoire, on ne peut pas poser toutes ses cartes sans en
  garder une à défausser.
- Le premier joueur change à chaque manche (le suivant dans le sens des aiguilles d'une montre).
- **Ce que représente un joker**, fixé au moment de la pose et affiché sur la table :
  - dans un brelan, il représente « l'une des enseignes manquantes » ; n'importe laquelle de ces
    cartes permet de le récupérer ; dans un carré il est entièrement déterminé ;
  - au milieu d'une suite, il est déterminé par ses voisines ;
  - à une extrémité d'une suite (5-6-joker), il est placé **en haut** si c'est possible (le 7),
    sinon en bas ; c'est cette lecture qui compte pour les 51 points. Rien n'empêche ensuite de
    compléter la suite par le bas.
- **Garde-fou contre une manche sans fin** : si la pioche a déjà été reconstituée 3 fois et se vide
  encore, la manche s'arrête et chacun compte ses pénalités, sans gagnant de manche. Une partie
  normale n'arrive jamais jusque-là ; la règle existe surtout pour que les parties entre adversaires
  de la machine se terminent toujours.

### 6.4 Poser l'ouverture (décidé par Renaud)
Renaud a choisi de poser les combinaisons de l'ouverture **une par une, en attente** :
- tant que le joueur n'a pas ouvert, « Poser la combinaison » place le groupe sur la table, marqué
  « en attente » (affichage distinct, total des points en attente dans le menu) ;
- « Valider l'ouverture » n'est permis que si le total en attente atteint 51 (et respecte l'option
  « suite sans joker ») ; les groupes deviennent alors définitifs ;
- « Annuler » rend toutes les cartes en attente à la main ; se défausser sans avoir validé fait de
  même avant la défausse ;
- après l'ouverture, une pose est définitive tout de suite.

Côté contrat, c'est un **brouillon de tour** générique : l'état peut porter des éléments provisoires,
la vue les marque `provisoire: true`, et les actions de brouillon (poser, annuler, valider) passent
par le même mécanisme d'actions et de contraintes que les autres. Chacune fait avancer `version`.
Le brouillon n'est jamais visible des autres joueurs ni rejoué comme événement des adversaires.
D'autres jeux pourront s'en servir pour un coup en plusieurs étapes.

### 6.5 Les adversaires (première version)
Pas de stratégie, mais ils doivent faire avancer la partie : piocher, ouvrir dès qu'ils trouvent 51
points dans leur main, compléter les combinaisons quand ils le peuvent, défausser leur carte la plus
chère qui n'appartient à aucune combinaison possible. Le choix est déterministe à partir de la graine
de la partie. L'interface `adversaire()` permettra de les remplacer plus tard.

## 7. Tests

- Le moteur du rami, sans Django : validité des suites et brelans (jokers, as), calcul des 51 points,
  ajout à une combinaison, récupération d'un joker, pioche épuisée, fin de manche, scores, chaque
  option.
- **Fuite d'information** : pour chaque état d'une partie rejouée, la vue d'un joueur ne contient ni
  les cartes des autres, ni la pioche, ni la graine.
- Une partie complète entre adversaires de la machine se termine toujours (sur de nombreuses graines).
- **Le contrat du tapis** : un jeu factice minimal, présent uniquement dans les tests, produit une vue
  de table que le frontend affiche sans code spécifique — c'est la preuve que le tapis est générique.
- Frontend : calcul des positions sur l'ovale et du chevauchement des cartes ; activation des
  boutons selon les contraintes de sélection.

## 8. Mise en production (conventions de la flotte)

Selon le CLAUDE.md global et `OPERATIONS.md` (`Foxugly/foxugly-ops`), avec `quizonline` comme
référence :
- vhost `foxhouse.foxugly.com`, gunicorn sur **8013** (prochain port libre), frontend servi en
  statique par nginx ; pas de Redis (rien à mettre en cache ni de tâches en arrière-plan) ;
- secrets dans SSM `/foxhouse/prod` → `/run/foxhouse/.env` ; unités systemd durcies sur le modèle de
  Facilitation ; base PostgreSQL `foxhouse`, reprise automatiquement par les sauvegardes de la flotte ;
- Sentry `foxhouse-backend` et `foxhouse-frontend`, sans données personnelles ; une sonde UptimeRobot ;
- CI (PostgreSQL en étapes depuis ECR et en cache), `deploy.yml` par OIDC avec le rôle
  `foxhouse-deploy`, Dependabot, protection de `main` et fusion automatique des PR Dependabot ;
- mise à jour de `OPERATIONS.md` et du CLAUDE.md global (tableau de la flotte, port suivant 8014).

Les étapes hors dépôt (DNS, certificat, rôle IAM, paramètres SSM, unités systemd, sudoers) touchent
la production : chacune est soumise à l'accord explicite de Renaud au moment de la faire.

## 9. Laissé au constructeur

- L'outillage API (Django REST Framework ou autre) et la structure interne des applications Django.
- Le détail visuel : typographie, couleurs, animations, dessin des cartes. Partir de la maquette.
- L'ordre de construction, tant que le tapis reste générique dès le début.
- Le nom exact des champs JSON de la vue de table, à figer dans un schéma partagé et testé des deux
  côtés.
