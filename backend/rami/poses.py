"""Poses du rami : ouverture en brouillon, ajouts aux groupes, récupération du joker.

N'importe pas Django. Les fonctions modifient l'état reçu (c'est l'appelant qui le
copie) et lèvent CoupRefuse avec un message destiné au joueur. Elles ne vérifient pas
à qui c'est le tour.

Un groupe de la table est {"id": "g<n>", "auteur": j, **vers_dict(comb)} ; le
brouillon est une liste de vers_dict(comb).
"""

from rami.combinaisons import (
    ajouter,
    analyser,
    depuis_dict,
    points,
    recuperer_joker,
    vers_dict,
)
from rami.manche import _verbe, fin_de_manche
from tapis.jeu import CoupRefuse

OUVERTURE_MINIMUM = 51


def _exiger_phase(etat: dict) -> None:
    if etat["phase"] != "jouer":
        raise CoupRefuse("Ce n'est pas le moment de poser.")


def _exiger_en_main(etat: dict, j: int, cartes: list[str]) -> None:
    main = etat["mains"][j]
    if not cartes or len(set(cartes)) != len(cartes) or any(c not in main for c in cartes):
        raise CoupRefuse("Ces cartes ne sont pas dans ta main.")


def _exiger_ouvert(etat: dict, j: int) -> None:
    if not etat["ouvert"][j]:
        raise CoupRefuse("Il faut d'abord avoir ouvert.")


def _exiger_une_carte_gardee(etat: dict, j: int, cartes: list[str]) -> None:
    """Avec « finir par une défausse », la main ne peut pas être vidée par une pose."""
    if etat["options"]["finir_par_defausse"] and len(etat["mains"][j]) == len(cartes):
        raise CoupRefuse("Garde une carte pour la défausse.")


def _retirer_de_la_main(etat: dict, j: int, cartes: list[str]) -> None:
    main = etat["mains"][j]
    for c in cartes:
        main.remove(c)


def _terminer_si_main_vide(etat: dict, j: int) -> None:
    if not etat["mains"][j]:
        fin_de_manche(etat, j)


def _groupe(etat: dict, groupe_id) -> dict:
    for g in etat["table"]:
        if g["id"] == groupe_id:
            return g
    raise CoupRefuse("Ce groupe n'existe pas.")


def _poser_sur_table(etat: dict, j: int, comb_dict: dict) -> None:
    etat["table"].append({"id": f"g{etat['prochain_groupe']}", "auteur": j, **comb_dict})
    etat["prochain_groupe"] += 1


def _nom_type(comb) -> str:
    if comb.type == "suite":
        return "une suite"
    return "un carré" if len(comb.cartes) == 4 else "un brelan"


def poser(etat: dict, j: int, cartes: list[str]) -> str:
    """Pose une combinaison : dans le brouillon avant l'ouverture, sur la table après."""
    _exiger_phase(etat)
    _exiger_en_main(etat, j, cartes)
    comb = analyser(cartes)
    if comb is None:
        raise CoupRefuse("Ces cartes ne forment pas une combinaison.")
    _exiger_une_carte_gardee(etat, j, cartes)
    _retirer_de_la_main(etat, j, cartes)
    if not etat["ouvert"][j]:
        etat["brouillon"].append(vers_dict(comb))
        return f"{_verbe(j, 'mets', 'met')} {_nom_type(comb)} en attente."
    _poser_sur_table(etat, j, vers_dict(comb))
    message = f"{_verbe(j, 'poses', 'pose')} {_nom_type(comb)}."
    _terminer_si_main_vide(etat, j)
    return message


def valider_ouverture(etat: dict, j: int) -> str:
    """Rend définitif le brouillon s'il vaut au moins 51 points (et respecte les options)."""
    _exiger_phase(etat)
    if etat["ouvert"][j]:
        raise CoupRefuse("Tu as déjà ouvert.")
    combs = [depuis_dict(d) for d in etat["brouillon"]]
    total = sum(points(c, etat["options"]["as"]) for c in combs)
    if total < OUVERTURE_MINIMUM:
        raise CoupRefuse(
            f"Il faut au moins {OUVERTURE_MINIMUM} points pour ouvrir (tu en as {total})."
        )
    if etat["options"]["ouverture_suite_sans_joker"] and not any(
        c.type == "suite" and not c.jokers for c in combs
    ):
        raise CoupRefuse("L'ouverture doit contenir une suite sans joker.")
    for d in etat["brouillon"]:
        _poser_sur_table(etat, j, d)
    etat["brouillon"] = []
    etat["ouvert"][j] = True
    message = f"{_verbe(j, 'ouvres', 'ouvre')} avec {total} points."
    _terminer_si_main_vide(etat, j)
    return message


def annuler(etat: dict, j: int) -> str:
    """Rend à la main toutes les cartes du brouillon."""
    _exiger_phase(etat)
    for d in etat["brouillon"]:
        etat["mains"][j].extend(d["cartes"])
    etat["brouillon"] = []
    return "Les cartes en attente reviennent dans ta main."


def ajouter_a(etat: dict, j: int, cartes: list[str], groupe_id) -> str:
    """Complète un groupe de la table, le sien ou celui d'un adversaire."""
    _exiger_phase(etat)
    _exiger_en_main(etat, j, cartes)
    _exiger_ouvert(etat, j)
    groupe = _groupe(etat, groupe_id)
    comb = ajouter(depuis_dict(groupe), cartes)
    if comb is None:
        raise CoupRefuse("Ces cartes ne complètent pas ce groupe.")
    _exiger_une_carte_gardee(etat, j, cartes)
    _retirer_de_la_main(etat, j, cartes)
    groupe.update(vers_dict(comb))
    message = f"{_verbe(j, 'complètes', 'complète')} {_nom_type(comb)}."
    _terminer_si_main_vide(etat, j)
    return message


def recuperer(etat: dict, j: int, carte: str, groupe_id) -> str:
    """Remplace le joker d'un groupe par cette carte ; le joker passe dans la main."""
    _exiger_phase(etat)
    _exiger_en_main(etat, j, [carte])
    if etat["options"]["recuperation_joker"] != "apres_ouverture":
        raise CoupRefuse("La récupération du joker n'est pas permise dans cette partie.")
    _exiger_ouvert(etat, j)
    if etat["joker_recupere"] in etat["mains"][j]:
        raise CoupRefuse("Utilise d'abord le joker récupéré.")
    groupe = _groupe(etat, groupe_id)
    if not groupe["jokers"]:
        raise CoupRefuse("Ce groupe n'a pas de joker.")
    resultat = recuperer_joker(depuis_dict(groupe), carte)
    if resultat is None:
        raise CoupRefuse("Cette carte ne remplace pas le joker de ce groupe.")
    comb, joker = resultat
    _retirer_de_la_main(etat, j, [carte])
    etat["mains"][j].append(joker)
    etat["joker_recupere"] = joker
    groupe.update(vers_dict(comb))
    return f"{_verbe(j, 'récupères', 'récupère')} un joker."
