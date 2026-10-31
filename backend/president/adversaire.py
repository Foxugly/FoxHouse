"""Les adversaires de la machine au président (spec des jeux §3.5). N'importe pas Django.

Sans stratégie, mais ils font avancer la partie : ils ne choisissent que parmi les actions
permises, et `President.appliquer` accepte toujours leur coup. Le choix est déterministe.
"""

from president.manche import force, trier
from president.vue import actions_permises
from tapis.cartes import valeur


def _coup(action: str, cartes=()) -> dict:
    return {"action": action, "cartes": list(cartes), "cible": None}


def _groupes(main: list[str]) -> list[list[str]]:
    """Les cartes de la main par valeur, des plus faibles aux plus fortes."""
    groupes: dict[str, list[str]] = {}
    for c in trier(main):
        groupes.setdefault(valeur(c), []).append(c)
    return list(groupes.values())


def _repondre(etat: dict, main: list[str]) -> dict:
    """La plus basse combinaison qui bat le pli sans casser un groupe plus grand, en gardant
    ses 2 tant qu'il reste plus de 3 cartes ; sinon passer."""
    pli = etat["pli"]
    nombre, a_battre = pli["nombre"], force(pli["cartes"][0])
    for groupe in _groupes(main):
        if len(groupe) != nombre or force(groupe[0]) <= a_battre:
            continue
        if valeur(groupe[0]) == "2" and len(main) > 3:
            continue
        return _coup("jouer", groupe)
    return _coup("passer")


def choisir(etat: dict, j: int) -> dict:
    actions = {a["id"]: a for a in actions_permises(etat, j)}
    main = etat["mains"][j]
    if "manche_suivante" in actions:
        return _coup("manche_suivante")
    if "rendre" in actions:
        return _coup("rendre", trier(main)[: actions["rendre"]["cartes_max"]])
    if "passer" in actions:
        return _repondre(etat, main)
    return _coup("jouer", _groupes(main)[0])  # entame : sa plus basse valeur, en entier
