# FoxHouse — 8 américain, dame de pique, président

*31 octobre 2026. Renaud a demandé ces trois jeux et laissé les règles à mon choix (« tu peux les
attaquer directement sans me demander mon go »). Tout ce qui suit est donc un **choix de conception**,
pris parmi les règles françaises les plus courantes, et peut être contesté.*

S'applique à chaque jeu, comme au rami (spec FoxHouse §4, CLAUDE.md « Ajouter un jeu ») :

- une app Django (`huit`, `dame`, `president`) dont les règles n'importent pas Django ; elle
  implémente `tapis.jeu.Jeu` et s'inscrit au registre dans `ready()` ;
- un jeu de 52 cartes, sans joker sauf mention contraire ; graine de 128 bits ;
- la vue d'un joueur ne fuit rien : ni les mains des autres, ni la pioche, ni la graine. Chaque jeu
  a son test de fuite ;
- **aucun changement du tapis Angular ni de `parties/`.** Les zones existantes suffisent : `main`,
  `pile`, `pli` au centre, et une zone de siège (`siege` renseigné, autre que `main`) pour la carte
  qu'un joueur vient de jouer. Si l'affichage ne convient vraiment pas, le dire, ne pas le contourner ;
- les adversaires jouent un coup permis selon une heuristique simple (§1.5, §2.5, §3.5), sans prétention
  d'intelligence ;
- un test rejoue des parties complètes entre machines sur de nombreuses graines et plusieurs jeux
  d'options : chaque partie se termine, chaque vue passe `valider_vue` ;
- toute partie se joue en manches et finit sur un tableau des scores (`resultat`), comme le rami ;
- textes en français, tutoiement du joueur humain, comme `rami/manche.py` (`_verbe`, `nom_joueur`).

## 1. Le 8 américain (`huit`)

### 1.1 Règles

- 2 à 6 joueurs. 1 paquet jusqu'à 4 joueurs, 2 paquets à 5 et 6.
- Chacun reçoit 8 cartes (7 à partir de 5 joueurs). Le reste forme la pioche ; on retourne la première
  carte pour commencer la défausse. Si c'est un 8, on la remet au milieu de la pioche et on en
  retourne une autre.
- Le joueur à gauche du donneur commence. Le donneur tourne à chaque manche.
- À son tour, on pose **une** carte de même couleur ou de même valeur que la carte du dessus
  (ou que la couleur annoncée après un 8). Un 8 se pose sur n'importe quoi ; celui qui le pose annonce
  ensuite une couleur.
- Si l'on ne peut pas ou ne veut pas jouer, on pioche une carte. Si cette carte est jouable, on peut
  la poser tout de suite ; sinon, ou si on ne le veut pas, on passe.
- Pioche vide : on remélange la défausse sans sa carte du dessus. Si elle aussi est vide, on passe.
- La manche s'arrête quand un joueur pose sa dernière carte. Les autres marquent la valeur des
  cartes qui leur restent : 8 = 50, figure = 10, as = 1, autre = sa valeur, joker = 50.
- Le plus petit total après la dernière manche gagne.

### 1.2 Options

| Code | Libellé | Type | Défaut |
|---|---|---|---|
| `cartes_speciales` | Cartes spéciales (2, valet, as) | booléen | vrai |
| `jokers` | Jokers (+4, sur tout) | booléen | faux |
| `manches` | Nombre de manches | entier 1–10 | 3 |

Avec `cartes_speciales` :

- un **2** fait piocher 2 cartes au joueur suivant, qui perd son tour, sauf s'il pose lui-même un 2 :
  le total passe alors au suivant (+2 à chaque 2). Personne ne peut poser autre chose qu'un 2 tant
  qu'une pénalité est en cours ;
- un **valet** fait passer son tour au joueur suivant ;
- un **as** inverse le sens du jeu. À 2 joueurs, il vaut un valet.

Avec `jokers` (2 par paquet) : le joker se pose sur n'importe quoi, sans annonce. Il fait piocher
4 cartes au suivant, qui perd son tour ; un 2 ne peut pas le contrer, un autre joker si (+4). La carte
qui précède le joker reste la référence : sa couleur et sa valeur.

Une carte spéciale posée en dernière carte termine la manche, et son effet n'a pas lieu.

### 1.3 Actions

| Phase | Action | Cartes |
|---|---|---|
| jouer | `jouer` « Jouer » | 1 |
| jouer (sans avoir pioché) | `piocher` « Piocher » (ou « Piocher N » sous pénalité) | 0 |
| jouer (après avoir pioché) | `passer` « Passer » ; seule la carte piochée peut alors être jouée | 0 |
| couleur | `couleur_S`, `couleur_H`, `couleur_D`, `couleur_C` « Pique », « Cœur », « Carreau », « Trèfle » | 0 |
| fin de manche | `manche_suivante` « Manche suivante » | 0 |

Sous pénalité, « Piocher N » prend les cartes et termine le tour.

### 1.4 Vue

Les mains ; au centre, la pile `pioche` (nombre seulement), la pile `defausse` (carte du dessus) ;
au menu : manche, couleur demandée (après un 8), sens du jeu, pénalité en cours. Compteurs du siège :
cartes, points.

### 1.5 Adversaire

Pose une carte jouable autre qu'un 8 en préférant ses cartes spéciales et sa couleur la plus fournie ;
le 8 (puis le joker) en dernier recours ; sinon pioche, puis pose la carte piochée si elle est jouable.
Annonce la couleur la plus présente dans sa main.

## 2. La dame de pique (`dame`)

### 2.1 Règles

- 3 à 6 joueurs ; 4 est le jeu normal. Pour une donne égale, on retire : à 3 le 2♦ ; à 5 le 2♦ et
  le 2♠ ; à 6 les 2♦, 2♠, 3♦ et 3♠. Le 2♣ n'est jamais retiré.
- Toutes les cartes sont distribuées. Ordre : as fort, puis R, D, V, 10 … 2. Pas d'atout.
- **Échange** avant chaque manche : chacun choisit 3 cartes et les donne. Le sens tourne : gauche,
  droite, en face, aucun. Sans « en face » (3, 5 ou 6 joueurs) : gauche, droite, aucun. Chacun
  choisit avant de recevoir. Le choix est un coup privé : son message n'est montré qu'à son auteur.
- Le détenteur du 2♣ entame le premier pli avec le 2♣.
- Il faut fournir la couleur demandée. Sinon on joue ce qu'on veut, sauf au premier pli : ni cœur ni
  dame de pique, si l'on a autre chose.
- On ne peut pas entamer à cœur tant qu'aucun cœur n'a été joué (« cœurs ouverts »), sauf si l'on n'a
  que des cœurs. La dame de pique n'ouvre pas les cœurs.
- La plus haute carte de la couleur demandée remporte le pli ; son gagnant entame le suivant.
- Fin de manche, quand les mains sont vides : chaque cœur ramassé vaut 1, la dame de pique 13.
  **Grand chelem** : qui ramasse tous les cœurs et la dame marque 0, et chacun des autres 26.
- La partie s'arrête à la fin de la manche où quelqu'un atteint le score de fin. Le plus petit total
  gagne ; l'égalité est permise.

### 2.2 Options

| Code | Libellé | Type | Défaut |
|---|---|---|---|
| `echange` | Échange de 3 cartes | booléen | vrai |
| `score_fin` | Score de fin de partie | entier 20–200 | 100 |
| `valet_carreau` | Valet de carreau à −10 | booléen | faux |

Avec `valet_carreau`, le valet de carreau vaut −10 à qui le ramasse. Il ne compte pas pour le grand
chelem.

### 2.3 Actions

| Phase | Action | Cartes |
|---|---|---|
| échange | `donner` « Donner à <nom> » | 3 |
| plis | `jouer` « Jouer » | 1 |
| fin de manche | `manche_suivante` « Manche suivante » | 0 |

### 2.4 Vue

Les mains, avec les 3 cartes reçues mises en évidence par un message, pas par le tapis. Une zone de
siège `pli-<s>` (type `pli`, libellé « Pli ») porte la carte que le siège a jouée dans le pli en cours.
Tant que le pli suivant n'a reçu aucune carte, ces zones montrent le pli qui vient d'être ramassé,
pour qu'on voie qui l'a pris ; le message de l'étape le dit (« Ouest remporte le pli (2 points) »).
Les points de la manche vont dans les compteurs du siège (« Points », « Total »).
Au menu : manche, sens de l'échange, cœurs ouverts ou non.

### 2.5 Adversaire

Échange : donne la dame, le roi et l'as de pique s'il les a, puis ses plus hauts cœurs, puis ses
plus hautes cartes. Jeu : sous la couleur demandée, joue la plus haute carte qui ne prend pas le pli,
sinon la plus basse ; dernier du pli sans points dedans, joue sa plus haute. Sans la couleur : se
défausse de la dame de pique, puis de son plus haut cœur, puis de sa plus haute carte. À l'entame :
sa plus basse carte, hors cœur si possible.

## 3. Le président (`president`)

### 3.1 Règles

- 3 à 7 joueurs, un paquet. Toutes les cartes sont distribuées ; certains en ont une de plus.
- Ordre des valeurs : 3, 4, …, 10, V, D, R, A, **2** (le plus fort). Les couleurs ne comptent pas.
- Première manche : le détenteur du 3♣ entame. Manches suivantes : le Pauvre entame.
- Celui qui entame pose 1 à 4 cartes de même valeur. Ensuite, chacun à son tour pose **autant** de
  cartes, de même valeur, et **plus fortes** que la dernière combinaison ; ou passe. Un joueur qui a
  passé peut rejouer quand son tour revient dans le même pli.
- Le pli se ferme quand tous les autres joueurs encore en jeu ont passé à la suite de la dernière
  combinaison posée. Celui qui l'a posée entame le pli suivant. S'il a fini sa main, c'est le
  joueur suivant encore en jeu qui entame.
- Un joueur qui vide sa main sort de la manche. Le premier sorti est **Président**, le deuxième
  **Vice-président** ; l'avant-dernier **Vice-pauvre**, le dernier **Pauvre** ; les autres
  **Neutres**. À 3 joueurs : Président, Neutre, Pauvre (pas de vice).
- Points de la manche : Président = nombre de joueurs − 1, puis un de moins à chaque rang, le Pauvre 0.
  Le plus grand total après la dernière manche gagne.
- **Échange** au début de chaque manche après la première : le Pauvre donne d'office ses 2 meilleures
  cartes au Président, qui lui rend 2 cartes de son choix. À 4 joueurs et plus, le Vice-pauvre et le
  Vice-président échangent de même 1 carte. Le choix du Président (et du Vice-président) est un coup
  privé ; le don d'office est annoncé sans dire les cartes.

### 3.2 Options

| Code | Libellé | Type | Défaut |
|---|---|---|---|
| `deux_ferme` | Le 2 ferme le pli | booléen | vrai |
| `echanges` | Échanges entre manches | booléen | vrai |
| `manches` | Nombre de manches | entier 1–10 | 5 |

Avec `deux_ferme`, une combinaison de 2 ferme le pli tout de suite ; son auteur entame le suivant.

### 3.3 Actions

| Phase | Action | Cartes |
|---|---|---|
| échange | `rendre` « Donner au Pauvre » / « Donner au Vice-pauvre » | 2 ou 1 |
| pli | `jouer` « Jouer » | 1–4 à l'entame, sinon exactement le nombre du pli |
| pli (pas à l'entame) | `passer` « Passer » | 0 |
| fin de manche | `manche_suivante` « Manche suivante » | 0 |

### 3.4 Vue

Les mains ; au centre, la zone `pli` (type `pli`) porte la dernière combinaison posée ; au menu :
manche, le nombre de cartes à poser dans le pli, qui a posé la dernière combinaison. Compteurs du
siège : cartes, rang de la manche précédente, total.

### 3.5 Adversaire

À l'entame : sa plus basse valeur, avec toutes ses cartes de cette valeur. Sinon : la plus basse
combinaison qui bat le pli sans casser un groupe plus grand, en gardant ses 2 tant qu'il lui reste
plus de 3 cartes ; sinon passe. Échange : rend ses cartes les plus basses.
