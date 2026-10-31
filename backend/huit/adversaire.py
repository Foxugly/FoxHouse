"""Les adversaires de la machine au 8 américain (spec §1.5). N'importe pas Django.

Sans stratégie : une carte jouable autre qu'un 8, cartes spéciales et couleur la plus fournie
d'abord ; le 8, puis le joker, en dernier recours ; sinon la pioche, puis la carte piochée si
elle se joue. Ils ne choisissent que parmi les coups que `manche.peut_jouer` accepte, pour que
`Huit.appliquer` accepte toujours leur coup. Le choix est déterministe.
"""

from collections import Counter

from huit.manche import COULEURS, est_huit, peut_jouer
from huit.vue import actions_permises
from tapis.cartes import enseigne, est_joker, valeur

_SPECIALES = ("2", "J", "A")


def _coup(action: str, cartes=()) -> dict:
    return {"action": action, "cartes": list(cartes), "cible": None}


def _couleurs(main: list[str]) -> Counter:
    """Le nombre de cartes de chaque enseigne, hors 8 et jokers."""
    return Counter(enseigne(c) for c in main if not (est_joker(c) or est_huit(c)))


def couleur_preferee(main: list[str]) -> str:
    """L'enseigne la plus présente ; à égalité, dans l'ordre pique, cœur, carreau, trèfle."""
    nombres = _couleurs(main)
    return max(COULEURS, key=lambda e: (nombres[e], -list(COULEURS).index(e)))


def _preference(etat: dict, main: list[str]):
    nombres = _couleurs(main)
    speciales = etat["options"]["cartes_speciales"]

    def cle(c: str) -> tuple:
        if est_joker(c):
            return (3, 0, c)
        if est_huit(c):
            return (2, 0, c)
        speciale = speciales and valeur(c) in _SPECIALES
        return (0 if speciale else 1, -nombres[enseigne(c)], c)

    return cle


def choisir(etat: dict, j: int) -> dict:
    """Le coup de l'adversaire j, toujours parmi ses actions permises."""
    permises = {a["id"] for a in actions_permises(etat, j)}
    if not permises:
        raise ValueError(f"Le joueur {j} n'a rien à jouer.")
    if etat["phase"] == "fin_manche":
        return _coup("manche_suivante")
    main = etat["mains"][j]
    if etat["phase"] == "couleur":
        return _coup(f"couleur_{couleur_preferee(main)}")
    jouables = [c for c in main if peut_jouer(etat, c)]
    if jouables:
        return _coup("jouer", [min(jouables, key=_preference(etat, main))])
    return _coup("passer" if "passer" in permises else "piocher")
