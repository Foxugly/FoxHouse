"""Ce que chaque joueur voit de la table du rami (schéma de tapis.vue). N'importe pas Django.

La vue d'un joueur ne contient jamais la main ni le brouillon d'un autre, la pioche ni la
graine.
"""

from rami.combinaisons import depuis_dict, points
from rami.manche import _verbe, nom_joueur
from tapis.cartes import CACHEE, decrire, est_joker
from tapis.vue import SCHEMA


def _action(id_, libelle, cartes_min, cartes_max, cible=None) -> dict:
    return {
        "id": id_, "libelle": libelle, "cartes_min": cartes_min, "cartes_max": cartes_max,
        "cible": cible,
    }


def actions_permises(etat: dict, j: int) -> list[dict]:
    """Les actions que le joueur j peut jouer maintenant ; aucune si ce n'est pas son tour."""
    phase = etat["phase"]
    if phase == "terminee" or etat["actif"] != j:
        return []
    if phase == "piocher":
        actions = [_action("piocher", "Piocher", 0, 0)]
        if etat["defausse"]:
            actions.append(_action("prendre_defausse", "Prendre la défausse", 0, 0))
        return actions
    if phase == "fin_manche":
        return [_action("manche_suivante", "Manche suivante", 0, 0)]
    actions = [
        _action("poser", "Poser la combinaison", 3, 13),
        _action("defausser", "Défausser", 1, 1),
    ]
    if not etat["ouvert"][j]:
        if etat["brouillon"]:
            actions.append(_action("valider_ouverture", "Valider l'ouverture", 0, 0))
            actions.append(_action("annuler", "Annuler", 0, 0))
    else:
        actions.append(_action("ajouter", "Ajouter à la combinaison", 1, 12, "groupe"))
        if etat["options"]["recuperation_joker"] == "apres_ouverture":
            actions.append(_action("recuperer_joker", "Récupérer le joker", 1, 1, "groupe"))
    return actions


def _nb_cartes(etat: dict, s: int) -> int:
    """Main plus brouillon : la taille d'une main ne trahit pas un brouillon."""
    nb = len(etat["mains"][s])
    if s == etat["actif"]:
        nb += sum(len(comb["cartes"]) for comb in etat["brouillon"])
    return nb


def _totaux(etat: dict) -> list[int]:
    return [sum(ligne[s] for ligne in etat["penalites"]) for s in range(etat["nb"])]


def _ordre(etat: dict, j: int) -> list[int]:
    return [(j + k) % etat["nb"] for k in range(etat["nb"])]


def _sieges(etat: dict, j: int) -> list[dict]:
    totaux = _totaux(etat)
    actif = None if etat["phase"] == "terminee" else etat["actif"]
    return [
        {
            "id": s,
            "nom": nom_joueur(s),
            "actif": s == actif,
            "compteurs": [
                {"libelle": "Cartes", "valeur": _nb_cartes(etat, s)},
                {"libelle": "Pénalités", "valeur": totaux[s]},
            ],
        }
        for s in _ordre(etat, j)
    ]


def _main(etat: dict, j: int, s: int) -> dict:
    if s == j:
        cartes = [decrire(c) for c in etat["mains"][s]]
    else:
        cartes = [dict(CACHEE) for _ in range(_nb_cartes(etat, s))]
    return {
        "id": f"main-{s}", "type": "main", "siege": s,
        "libelle": "Ta main" if s == j else nom_joueur(s),
        "cartes": cartes, "nombre": None, "groupes": [],
    }


def _carte_de_groupe(c: str, jokers: dict) -> dict:
    carte = decrire(c)
    if est_joker(c):
        carte["represente"] = jokers.get(c)
    return carte


def _groupe(id_: str, comb: dict, provisoire: bool, ciblable: bool) -> dict:
    return {
        "id": id_,
        "cartes": [_carte_de_groupe(c, comb["jokers"]) for c in comb["cartes"]],
        "provisoire": provisoire,
        "ciblable": ciblable,
    }


def _zones(etat: dict, j: int, actions: list[dict]) -> list[dict]:
    ciblable = any(a["cible"] == "groupe" for a in actions)
    groupes = [_groupe(g["id"], g, False, ciblable) for g in etat["table"]]
    if etat["actif"] == j:
        groupes += [_groupe(f"b{k}", comb, True, False) for k, comb in enumerate(etat["brouillon"])]
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
        {
            "id": "table", "type": "combinaisons", "siege": None, "libelle": "Table",
            "cartes": [], "nombre": None, "groupes": groupes,
        },
    ]


def _menu(etat: dict, j: int) -> list[dict]:
    menu = [
        {"libelle": "Manche", "valeur": f"{etat['manche']} / {etat['options']['manches']}"},
        {"libelle": "Ouverture", "valeur": "faite" if etat["ouvert"][j] else "pas encore"},
    ]
    if etat["actif"] == j and etat["brouillon"]:
        total = sum(points(depuis_dict(d), etat["options"]["as"]) for d in etat["brouillon"])
        menu.append({"libelle": "Points en attente", "valeur": total})
    return menu


def _resultat(etat: dict, j: int) -> dict | None:
    if etat["phase"] == "fin_manche":
        titre = f"Fin de la manche {etat['manche']}"
    elif etat["phase"] == "terminee":
        totaux = _totaux(etat)
        gagnants = [s for s in range(etat["nb"]) if totaux[s] == min(totaux)]
        if len(gagnants) == 1:
            titre = f"Fin de la partie — {_verbe(gagnants[0], 'gagnes', 'gagne')}"
        else:
            titre = "Fin de la partie — égalité"
    else:
        return None
    manches = len(etat["penalites"])
    totaux = _totaux(etat)
    return {
        "titre": titre,
        "colonnes": ["Joueur"] + [f"Manche {m}" for m in range(1, manches + 1)] + ["Total"],
        "lignes": [
            [nom_joueur(s)] + [ligne[s] for ligne in etat["penalites"]] + [totaux[s]]
            for s in _ordre(etat, j)
        ],
    }


def vue(etat: dict, j: int) -> dict:
    actions = actions_permises(etat, j)
    return {
        "schema": SCHEMA,
        "jeu": "rami",
        "version": 0,
        "terminee": etat["phase"] == "terminee",
        "sieges": _sieges(etat, j),
        "zones": _zones(etat, j, actions),
        "menu": _menu(etat, j),
        "actions": actions,
        "resultat": _resultat(etat, j),
    }
