"""Ce que chaque joueur voit de la table de la dame de pique (schéma de tapis.vue).

N'importe pas Django. La vue d'un joueur ne contient jamais la main d'un autre, ni les cartes
qu'un autre a choisies pour l'échange, ni la graine.
"""

from dame.manche import (
    LIBELLES_SENS,
    _verbe,
    destinataire,
    enumerer,
    nom_joueur,
    points_des_cartes,
    totaux,
)
from tapis.cartes import CACHEE, decrire
from tapis.vue import SCHEMA


def _action(id_, libelle, cartes_min, cartes_max, direct=False) -> dict:
    action = {
        "id": id_, "libelle": libelle, "cartes_min": cartes_min, "cartes_max": cartes_max,
        "cible": None,
    }
    if direct:
        action["direct"] = True
    return action


def actions_permises(etat: dict, j: int) -> list[dict]:
    """Les actions que le joueur j peut jouer maintenant ; aucune si ce n'est pas son tour."""
    phase = etat["phase"]
    if phase == "terminee" or etat["actif"] != j:
        return []
    if phase == "echange":
        return [_action("donner", f"Donner à {nom_joueur(destinataire(etat, j))}", 3, 3)]
    if phase == "plis":
        # Un pli se joue d'un clic sur la carte (demande de Renaud, 2026-11-01).
        return [_action("jouer", "Jouer", 1, 1, direct=True)]
    return [_action("manche_suivante", "Manche suivante", 0, 0)]


def _ordre(etat: dict, j: int) -> list[int]:
    return [(j + k) % etat["nb"] for k in range(etat["nb"])]


def _sieges(etat: dict, j: int) -> list[dict]:
    total = totaux(etat)
    actif = None if etat["phase"] == "terminee" else etat["actif"]
    return [
        {
            "id": s,
            "nom": nom_joueur(s),
            "actif": s == actif,
            "compteurs": [
                {"libelle": "Points",
                 "valeur": points_des_cartes(etat["ramassees"][s], etat["options"])},
                {"libelle": "Total", "valeur": total[s]},
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


def _pli(etat: dict, s: int) -> dict:
    """La carte du siège dans le pli en cours, ou dans le pli ramassé tant que rien n'est joué."""
    pli = etat["pli"] or etat["dernier_pli"]
    return {
        "id": f"pli-{s}", "type": "pli", "siege": s, "libelle": "Pli",
        "cartes": [decrire(c) for siege, c in pli if siege == s], "nombre": None, "groupes": [],
    }


def _zones(etat: dict, j: int) -> list[dict]:
    zones = []
    for s in _ordre(etat, j):
        zones += [_main(etat, j, s), _pli(etat, s)]
    return zones


def _menu(etat: dict, j: int) -> list[dict]:
    menu = [
        {"libelle": "Manche", "valeur": etat["manche"]},
        {"libelle": "Échange", "valeur": LIBELLES_SENS[etat["sens"]]},
        {"libelle": "Cœurs", "valeur": "ouverts" if etat["coeurs_ouverts"] else "fermés"},
        {"libelle": "Score de fin", "valeur": etat["options"]["score_fin"]},
    ]
    if etat["phase"] == "plis" and etat["plis_joues"] == 0 and etat["recues"][j]:
        menu.append({"libelle": "Reçues", "valeur": enumerer(etat["recues"][j])})
    return menu


def _resultat(etat: dict, j: int) -> dict | None:
    total = totaux(etat)
    if etat["phase"] == "fin_manche":
        titre = f"Fin de la manche {etat['manche']}"
    elif etat["phase"] == "terminee":
        gagnants = [s for s in range(etat["nb"]) if total[s] == min(total)]
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
            [nom_joueur(s)] + [ligne[s] for ligne in etat["scores"]] + [total[s]]
            for s in _ordre(etat, j)
        ],
    }


def vue(etat: dict, j: int) -> dict:
    return {
        "schema": SCHEMA,
        "jeu": "dame",
        "version": 0,
        "terminee": etat["phase"] == "terminee",
        "sieges": _sieges(etat, j),
        "zones": _zones(etat, j),
        "menu": _menu(etat, j),
        "actions": actions_permises(etat, j),
        "resultat": _resultat(etat, j),
    }
