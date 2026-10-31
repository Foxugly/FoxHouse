"""Ce que chaque joueur voit de la table du 8 américain (spec §1.4, schéma de tapis.vue).
N'importe pas Django.

La vue d'un joueur ne contient jamais la main d'un autre, la pioche ni la graine.
"""

from huit.manche import COULEURS, _verbe, etiquette_carte, nom_joueur, totaux
from tapis.cartes import CACHEE, decrire, est_joker
from tapis.vue import SCHEMA


def _action(id_, libelle, cartes_min=0, cartes_max=0) -> dict:
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
        return [_action("manche_suivante", "Manche suivante")]
    if phase == "couleur":
        return [_action(f"couleur_{e}", nom) for e, nom in COULEURS.items()]
    actions = [_action("jouer", "Jouer", 1, 1)]
    if etat["piochee"] is not None:
        actions.append(_action("passer", "Passer"))
    elif etat["penalite"]:
        actions.append(_action("piocher", f"Piocher {etat['penalite']}"))
    else:
        actions.append(_action("piocher", "Piocher"))
    return actions


def _ordre(etat: dict, j: int) -> list[int]:
    return [(j + k) % etat["nb"] for k in range(etat["nb"])]


def _sieges(etat: dict, j: int) -> list[dict]:
    points = totaux(etat)
    actif = None if etat["phase"] == "terminee" else etat["actif"]
    return [
        {
            "id": s,
            "nom": nom_joueur(s),
            "actif": s == actif,
            "compteurs": [
                {"libelle": "Cartes", "valeur": len(etat["mains"][s])},
                {"libelle": "Points", "valeur": points[s]},
            ],
        }
        for s in _ordre(etat, j)
    ]


def _main(etat: dict, j: int, s: int) -> dict:
    if s == j:
        cartes = [decrire(c) for c in etat["mains"][s]]
    else:
        cartes = [dict(CACHEE) for _ in etat["mains"][s]]
    return {
        "id": f"main-{s}", "type": "main", "siege": s,
        "libelle": "Ta main" if s == j else nom_joueur(s),
        "cartes": cartes, "nombre": None, "groupes": [],
    }


def _zones(etat: dict, j: int) -> list[dict]:
    defausse = etat["defausse"]
    return [_main(etat, j, s) for s in _ordre(etat, j)] + [
        {
            "id": "pioche", "type": "pile", "siege": None, "libelle": "Pioche",
            "cartes": [], "nombre": len(etat["pioche"]), "groupes": [],
        },
        {
            "id": "defausse", "type": "pile", "siege": None, "libelle": "Défausse",
            "cartes": [decrire(defausse[-1])] if defausse else [],
            "nombre": len(defausse), "groupes": [],
        },
    ]


def _menu(etat: dict) -> list[dict]:
    menu = [{"libelle": "Manche", "valeur": f"{etat['manche']} / {etat['options']['manches']}"}]
    if etat["phase"] in ("fin_manche", "terminee"):
        return menu
    if etat["couleur"]:
        menu.append({"libelle": "Couleur demandée", "valeur": COULEURS[etat["couleur"]]})
    elif est_joker(etat["defausse"][-1]):
        # Le joker ne change pas la carte à suivre, qu'on ne voit plus sous lui.
        menu.append({"libelle": "Carte à suivre", "valeur": etiquette_carte(etat["reference"])})
    menu.append({"libelle": "Sens du jeu", "valeur": "normal" if etat["sens"] == 1 else "inversé"})
    if etat["penalite"]:
        menu.append({"libelle": "Pénalité", "valeur": f"{etat['penalite']} cartes"})
    return menu


def _resultat(etat: dict, j: int) -> dict | None:
    points = totaux(etat)
    if etat["phase"] == "fin_manche":
        titre = f"Fin de la manche {etat['manche']}"
    elif etat["phase"] == "terminee":
        gagnants = [s for s in range(etat["nb"]) if points[s] == min(points)]
        if len(gagnants) == 1:
            titre = f"Fin de la partie — {_verbe(gagnants[0], 'gagnes', 'gagne')}"
        else:
            titre = "Fin de la partie — égalité"
    else:
        return None
    manches = len(etat["scores"])
    return {
        "titre": titre,
        "colonnes": ["Joueur"] + [f"Manche {m}" for m in range(1, manches + 1)] + ["Total"],
        "lignes": [
            [nom_joueur(s)] + [ligne[s] for ligne in etat["scores"]] + [points[s]]
            for s in _ordre(etat, j)
        ],
    }


def vue(etat: dict, j: int) -> dict:
    return {
        "schema": SCHEMA,
        "jeu": "huit",
        "version": 0,
        "terminee": etat["phase"] == "terminee",
        "sieges": _sieges(etat, j),
        "zones": _zones(etat, j),
        "menu": _menu(etat),
        "actions": actions_permises(etat, j),
        "resultat": _resultat(etat, j),
    }
