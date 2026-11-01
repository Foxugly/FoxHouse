"""Ce que chaque joueur voit de la table du whist à la couleur (schéma de tapis.vue).

N'importe pas Django. La vue d'un joueur ne contient jamais la main d'un autre, ni la graine,
avec deux exceptions publiques (spec whist §5) : la carte retournée, tant que le donneur ne l'a
pas jouée, et la main du preneur d'une misère ouverte, une fois le premier pli joué.
"""

from tapis.cartes import CACHEE, decrire
from tapis.vue import SCHEMA
from whist.manche import (
    COULEURS,
    MISERES,
    NB,
    _verbe,
    annonces_permises,
    contrat_de_l_annonce,
    etiquette,
    libelle,
    nom_atout,
    nom_joueur,
    noms,
    majuscule,
    totaux,
)


def _action(id_, libelle_, cartes_min=0, cartes_max=0, direct=False) -> dict:
    action = {
        "id": id_, "libelle": libelle_, "cartes_min": cartes_min, "cartes_max": cartes_max,
        "cible": None,
    }
    if direct:
        action["direct"] = True
    return action


def _libelle_annonce(annonce: str) -> str:
    if annonce == "demander":
        return "Demander"
    if annonce == "accepter":
        return "Accepter"
    if annonce == "seul":
        return "Seul (5 plis)"
    return libelle(contrat_de_l_annonce(annonce))


def actions_permises(etat: dict, j: int) -> list[dict]:
    """Les actions que le joueur j peut jouer maintenant ; aucune si ce n'est pas son tour."""
    phase = etat["phase"]
    if phase == "terminee" or etat["actif"] != j:
        return []
    if phase == "encheres":
        return [_action("passer", "Passer")] + [
            _action(a, _libelle_annonce(a)) for a in annonces_permises(etat, j)
        ]
    if phase == "demande_seule":
        return [_action("seul", "Jouer seul (5 plis)"), _action("passer", "Passer")]
    if phase == "atout":
        return [_action(f"atout_{e}", f"Atout {nom}") for e, nom in COULEURS.items()]
    if phase == "plis":
        return [_action("jouer", "Jouer", 1, 1, direct=True)]
    return [_action("donne_suivante", "Donne suivante")]


def retournee_visible(etat: dict) -> bool:
    """La carte retournée se voit tant qu'elle est dans la main du donneur."""
    return etat["retournee"] in etat["mains"][etat["donneur"]]


def main_ouverte(etat: dict) -> int | None:
    """Le preneur d'une misère ouverte dont la main est étalée, s'il y en a un."""
    contrat = etat["contrat"]
    if (contrat and contrat["code"] == "misere_ouverte" and etat["plis_joues"] >= 1
            and etat["phase"] in ("plis", "fin_donne", "terminee")):
        return contrat["preneurs"][0]
    return None


def _ordre(j: int) -> list[int]:
    return [(j + k) % NB for k in range(NB)]


def _sieges(etat: dict, j: int) -> list[dict]:
    total = totaux(etat)
    actif = None if etat["phase"] == "terminee" else etat["actif"]
    return [
        {
            "id": s,
            "nom": nom_joueur(s),
            "actif": s == actif,
            "compteurs": [
                {"libelle": "Plis", "valeur": etat["plis"][s]},
                {"libelle": "Total", "valeur": total[s]},
            ],
        }
        for s in _ordre(j)
    ]


def _main(etat: dict, j: int, s: int) -> dict:
    if s == j or s == main_ouverte(etat):
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
    for s in _ordre(j):
        zones += [_main(etat, j, s), _pli(etat, s)]
    if retournee_visible(etat):
        # La même carte est aussi dans la main du donneur : le schéma le permet.
        zones.append({
            "id": "atout", "type": "pile", "siege": None, "libelle": "Atout",
            "cartes": [decrire(etat["retournee"])], "nombre": None, "groupes": [],
        })
    return zones


def _numero_de_donne(etat: dict) -> int:
    finie = etat["phase"] in ("fin_donne", "terminee")
    return len(etat["scores"]) if finie else len(etat["scores"]) + 1


def _annonce_en_cours(etat: dict) -> str:
    enchere = etat["enchere"]
    if enchere is None:
        return "aucune"
    detenteurs = [s for s in (enchere["preneur"], enchere["partenaire"]) if s is not None]
    return f"{libelle(enchere['code'])} ({noms(detenteurs)})"


def _menu(etat: dict) -> list[dict]:
    menu = [
        {"libelle": "Donne", "valeur": f"{_numero_de_donne(etat)} / {etat['options']['donnes']}"},
        {"libelle": "Donneur", "valeur": nom_joueur(etat["donneur"])},
    ]
    if retournee_visible(etat):
        menu.append({"libelle": "Retournée", "valeur": etiquette(etat["retournee"])})
    contrat = etat["contrat"]
    if contrat is None:
        menu.append({"libelle": "Plus haute annonce", "valeur": _annonce_en_cours(etat)})
        return menu
    preneurs = contrat["preneurs"]
    atout = "à choisir" if etat["phase"] == "atout" else nom_atout(etat["atout"])
    menu += [
        {"libelle": "Contrat", "valeur": libelle(contrat["code"])},
        {"libelle": "Preneurs" if len(preneurs) > 1 else "Preneur",
         "valeur": majuscule(noms(preneurs))},
        {"libelle": "Atout", "valeur": atout},
    ]
    if contrat["code"] not in MISERES:
        menu.append({"libelle": "Plis des preneurs",
                     "valeur": sum(etat["plis"][s] for s in preneurs)})
    return menu


def _resultat(etat: dict, j: int) -> dict | None:
    total = totaux(etat)
    if etat["phase"] == "fin_donne":
        titre = f"Fin de la donne {len(etat['scores'])}"
    elif etat["phase"] == "terminee":
        gagnants = [s for s in range(NB) if total[s] == max(total)]
        if len(gagnants) == 1:
            titre = f"Fin de la partie — {_verbe(gagnants[0], 'gagnes', 'gagne')}"
        else:
            titre = "Fin de la partie — égalité"
    else:
        return None
    donnes = len(etat["scores"])
    return {
        "titre": titre,
        "colonnes": ["Joueur"] + [f"Donne {d}" for d in range(1, donnes + 1)] + ["Total"],
        "lignes": [
            [nom_joueur(s)] + [ligne[s] for ligne in etat["scores"]] + [total[s]]
            for s in _ordre(j)
        ],
    }


def vue(etat: dict, j: int) -> dict:
    return {
        "schema": SCHEMA,
        "jeu": "whist",
        "version": 0,
        "terminee": etat["phase"] == "terminee",
        "sieges": _sieges(etat, j),
        "zones": _zones(etat, j),
        "menu": _menu(etat),
        "actions": actions_permises(etat, j),
        "resultat": _resultat(etat, j),
    }
