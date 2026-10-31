"""Les adversaires de la machine à la dame de pique (spec jeux §2.5). N'importe pas Django.

Sans stratégie : ils ne choisissent que parmi les coups permis, de façon déterministe, pour
que `Dame.appliquer` accepte toujours leur coup.
"""

from dame.manche import (
    DAME_PIQUE,
    NB_DONNEES,
    ORDRE_COULEURS,
    VALET_CARREAU,
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
    valet = VALET_CARREAU if etat["options"]["valet_carreau"] else None
    demandee = enseigne(pli[0][1])
    if enseigne(jouables[0]) == demandee:  # il fournit : toutes ses jouables sont de la couleur
        return _fournir(etat, jouables, valet)
    if DAME_PIQUE in jouables:
        return DAME_PIQUE
    coeurs = [c for c in jouables if enseigne(c) == "H"]
    return _plus_haute(coeurs or _sauf(jouables, valet))


def _sauf(cartes: list[str], *exclues) -> list[str]:
    """Les cartes sans les exclues ; toutes si rien d'autre ne reste."""
    return [c for c in cartes if c not in exclues] or cartes


def _fournir(etat: dict, jouables: list[str], valet: str | None) -> str:
    """Sous la couleur demandée.

    La dame de pique n'est jouée que si une carte plus haute (R♠ ou A♠) est déjà dans le pli,
    ou s'il ne reste qu'elle. Le valet de carreau (avec l'option) n'est jamais donné à un
    autre s'il y a autre chose ; il est pris, dernier du pli, s'il le remporte.
    """
    pli = etat["pli"]
    maitresse = next(c for s, c in pli if s == gagnant_du_pli(pli))
    dame_prend = DAME_PIQUE in jouables and rang(DAME_PIQUE) > rang(maitresse)
    sures = _sauf(jouables, DAME_PIQUE) if dame_prend else jouables
    dernier = len(pli) == etat["nb"] - 1
    if dernier and points_des_cartes([c for _, c in pli], etat["options"]) <= 0:
        if valet in sures and rang(valet) > rang(maitresse):
            return valet
        haute = _plus_haute(sures)
        if haute == valet and rang(valet) < rang(maitresse):
            return _plus_haute(_sauf(sures, valet))
        return haute
    dessous = _sauf([c for c in sures if rang(c) < rang(maitresse)], valet)
    return _plus_haute(dessous) if dessous else _plus_basse(sures)


def choisir(etat: dict, j: int) -> dict:
    match etat["phase"]:
        case "echange":
            return _coup("donner", choisir_dons(etat["mains"][j]))
        case "plis":
            return _coup("jouer", [choisir_carte(etat, j)])
        case _:
            return _coup("manche_suivante")
