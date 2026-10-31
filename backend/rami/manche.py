"""Déroulement d'une manche et des manches du rami. N'importe pas Django.

Les fonctions modifient l'état reçu ; c'est l'appelant qui le copie.
"""

from rami.combinaisons import penalite
from tapis.cartes import est_joker, melanger, paquet, valeur

CARTES_PAR_MAIN = 13
_SYMBOLES = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}


def nom_joueur(j: int) -> str:
    return "Toi" if j == 0 else f"Ordinateur {j}"


def etiquette_carte(carte: str) -> str:
    if est_joker(carte):
        return "joker"
    return f"{valeur(carte)}{_SYMBOLES[carte.split('-')[0][-1]]}"


def _verbe(j: int, humain: str, ordi: str) -> str:
    return f"Tu {humain}" if j == 0 else f"{nom_joueur(j)} {ordi}"


def nouvel_etat(options: dict, nb: int, graine: int) -> dict:
    etat = {
        "options": options,
        "graine": graine,
        "nb": nb,
        "manche": 1,
        "premier": 0,
        "actif": 0,
        "phase": "piocher",
        "pioche": [],
        "defausse": [],
        "mains": [],
        "ouvert": [False] * nb,
        "table": [],
        "prochain_groupe": 1,
        "brouillon": [],
        "prise": None,
        "joker_recupere": None,
        "reconstitutions": 0,
        "penalites": [],
    }
    distribuer(etat)
    return etat


def distribuer(etat: dict) -> None:
    nb = etat["nb"]
    pioche = melanger(paquet(2, 4), etat["graine"] * 100 + etat["manche"])
    mains = [[] for _ in range(nb)]
    for k in range(nb):
        j = (etat["premier"] + k) % nb
        mains[j] = [pioche.pop() for _ in range(CARTES_PAR_MAIN)]
    etat["mains"] = mains
    etat["defausse"] = [pioche.pop()]
    etat["pioche"] = pioche
    etat["phase"] = "piocher"
    etat["actif"] = etat["premier"]
    etat["prise"] = None
    etat["joker_recupere"] = None


def reconstituer_pioche(etat: dict) -> bool:
    """Refait la pioche avec la défausse (sauf son dessus) ; False si impossible."""
    if etat["reconstitutions"] >= 3 or len(etat["defausse"]) <= 1:
        return False
    graine = etat["graine"] * 100 + etat["manche"] + 1000 * (etat["reconstitutions"] + 1)
    dessus = etat["defausse"][-1]
    etat["pioche"] = melanger(etat["defausse"][:-1], graine)
    etat["defausse"] = [dessus]
    etat["reconstitutions"] += 1
    return True


def piocher(etat: dict, j: int) -> str:
    if not etat["pioche"] and not reconstituer_pioche(etat):
        fin_de_manche(etat, None)
        return "La pioche est épuisée : la manche est terminée."
    etat["mains"][j].append(etat["pioche"].pop())
    etat["phase"] = "jouer"
    return f"{nom_joueur(j)} pioche." if j else "Tu pioches."


def prendre_defausse(etat: dict, j: int) -> str:
    if not etat["defausse"]:
        raise ValueError("La défausse est vide.")
    carte = etat["defausse"].pop()
    etat["mains"][j].append(carte)
    etat["prise"] = carte
    etat["phase"] = "jouer"
    return f"{_verbe(j, 'prends', 'prend')} le {etiquette_carte(carte)} de la défausse."


def defausser(etat: dict, j: int, carte: str) -> str:
    main = etat["mains"][j]
    if carte not in main:
        raise ValueError(f"La carte {carte!r} n'est pas dans la main.")
    main.remove(carte)
    etat["defausse"].append(carte)
    message = f"{_verbe(j, 'défausses', 'défausse')} le {etiquette_carte(carte)}."
    etat["prise"] = None
    etat["joker_recupere"] = None
    if not main:
        fin_de_manche(etat, j)
    else:
        etat["actif"] = (j + 1) % etat["nb"]
        etat["phase"] = "piocher"
    return message


def _penalite_cartes(etat: dict, cartes: list[str]) -> int:
    return sum(
        penalite(c, etat["options"]["as"], etat["options"]["penalite_joker"]) for c in cartes
    )


def fin_de_manche(etat: dict, gagnant: int | None) -> None:
    ligne = []
    for j in range(etat["nb"]):
        if j == gagnant:
            ligne.append(0)
            continue
        cartes = list(etat["mains"][j])
        if j == etat["actif"]:
            for comb in etat["brouillon"]:
                cartes += comb["cartes"]
        ligne.append(_penalite_cartes(etat, cartes))
    etat["penalites"].append(ligne)
    etat["brouillon"] = []
    etat["phase"] = "fin_manche" if etat["manche"] < etat["options"]["manches"] else "terminee"
    etat["actif"] = 0


def manche_suivante(etat: dict) -> None:
    etat["manche"] += 1
    etat["premier"] = (etat["premier"] + 1) % etat["nb"]
    etat["table"] = []
    etat["prochain_groupe"] = 1
    etat["brouillon"] = []
    etat["ouvert"] = [False] * etat["nb"]
    etat["reconstitutions"] = 0
    distribuer(etat)
