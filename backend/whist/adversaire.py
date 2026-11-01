"""Les adversaires de la machine au whist à la couleur (spec whist §6). N'importe pas Django.

Sans stratégie : ils ne choisissent que parmi les coups permis, de façon déterministe, pour
que `Whist.appliquer` accepte toujours leur coup. Ils ne se servent que de leur main et de ce
qui est public (cartes jouées, contrat, main étalée d'une misère ouverte).
"""

from tapis.cartes import enseigne, valeur
from whist.manche import (
    COULEURS,
    MISERES,
    ORDRE_COULEURS,
    annonces_permises,
    camp,
    cartes_jouables,
    gagnant_du_pli,
    rang,
)
from whist.vue import main_ouverte

NB_CARTES_COULEUR = 13


def _coup(action: str, cartes=()) -> dict:
    return {"action": action, "cartes": list(cartes), "cible": None}


def _force(c: str) -> tuple:
    """Rang puis couleur : un ordre total et stable."""
    return (rang(c), ORDRE_COULEURS[enseigne(c)])


def _plus_haute(cartes: list[str]) -> str:
    return max(cartes, key=_force)


def _plus_basse(cartes: list[str]) -> str:
    return min(cartes, key=_force)


def _de_la_couleur(cartes: list[str], e: str | None) -> list[str]:
    return [c for c in cartes if e is not None and enseigne(c) == e]


# --- Enchères ------------------------------------------------------------------------------


def estimer(main: list[str], atout: str | None) -> int:
    """As + rois gardés (avec une autre carte de la couleur) + atouts au-delà de trois."""
    plis = sum(1 for c in main if valeur(c) == "A")
    plis += sum(
        1 for c in main if valeur(c) == "K" and len(_de_la_couleur(main, enseigne(c))) >= 2
    )
    return plis + max(0, len(_de_la_couleur(main, atout)) - 3)


def main_de_misere(main: list[str]) -> bool:
    """Ni as ni roi, une dame au plus, et une carte plus basse que 7 dans chaque couleur tenue."""
    if any(valeur(c) in ("A", "K") for c in main):
        return False
    if sum(1 for c in main if valeur(c) == "Q") > 1:
        return False
    tenues = {enseigne(c) for c in main}
    return all(any(rang(c) < rang("7S-1") for c in _de_la_couleur(main, e)) for e in tenues)


def _couleurs_longues(main: list[str]) -> list[str]:
    """Les couleurs d'au moins 6 cartes, de la plus longue à la plus courte."""
    longues = [e for e in COULEURS if len(_de_la_couleur(main, e)) >= 6]
    return sorted(longues, key=lambda e: (-len(_de_la_couleur(main, e)), ORDRE_COULEURS[e]))


def choisir_annonce(etat: dict, j: int) -> str:
    """Elle n'annonce que ce que sa main justifie, jamais au-delà de l'abondance 9 (sauf misère)."""
    main = etat["mains"][j]
    permises = annonces_permises(etat, j)
    if "misere" in permises and main_de_misere(main):
        return "misere"
    if "abondance_9" in permises and any(estimer(main, e) >= 9 for e in _couleurs_longues(main)):
        return "abondance_9"
    estimes = estimer(main, enseigne(etat["retournee"]))
    if estimes >= 5:
        return "seul" if "seul" in permises else "passer"
    if estimes >= 3:
        for annonce in ("accepter", "demander"):
            if annonce in permises:
                return annonce
    return "passer"


def choisir_couleur_d_atout(main: list[str]) -> str:
    """La couleur qui lui promet le plus de plis, puis la plus longue."""
    return max(
        COULEURS,
        key=lambda e: (estimer(main, e), len(_de_la_couleur(main, e)), -ORDRE_COULEURS[e]),
    )


# --- Plis ----------------------------------------------------------------------------------


def _couleur_la_plus_longue(cartes: list[str]) -> list[str]:
    couleur = max(
        {enseigne(c) for c in cartes},
        key=lambda e: (len(_de_la_couleur(cartes, e)), -ORDRE_COULEURS[e]),
    )
    return _de_la_couleur(cartes, couleur)


def _gagnerait(etat: dict, j: int, carte: str) -> bool:
    return gagnant_du_pli(etat["pli"] + [[j, carte]], etat["atout"]) == j


def _majorite_d_atouts(etat: dict, j: int) -> bool:
    """Il tient plus de la moitié des atouts encore en jeu (les siens compris)."""
    atout = etat["atout"]
    miens = len(_de_la_couleur(etat["mains"][j], atout))
    joues = len(_de_la_couleur(etat["jouees"], atout))
    return miens > (NB_CARTES_COULEUR - joues - miens)


def _entamer(etat: dict, j: int, jouables: list[str]) -> str:
    if j not in etat["contrat"]["preneurs"]:
        return _plus_basse(_couleur_la_plus_longue(jouables))
    as_ = [c for c in jouables if valeur(c) == "A"]
    if as_:
        return min(as_, key=_force)
    atouts = _de_la_couleur(jouables, etat["atout"])
    if atouts and _majorite_d_atouts(etat, j):
        return _plus_haute(atouts)
    return _plus_haute(_couleur_la_plus_longue(jouables))


def _suivre(etat: dict, j: int, jouables: list[str]) -> str:
    pli = etat["pli"]
    au_partenaire = gagnant_du_pli(pli, etat["atout"]) in camp(etat, j)
    demandee = enseigne(pli[0][1])
    gagnantes = [c for c in jouables if _gagnerait(etat, j, c)]
    if enseigne(jouables[0]) == demandee:  # il fournit : toutes ses jouables sont de la couleur
        if au_partenaire or not gagnantes:
            return _plus_basse(jouables)
        return _plus_basse(gagnantes)
    coupes = _de_la_couleur(gagnantes, etat["atout"])
    if coupes and not au_partenaire:
        return _plus_basse(coupes)
    hors_atout = [c for c in jouables if etat["atout"] is None or enseigne(c) != etat["atout"]]
    return _plus_basse(hors_atout or jouables)


def _misere(etat: dict, j: int, jouables: list[str]) -> str:
    pli = etat["pli"]
    preneur = etat["contrat"]["preneurs"][0]
    if j == preneur:
        if not pli:
            return _plus_basse(jouables)
        sures = [c for c in jouables if not _gagnerait(etat, j, c)]
        return _plus_haute(sures) if sures else _plus_basse(jouables)
    if not pli:
        if main_ouverte(etat) == preneur:
            # Sa couleur courte, parmi celles qu'il tient et que le défenseur a aussi.
            sa_main = etat["mains"][preneur]
            communes = {enseigne(c) for c in jouables} & {enseigne(c) for c in sa_main}
            if communes:
                courte = min(communes, key=lambda e: (len(_de_la_couleur(sa_main, e)),
                                                       ORDRE_COULEURS[e]))
                return _plus_basse(_de_la_couleur(jouables, courte))
        return _plus_basse(jouables)
    demandee = enseigne(pli[0][1])
    if enseigne(jouables[0]) != demandee:  # défausse : sans atout, elle ne prend jamais
        return _plus_haute(jouables)
    if gagnant_du_pli(pli, None) == preneur:
        dessous = [c for c in jouables if not _gagnerait(etat, j, c)]
        return _plus_basse(dessous or jouables)
    return _plus_basse(jouables)


def choisir_carte(etat: dict, j: int) -> str:
    jouables = cartes_jouables(etat, j)
    if etat["contrat"]["code"] in MISERES:
        return _misere(etat, j, jouables)
    if not etat["pli"]:
        return _entamer(etat, j, jouables)
    return _suivre(etat, j, jouables)


def choisir(etat: dict, j: int) -> dict:
    match etat["phase"]:
        case "encheres":
            return _coup(choisir_annonce(etat, j))
        case "demande_seule":
            estimes = estimer(etat["mains"][j], enseigne(etat["retournee"]))
            return _coup("seul" if estimes >= 5 else "passer")
        case "atout":
            return _coup(f"atout_{choisir_couleur_d_atout(etat['mains'][j])}")
        case "plis":
            return _coup("jouer", [choisir_carte(etat, j)])
        case _:
            return _coup("donne_suivante")
