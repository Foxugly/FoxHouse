# FoxHouse — whist à la couleur (`whist`)

*1er novembre 2026. Renaud a demandé « une app whist à la couleur » et laisse les règles à mon choix
(go implicite sur le backlog). Ce qui suit retient les règles belges les plus courantes, simplifiées
là où les tables varient ; chaque choix peut être contesté.*

Le préambule commun de `2026-10-31-jeux-huit-dame-president.md` s'applique tel quel (app Django sans
import Django hors `apps.py`, vue sans fuite, aucun changement du tapis ni de `parties/`, parties
machine contre machine, tableau des scores en fin de partie, textes en français et tutoiement).

## 1. Règles

- **4 joueurs exactement**, partenaires changeant à chaque donne. Un paquet de 52 cartes. Ordre :
  as fort, puis R, D, V, 10 … 2.
- Le donneur distribue les 52 cartes, 13 chacun. **La dernière carte (celle du donneur) est
  retournée** : sa couleur est l'atout de la donne, sauf contrat qui en décide autrement. Tout le
  monde la voit jusqu'à ce que le donneur la joue. Le donneur tourne à chaque donne.
- **Enchères**, en commençant à gauche du donneur, dans le sens du jeu. À son tour, un joueur passe
  ou annonce un contrat **plus haut** que le plus haut annoncé. Un joueur qui a passé ne revient plus.
  Les enchères s'arrêtent quand tous les autres ont passé après la dernière annonce.
- **Contrats**, du plus bas au plus haut :

| Contrat | Joueurs | But | Atout |
|---|---|---|---|
| Emballage (demande + accepte) | 2 contre 2 | 8 plis à deux | retourné |
| Seul | 1 contre 3 | 5 plis | retourné |
| Abondance 9 | 1 contre 3 | 9 plis | choisi par le preneur |
| Misère | 1 contre 3 | aucun pli | sans atout |
| Abondance 10 | 1 contre 3 | 10 plis | choisi |
| Abondance 11 | 1 contre 3 | 11 plis | choisi |
| Misère ouverte | 1 contre 3 | aucun pli, sa main étalée dès la fin du premier pli | sans atout |
| Abondance 12 | 1 contre 3 | 12 plis | choisi |
| Solo | 1 contre 3 | 13 plis | retourné |
| Solo slim | 1 contre 3 | 13 plis | choisi |

- **Demande** : un joueur « demande » ; tant que la demande est le plus haut contrat, un joueur
  suivant peut **accepter** (au lieu de passer ou de monter) et devient son partenaire, connu de tous.
  Une demande acceptée vaut l'emballage ; seul un contrat plus haut que l'emballage la couvre.
  Si les enchères finissent sur une demande que personne n'a acceptée, le demandeur choisit :
  jouer **seul** (5 plis) ou **passer**.
- Une seule misère par donne (simplification) : chaque annonce doit être plus haute que la
  précédente, misère comprise.
- **Trou** (option) : avant les enchères, un joueur qui a trois as en main est tenu de jouer avec le
  détenteur du quatrième as, à 2 contre 2, pour 8 plis, à l'atout retourné. Avec les quatre as, son
  partenaire est le détenteur du roi de cœur (ou de la dame, s'il a aussi le roi, etc.). Le trou
  s'annonce automatiquement, sans enchères ; les deux partenaires sont dévoilés par un message.
- Si tout le monde passe, **la donne est rejouée** par le donneur suivant (aucun point).
- **Jeu** : le joueur à gauche du donneur entame le premier pli. Il faut fournir la couleur demandée ;
  sinon on joue n'importe quelle carte (pas d'obligation de couper ni de surcouper). Le plus haut
  atout remporte le pli, sinon la plus haute carte de la couleur demandée ; le gagnant entame.
- Une misère s'arrête dès que le preneur prend un pli (échec). Les autres contrats se jouent jusqu'au
  bout.

## 2. Points

Chaque donne est à somme nulle. Pour un contrat **à 1 contre 3**, le preneur gagne (ou perd) trois
fois la valeur, chaque adversaire perd (ou gagne) une fois la valeur. Pour un contrat **à 2 contre 2**,
chaque preneur gagne (ou perd) la valeur et chaque adversaire perd (ou gagne) la même.

| Contrat | Valeur réussie | Valeur ratée |
|---|---|---|
| Emballage, trou | 2 + 1 par pli au-delà de 8 ; **les 13 plis : 2 × (2 + 5) = 14** | 2 + 1 par pli manquant |
| Seul | 3 + 1 par pli au-delà de 5 (13 plis : 11) | 3 + 1 par pli manquant |
| Abondance 9 / 10 / 11 / 12 | 5 / 7 / 10 / 15, sans bonus de plis | la même valeur |
| Misère | 7 | 7 |
| Misère ouverte | 15 | 15 |
| Solo | 25 | 25 |
| Solo slim | 30 | 30 |

Exemple : seul, réussi avec 7 plis → valeur 3 + 2 = 5 ; le preneur marque +15, chacun des trois
autres −5.

## 3. Options

| Code | Libellé | Type | Défaut |
|---|---|---|---|
| `donnes` | Nombre de donnes | entier 4–24 | 8 |
| `trou` | Trou (trois as) | booléen | vrai |
| `misere` | Misère et misère ouverte | booléen | vrai |

Sans `misere`, ces deux contrats ne sont pas proposés. Une donne rejouée (tout le monde passe) ne
compte pas dans `donnes`. La partie finit après `donnes` donnes ; le plus haut total gagne.

## 4. Actions

| Phase | Action | Cartes |
|---|---|---|
| enchères | `passer` « Passer » et une action par contrat permis maintenant (`demander`, `accepter`, `seul`, `abondance_9`, `misere`, …), au libellé du contrat | 0 |
| demande sans partenaire | `seul` « Jouer seul (5 plis) », `passer` « Passer » | 0 |
| choix de l'atout (abondance, solo slim) | une action par couleur : `atout_H` « Atout cœur », … | 0 |
| plis | `jouer` « Jouer », **direct** (un clic sur la carte la joue) | 1 |
| fin de donne | `donne_suivante` « Donne suivante » | 0 |

Seules les annonces permises au joueur actif sont proposées (plus hautes que la dernière, misère
seulement avec l'option, accepter seulement si la demande est la plus haute annonce et sans partenaire).

## 5. Vue

- Les mains ; une zone de siège `pli-<s>` (type `pli`), comme la dame de pique, pour la carte jouée
  dans le pli en cours, qui garde le pli ramassé tant que le suivant n'a pas commencé.
- La carte retournée : zone du centre (type `pile`, libellé « Atout ») tant que le donneur ne l'a
  pas jouée ; elle reste aussi dans la main du donneur (même identifiant) — si le schéma refuse une
  carte présente dans deux zones, la montrer seulement au menu (« Retournée : 7 ♥ »).
- Misère ouverte : après le premier pli, la main du preneur est visible de tous (cartes visibles dans
  sa zone `main`, pas `cachee`). C'est la seule main d'un autre qui se montre.
- Compteurs de siège : « Plis » (de la donne), « Total ».
- Menu : donne (n / total), donneur, atout (ou « sans atout »), contrat et preneur(s) une fois les
  enchères finies, plus haute annonce pendant les enchères.
- Messages : chaque annonce (« Ordinateur 2 demande. », « Tu acceptes. »), le trou, le gagnant de
  chaque pli, le bilan de la donne (« Contrat réussi : Ordinateur 1 et toi marquez +3 chacun. »).

## 6. Adversaire

- **Enchères** : estime ses plis = as + rois gardés (roi avec au moins une autre carte de la couleur)
  + atouts au-delà de trois. ≥ 9 plis estimés avec une couleur longue (6+) : abondance 9 dans cette
  couleur. ≥ 5 : seul. 3–4 : demande, ou accepte une demande en cours. Misère : main sans as ni roi,
  au plus une dame et un plus bas que 7 dans chaque couleur. Sinon passe. Ne monte jamais au-delà
  de l'abondance 9 sauf misère ; ne sur-annonce pas le joueur humain par pure enchère.
- **Demande non acceptée** : seul si 5 plis estimés, sinon passe.
- **Jeu**, en attaque (preneur ou partenaire) : entame ses as, puis tire les atouts s'il en a la
  majorité, puis sa couleur la plus longue. En défense : entame la plus basse de sa couleur la plus
  longue. Sous la couleur : prend avec la plus basse carte gagnante si le pli n'est pas déjà à son
  partenaire, sinon fournit la plus basse. Sans la couleur : coupe au plus bas atout si le pli n'est
  pas à son partenaire, sinon se défausse de sa plus basse carte.
- **Misère**, preneur : joue toujours la plus haute carte qui ne prend pas, sinon la plus basse.
  Défenseurs : cherchent à le faire prendre (entament sa couleur courte, jouent bas derrière lui).
