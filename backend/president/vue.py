"""Ce que chaque joueur voit de la table du président (schéma de tapis.vue). N'importe pas Django.

La vue d'un joueur ne contient jamais la main d'un autre ni la graine. Les cartes reçues à
l'échange ne sont montrées qu'à celui qui les a reçues.
"""

from president.manche import (
    _etiquettes,
    _verbe,
    destinataire,
    nom_joueur,
    nom_rang,
    trier,
)
from tapis.cartes import CACHEE, decrire
from tapis.vue import SCHEMA


def _action(id_, libelle, cartes_min, cartes_max) -> dict:
    return {
        "id": id_, "libelle": libelle, "cartes_min": cartes_min, "cartes_max": cartes_max,
        "cible": None,
    }


def actions_permises(etat: dict, j: int) -> list[dict]:
    """Les actions que le joueur j peut jouer maintenant ; aucune si ce n'est pas son tour."""
    phase = etat["phase"]
    if phase == "terminee" or etat["actif"] != j:
        return []
    if phase == "fin_manche":
        return [_action("manche_suivante", "Manche suivante", 0, 0)]
    if phase == "echange":
        nombre = etat["a_rendre"][0]["nombre"]
        return [_action("rendre", f"Donner au {destinataire(etat)}", nombre, nombre)]
    nombre = etat["pli"]["nombre"]
    if nombre == 0:
        return [_action("jouer", "Jouer", 1, 4)]
    return [_action("jouer", "Jouer", nombre, nombre), _action("passer", "Passer", 0, 0)]


def _totaux(etat: dict) -> list[int]:
    return [sum(ligne[s] for ligne in etat["points"]) for s in range(etat["nb"])]


def _ordre(etat: dict, j: int) -> list[int]:
    return [(j + k) % etat["nb"] for k in range(etat["nb"])]


def _rang(etat: dict, s: int) -> str:
    return "—" if etat["rangs"] is None else nom_rang(etat["rangs"][s], etat["nb"])


def _sieges(etat: dict, j: int) -> list[dict]:
    totaux = _totaux(etat)
    actif = None if etat["phase"] == "terminee" else etat["actif"]
    return [
        {
            "id": s,
            "nom": nom_joueur(s),
            "actif": s == actif,
            "compteurs": [
                {"libelle": "Cartes", "valeur": len(etat["mains"][s])},
                {"libelle": "Rang", "valeur": _rang(etat, s)},
                {"libelle": "Total", "valeur": totaux[s]},
            ],
        }
        for s in _ordre(etat, j)
    ]


def _main(etat: dict, j: int, s: int) -> dict:
    if s == j:
        cartes = [decrire(c) for c in trier(etat["mains"][s])]
    else:
        cartes = [dict(CACHEE) for _ in etat["mains"][s]]
    return {
        "id": f"main-{s}", "type": "main", "siege": s,
        "libelle": "Ta main" if s == j else nom_joueur(s),
        "cartes": cartes, "nombre": None, "groupes": [],
    }


def _zones(etat: dict, j: int) -> list[dict]:
    pli = etat["pli"]
    # Fermé, le pli reste affiché jusqu'à l'entame suivante, sous un autre libellé.
    libelle = "Pli" if pli["nombre"] or not pli["cartes"] else "Dernier pli"
    return [_main(etat, j, s) for s in _ordre(etat, j)] + [
        {
            "id": "pli", "type": "pli", "siege": None, "libelle": libelle,
            "cartes": [decrire(c) for c in pli["cartes"]], "nombre": None, "groupes": [],
        },
    ]


def _a_poser(etat: dict) -> str:
    nombre = etat["pli"]["nombre"]
    if nombre == 0:
        return "1 à 4 cartes (entame)"
    return "1 carte" if nombre == 1 else f"{nombre} cartes"


def _menu(etat: dict, j: int) -> list[dict]:
    menu = [{"libelle": "Manche", "valeur": f"{etat['manche']} / {etat['options']['manches']}"}]
    if etat["phase"] == "pli":
        auteur = etat["pli"]["auteur"]
        menu.append({"libelle": "À poser", "valeur": _a_poser(etat)})
        menu.append(
            {"libelle": "Dernière combinaison", "valeur": "—" if auteur is None
             else nom_joueur(auteur)}
        )
    if etat["recues"][j]:
        menu.append({"libelle": "Cartes reçues", "valeur": _etiquettes(etat["recues"][j])})
    return menu


def _resultat(etat: dict, j: int) -> dict | None:
    totaux = _totaux(etat)
    if etat["phase"] == "fin_manche":
        titre = f"Fin de la manche {etat['manche']}"
    elif etat["phase"] == "terminee":
        gagnants = [s for s in range(etat["nb"]) if totaux[s] == max(totaux)]
        if len(gagnants) == 1:
            titre = f"Fin de la partie — {_verbe(gagnants[0], 'gagnes', 'gagne')}"
        else:
            titre = "Fin de la partie — égalité"
    else:
        return None
    manches = len(etat["points"])
    return {
        "titre": titre,
        "colonnes": ["Joueur", "Rang"] + [f"Manche {m}" for m in range(1, manches + 1)]
        + ["Total"],
        "lignes": [
            [nom_joueur(s), _rang(etat, s)] + [ligne[s] for ligne in etat["points"]]
            + [totaux[s]]
            for s in _ordre(etat, j)
        ],
    }


def vue(etat: dict, j: int) -> dict:
    return {
        "schema": SCHEMA,
        "jeu": "president",
        "version": 0,
        "terminee": etat["phase"] == "terminee",
        "sieges": _sieges(etat, j),
        "zones": _zones(etat, j),
        "menu": _menu(etat, j),
        "actions": actions_permises(etat, j),
        "resultat": _resultat(etat, j),
    }
