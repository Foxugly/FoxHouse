"""Règles et déroulement des manches du 8 américain (spec §1.1, §1.2). N'importe pas Django.

Les fonctions modifient l'état reçu ; c'est l'appelant qui le copie.

L'état :
- `reference` : la dernière carte normale posée ; sa couleur et sa valeur sont à suivre (un
  joker ne la change pas) ;
- `couleur` : l'enseigne annoncée après un 8, ou None ;
- `penalite` : les cartes à piocher en cours (2 et jokers cumulés), `penalite_par` : "2" ou
  "joker", la seule carte qui la contre ;
- `piochee` : la carte que le joueur actif vient de piocher, la seule qu'il peut encore jouer ;
- `blocages` : les tours de suite où personne n'a rien pu piocher ni joué ; à `nb`, la manche
  s'arrête ;
- `scores` : une ligne de points par manche jouée.
"""

from tapis.cartes import enseigne, est_joker, melanger, paquet, valeur
from tapis.jeu import CoupRefuse

_SYMBOLES = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
COULEURS = {"S": "Pique", "H": "Cœur", "D": "Carreau", "C": "Trèfle"}
_FIGURES = ("J", "Q", "K")


def nom_joueur(j: int) -> str:
    return "Toi" if j == 0 else f"Ordinateur {j}"


def _verbe(j: int, humain: str, ordi: str) -> str:
    return f"Tu {humain}" if j == 0 else f"{nom_joueur(j)} {ordi}"


def etiquette_carte(carte: str) -> str:
    if est_joker(carte):
        return "joker"
    return f"{valeur(carte)}{_SYMBOLES[enseigne(carte)]}"


def nb_paquets(nb: int) -> int:
    return 1 if nb <= 4 else 2


def cartes_par_main(nb: int) -> int:
    return 8 if nb <= 4 else 7


def points(carte: str) -> int:
    if est_joker(carte):
        return 50
    v = valeur(carte)
    if v == "8":
        return 50
    if v in _FIGURES:
        return 10
    if v == "A":
        return 1
    return int(v)


def est_huit(carte: str) -> bool:
    return not est_joker(carte) and valeur(carte) == "8"


# --- La donne -----------------------------------------------------------------------------


def nouvel_etat(options: dict, nb: int, graine: int) -> dict:
    etat = {
        "options": options,
        "graine": graine,
        "nb": nb,
        "manche": 1,
        "donneur": nb - 1,  # le joueur à sa gauche, le siège 0, commence la première manche
        "scores": [],
    }
    distribuer(etat)
    return etat


def retourner(pioche: list[str]) -> str:
    """La première carte de la défausse ; un 8 (ou un joker) retourne au milieu de la pioche."""
    while True:
        carte = pioche.pop()
        if not (est_huit(carte) or est_joker(carte)):
            return carte
        pioche.insert(len(pioche) // 2, carte)


def distribuer(etat: dict) -> None:
    nb = etat["nb"]
    jeux = nb_paquets(nb)
    jokers = 2 * jeux if etat["options"]["jokers"] else 0
    pioche = melanger(paquet(jeux, jokers), etat["graine"] * 100 + etat["manche"])
    premier = (etat["donneur"] + 1) % nb
    mains = [[] for _ in range(nb)]
    for _ in range(cartes_par_main(nb)):
        for k in range(nb):
            mains[(premier + k) % nb].append(pioche.pop())
    dessus = retourner(pioche)
    etat.update(
        {
            "mains": mains,
            "pioche": pioche,
            "defausse": [dessus],
            "reference": dessus,
            "couleur": None,
            "penalite": 0,
            "penalite_par": None,
            "piochee": None,
            "sens": 1,
            "actif": premier,
            "phase": "jouer",
            "remelanges": 0,
            "blocages": 0,
        }
    )


# --- Ce qui se joue -----------------------------------------------------------------------


def suivant(etat: dict, j: int, pas: int = 1) -> int:
    return (j + pas * etat["sens"]) % etat["nb"]


def jouable(etat: dict, carte: str) -> bool:
    """La carte se pose sur la défausse, hors pénalité."""
    if est_joker(carte) or est_huit(carte):
        return True
    if etat["couleur"]:
        return enseigne(carte) == etat["couleur"]
    ref = etat["reference"]
    return enseigne(carte) == enseigne(ref) or valeur(carte) == valeur(ref)


def contre(etat: dict, carte: str) -> bool:
    """La carte contre la pénalité en cours : un 2 sur un 2, un joker sur un joker."""
    if etat["penalite_par"] == "joker":
        return est_joker(carte)
    return not est_joker(carte) and valeur(carte) == "2"


def peut_jouer(etat: dict, carte: str) -> bool:
    """Ce que les règles acceptent de `jouer` pour le joueur actif."""
    if etat["piochee"] is not None and carte != etat["piochee"]:
        return False
    return contre(etat, carte) if etat["penalite"] else jouable(etat, carte)


def _exiger_jouable(etat: dict, carte: str) -> None:
    if etat["piochee"] is not None and carte != etat["piochee"]:
        raise CoupRefuse("Tu ne peux jouer que la carte piochée.")
    if etat["penalite"]:
        if not contre(etat, carte):
            parade = "un joker" if etat["penalite_par"] == "joker" else "un 2"
            raise CoupRefuse(
                f"Une pénalité est en cours : pose {parade} ou pioche {etat['penalite']} cartes."
            )
    elif not jouable(etat, carte):
        if etat["couleur"]:
            raise CoupRefuse(f"La couleur demandée est {COULEURS[etat['couleur']]}.")
        raise CoupRefuse(
            f"Le {etiquette_carte(carte)} ne se joue pas sur le "
            f"{etiquette_carte(etat['reference'])}."
        )


def _passer_au_suivant(etat: dict, j: int, pas: int = 1) -> int:
    etat["actif"] = suivant(etat, j, pas)
    etat["piochee"] = None
    return etat["actif"]


def _penaliser(etat: dict, j: int, nombre: int, par: str) -> str:
    etat["penalite"] += nombre
    etat["penalite_par"] = par
    victime = _passer_au_suivant(etat, j)
    return f" {_verbe(victime, 'dois', 'doit')} piocher {etat['penalite']} cartes."


def jouer(etat: dict, j: int, carte: str) -> str:
    _exiger_jouable(etat, carte)
    etat["mains"][j].remove(carte)
    etat["defausse"].append(carte)
    etat["piochee"] = None
    etat["blocages"] = 0
    if not est_joker(carte):
        etat["reference"] = carte
        etat["couleur"] = None
    message = f"{_verbe(j, 'joues', 'joue')} le {etiquette_carte(carte)}."
    if not etat["mains"][j]:  # une carte spéciale posée en dernier n'a pas d'effet
        fin_de_manche(etat, j)
        return f"{message} {_verbe(j, "n'as", "n'a")} plus de carte : la manche est terminée."
    speciales = etat["options"]["cartes_speciales"]
    v = None if est_joker(carte) else valeur(carte)
    if v is None:
        return message + _penaliser(etat, j, 4, "joker")
    if v == "8":
        etat["phase"] = "couleur"
        choix = "Choisis" if j == 0 else f"{nom_joueur(j)} choisit"
        return f"{message} {choix} une couleur."
    if speciales and v == "2":
        return message + _penaliser(etat, j, 2, "2")
    if speciales and (v == "J" or (v == "A" and etat["nb"] == 2)):
        saute = suivant(etat, j)
        _passer_au_suivant(etat, j, 2)
        return f"{message} {_verbe(saute, 'passes ton tour', 'passe son tour')}."
    if speciales and v == "A":
        etat["sens"] = -etat["sens"]
        _passer_au_suivant(etat, j)
        return f"{message} Le sens du jeu s'inverse."
    _passer_au_suivant(etat, j)
    return message


def annoncer(etat: dict, j: int, couleur: str) -> str:
    etat["couleur"] = couleur
    etat["phase"] = "jouer"
    _passer_au_suivant(etat, j)
    return f"{_verbe(j, 'annonces', 'annonce')} {COULEURS[couleur]}."


def _remelanger(etat: dict) -> bool:
    """Refait la pioche avec la défausse sans sa carte du dessus ; False si rien à remélanger."""
    if len(etat["defausse"]) <= 1:
        return False
    etat["remelanges"] += 1
    graine = (etat["graine"] * 100 + etat["manche"]) * 1000 + etat["remelanges"]
    etat["pioche"] = melanger(etat["defausse"][:-1], graine) + etat["pioche"]
    etat["defausse"] = etat["defausse"][-1:]
    return True


def _tirer(etat: dict, nombre: int) -> tuple[list[str], bool]:
    """Jusqu'à `nombre` cartes de la pioche, remélangée au besoin ; et « remélangée »."""
    tirees, remelangee = [], False
    while len(tirees) < nombre:
        if not etat["pioche"]:
            if not _remelanger(etat):
                break
            remelangee = True
        tirees.append(etat["pioche"].pop())
    return tirees, remelangee


def _bloque(etat: dict, j: int) -> str:
    """Le joueur n'a rien pu piocher : il passe ; si tous en sont là, la manche s'arrête."""
    etat["blocages"] += 1
    qui = "tu passes" if j == 0 else f"{nom_joueur(j)} passe"
    message = f"Il n'y a plus rien à piocher : {qui}."
    if etat["blocages"] >= etat["nb"]:
        fin_de_manche(etat, None)
        return f"{message} Personne ne peut plus jouer : la manche est terminée."
    _passer_au_suivant(etat, j)
    return message


def piocher(etat: dict, j: int) -> str:
    """Une carte, la seule que l'on pourra jouer ce tour. Sous pénalité : les cartes dues, et
    le tour passe."""
    penalite = etat["penalite"]
    tirees, remelangee = _tirer(etat, penalite or 1)
    prefixe = "La défausse est remélangée pour refaire la pioche. " if remelangee else ""
    etat["mains"][j] += tirees
    etat["penalite"] = 0
    etat["penalite_par"] = None
    if not tirees:
        return prefixe + _bloque(etat, j)
    etat["blocages"] = 0
    if not penalite:
        etat["piochee"] = tirees[0]
        return f"{prefixe}{_verbe(j, 'pioches', 'pioche')}."
    _passer_au_suivant(etat, j)
    pluriel = "s" if len(tirees) > 1 else ""
    message = f"{prefixe}{_verbe(j, 'pioches', 'pioche')} {len(tirees)} carte{pluriel}"
    if len(tirees) < penalite:
        message += " : il n'y en a pas plus"
    return message + "."


def passer(etat: dict, j: int) -> str:
    _passer_au_suivant(etat, j)
    return f"{_verbe(j, 'passes', 'passe')}."


# --- Les manches --------------------------------------------------------------------------


def fin_de_manche(etat: dict, gagnant: int | None) -> None:
    etat["scores"].append(
        [0 if j == gagnant else sum(points(c) for c in main) for j, main in enumerate(etat["mains"])]
    )
    etat["penalite"] = 0
    etat["penalite_par"] = None
    etat["piochee"] = None
    etat["couleur"] = None
    etat["phase"] = "fin_manche" if etat["manche"] < etat["options"]["manches"] else "terminee"
    etat["actif"] = 0


def manche_suivante(etat: dict) -> None:
    etat["manche"] += 1
    etat["donneur"] = (etat["donneur"] + 1) % etat["nb"]
    distribuer(etat)


def totaux(etat: dict) -> list[int]:
    return [sum(ligne[s] for ligne in etat["scores"]) for s in range(etat["nb"])]
