"""Les adversaires de la machine à la dame de pique (spec jeux §2.5). N'importe pas Django.

Sans stratégie : ils ne choisissent que parmi les coups permis, de façon déterministe, pour
que `Dame.appliquer` accepte toujours leur coup.
"""

from dame.manche import (
    DAME_PIQUE,
    NB_DONNEES,
    ORDRE_COULEURS,
    cartes_jouables,
    gagnant_du_pli,
    points_des_cartes,
    rang,
)
from tapis.cartes import enseigne

_PIQUES_HAUTS = [DAME_PIQUE, "KS-1", "AS-1"]


def _coup(action: str, cartes=()) -> dict:
    return {"action": action, "cartes": list(cartes), "cible": None}


def _force(c: str) -> tuple:
    """Rang puis couleur : un ordre total et stable."""
    return (rang(c), ORDRE_COULEURS[enseigne(c)])


def _plus_haute(cartes: list[str]) -> str:
    return max(cartes, key=_force)


def _plus_basse(cartes: list[str]) -> str:
    return min(cartes, key=_force)


def choisir_dons(main: list[str]) -> list[str]:
    """La dame, le roi et l'as de pique, puis les plus hauts cœurs, puis les plus hautes cartes."""
    piques = [c for c in _PIQUES_HAUTS if c in main]
    coeurs = sorted((c for c in main if enseigne(c) == "H"), key=_force, reverse=True)
    autres = sorted((c for c in main if c not in piques and c not in coeurs), key=_force,
                    reverse=True)
    return (piques + coeurs + autres)[:NB_DONNEES]


def choisir_carte(etat: dict, j: int) -> str:
    jouables = cartes_jouables(etat, j)
    pli = etat["pli"]
    if not pli:
        hors_coeur = [c for c in jouables if enseigne(c) != "H"]
        return _plus_basse(hors_coeur or jouables)
    demandee = enseigne(pli[0][1])
    if enseigne(jouables[0]) == demandee:  # il fournit : toutes ses jouables sont de la couleur
        dernier = len(pli) == etat["nb"] - 1
        if dernier and points_des_cartes([c for _, c in pli], etat["options"]) <= 0:
            return _plus_haute(jouables)
        maitresse = next(c for s, c in pli if s == gagnant_du_pli(pli))
        dessous = [c for c in jouables if rang(c) < rang(maitresse)]
        return _plus_haute(dessous) if dessous else _plus_basse(jouables)
    if DAME_PIQUE in jouables:
        return DAME_PIQUE
    coeurs = [c for c in jouables if enseigne(c) == "H"]
    return _plus_haute(coeurs or jouables)


def choisir(etat: dict, j: int) -> dict:
    match etat["phase"]:
        case "echange":
            return _coup("donner", choisir_dons(etat["mains"][j]))
        case "plis":
            return _coup("jouer", [choisir_carte(etat, j)])
        case _:
            return _coup("manche_suivante")
