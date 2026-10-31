"""Déroulement d'une manche et des manches du président. N'importe pas Django.

Les fonctions modifient l'état reçu ; c'est l'appelant qui le copie.

L'état d'une partie :

- `mains` : la main de chaque siège ; `sortis` : les sièges qui ont vidé leur main, dans
  l'ordre (le premier est Président) ;
- `pli` : la dernière combinaison posée (`cartes`, `auteur`) et le nombre de cartes qu'il faut
  poser (`nombre`, 0 à l'entame). Une fois le pli fermé, `cartes` et `auteur` restent pour
  l'affichage jusqu'à l'entame suivante ;
- `passes` : les sièges qui ont passé à la suite de la dernière combinaison ;
- `rangs` : la place de chaque siège à la manche précédente (0 = Président), None à la
  première ; `points` : une ligne par manche finie ;
- `recues` : les cartes que chaque siège a reçues à l'échange de la manche en cours ;
  `a_rendre` : les retours encore attendus, `{"donneur", "receveur", "nombre"}`.
"""

from tapis.cartes import est_carte, est_joker, melanger, paquet, valeur
from tapis.jeu import CoupRefuse

ORDRE = ["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2"]
_SYMBOLES = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
_NOMS_VALEURS = {"J": "le valet", "Q": "la dame", "K": "le roi", "A": "l'as"}
TROIS_DE_TREFLE = "3C-1"


# --- Textes -------------------------------------------------------------------------------
# Recopiés du rami plutôt qu'importés : un jeu ne dépend pas d'un autre.


def nom_joueur(j: int) -> str:
    return "Toi" if j == 0 else f"Ordinateur {j}"


def _verbe(j: int, humain: str, ordi: str) -> str:
    return f"Tu {humain}" if j == 0 else f"{nom_joueur(j)} {ordi}"


def etiquette_carte(carte: str) -> str:
    return f"{valeur(carte)}{_SYMBOLES[carte.split('-')[0][-1]]}"


def _etiquettes(cartes: list[str]) -> str:
    return " ".join(etiquette_carte(c) for c in cartes)


def nom_valeur(v: str) -> str:
    return _NOMS_VALEURS.get(v, f"le {v}")


def nom_rang(rang: int, nb: int) -> str:
    """Nom de la place `rang` (0 = premier sorti) à `nb` joueurs."""
    if rang == 0:
        return "Président"
    if rang == nb - 1:
        return "Pauvre"
    if nb >= 4 and rang == 1:
        return "Vice-président"
    if nb >= 4 and rang == nb - 2:
        return "Vice-pauvre"
    return "Neutre"


# --- Cartes -------------------------------------------------------------------------------


def force(carte: str) -> int:
    """Rang de la valeur : 0 pour le 3, 12 pour le 2. Les couleurs ne comptent pas."""
    return ORDRE.index(valeur(carte))


def trier(cartes: list[str]) -> list[str]:
    """Des plus faibles aux plus fortes ; à valeur égale, dans l'ordre des identifiants."""
    return sorted(cartes, key=lambda c: (force(c), c))


# --- Le tour et le pli --------------------------------------------------------------------


def en_jeu(etat: dict) -> list[int]:
    return [s for s in range(etat["nb"]) if s not in etat["sortis"]]


def suivant_en_jeu(etat: dict, j: int) -> int:
    """Le premier siège encore en jeu après j (j lui-même peut être sorti)."""
    nb = etat["nb"]
    for k in range(1, nb + 1):
        s = (j + k) % nb
        if s not in etat["sortis"]:
            return s
    raise ValueError("Plus personne en jeu.")


def _pli_vide() -> dict:
    return {"cartes": [], "auteur": None, "nombre": 0}


def _fermer_pli(etat: dict) -> str:
    """Ferme le pli : son auteur entame, ou le suivant encore en jeu s'il est sorti."""
    auteur = etat["pli"]["auteur"]
    entameur = auteur if auteur not in etat["sortis"] else suivant_en_jeu(etat, auteur)
    etat["pli"]["nombre"] = 0
    etat["passes"] = []
    etat["actif"] = entameur
    return "tu entames." if entameur == 0 else f"{nom_joueur(entameur)} entame."


def _exiger_cartes(etat: dict, j: int, cartes: list[str]) -> None:
    for c in cartes:
        if not est_carte(c) or est_joker(c):
            raise CoupRefuse("Carte inconnue.")
    if len(set(cartes)) != len(cartes):
        raise CoupRefuse("Une même carte est choisie deux fois.")
    for c in cartes:
        if c not in etat["mains"][j]:
            raise CoupRefuse("Cette carte n'est pas dans ta main.")


def _exiger_combinaison(etat: dict, j: int, cartes: list[str]) -> None:
    _exiger_cartes(etat, j, cartes)
    if len({valeur(c) for c in cartes}) != 1:
        raise CoupRefuse("Les cartes doivent être de même valeur.")


def jouer(etat: dict, j: int, cartes: list[str]) -> str:
    """Pose une combinaison ; le nombre de cartes a déjà été vérifié."""
    _exiger_combinaison(etat, j, cartes)
    pli = etat["pli"]
    if pli["nombre"] and force(cartes[0]) <= force(pli["cartes"][0]):
        raise CoupRefuse(
            f"Il faut une valeur plus forte que {nom_valeur(valeur(pli['cartes'][0]))}."
        )
    main = etat["mains"][j]
    for c in cartes:
        main.remove(c)
    etat["pli"] = {"cartes": list(cartes), "auteur": j, "nombre": len(cartes)}
    etat["passes"] = []
    message = f"{_verbe(j, 'poses', 'pose')} {_etiquettes(cartes)}."

    if not main:
        etat["sortis"].append(j)
        rang = nom_rang(len(etat["sortis"]) - 1, etat["nb"])
        message += f" {_verbe(j, 'sors', 'sort')} : {rang}."
        restants = en_jeu(etat)
        if len(restants) == 1:
            dernier = restants[0]
            etat["sortis"].append(dernier)
            message += f" {_verbe(dernier, 'restes', 'reste')} seul : Pauvre."
            return message + " " + fin_de_manche(etat)

    if etat["options"]["deux_ferme"] and valeur(cartes[0]) == "2":
        return message + " Le 2 ferme le pli : " + _fermer_pli(etat)
    etat["actif"] = suivant_en_jeu(etat, j)
    return message


def passer(etat: dict, j: int) -> str:
    etat["passes"].append(j)
    message = f"{_verbe(j, 'passes', 'passe')}."
    autres = set(en_jeu(etat)) - {etat["pli"]["auteur"]}
    if autres <= set(etat["passes"]):
        return message + " Pli fermé : " + _fermer_pli(etat)
    etat["actif"] = suivant_en_jeu(etat, j)
    return message


# --- Les manches --------------------------------------------------------------------------


def nouvel_etat(options: dict, nb: int, graine: int) -> dict:
    etat = {
        "options": options,
        "graine": graine,
        "nb": nb,
        "manche": 1,
        "phase": "pli",
        "actif": 0,
        "mains": [],
        "sortis": [],
        "pli": _pli_vide(),
        "passes": [],
        "rangs": None,
        "points": [],
        "recues": [[] for _ in range(nb)],
        "a_rendre": [],
    }
    distribuer(etat)
    etat["actif"] = next(s for s in range(nb) if TROIS_DE_TREFLE in etat["mains"][s])
    return etat


def distribuer(etat: dict) -> None:
    """Toutes les cartes, une à une ; la donne commence à un siège qui tourne à chaque manche,
    et ceux qui sont servis les premiers ont une carte de plus."""
    nb = etat["nb"]
    cartes = melanger(paquet(1, 0), etat["graine"] * 100 + etat["manche"])
    mains = [[] for _ in range(nb)]
    premier = (etat["manche"] - 1) % nb
    for k, c in enumerate(cartes):
        mains[(premier + k) % nb].append(c)
    etat["mains"] = [trier(m) for m in mains]
    etat["sortis"] = []
    etat["pli"] = _pli_vide()
    etat["passes"] = []
    etat["recues"] = [[] for _ in range(nb)]
    etat["a_rendre"] = []


def fin_de_manche(etat: dict) -> str:
    nb = etat["nb"]
    etat["rangs"] = [etat["sortis"].index(s) for s in range(nb)]
    etat["points"].append([nb - 1 - etat["rangs"][s] for s in range(nb)])
    etat["pli"]["nombre"] = 0
    etat["passes"] = []
    etat["actif"] = 0
    if etat["manche"] < etat["options"]["manches"]:
        etat["phase"] = "fin_manche"
        return f"Fin de la manche {etat['manche']}."
    etat["phase"] = "terminee"
    return "Fin de la partie."


def _par_rang(etat: dict, rang: int) -> int:
    return etat["rangs"].index(rang)


def _donner(etat: dict, donneur: int, receveur: int, cartes: list[str]) -> None:
    for c in cartes:
        etat["mains"][donneur].remove(c)
    etat["mains"][receveur] = trier(etat["mains"][receveur] + cartes)
    etat["recues"][receveur] = list(cartes)


def _message_don(etat: dict, donneur: int, receveur: int, nombre: int) -> str:
    """Le don d'office, annoncé à tous sans dire les cartes."""
    nb = etat["nb"]
    rang_d = nom_rang(etat["rangs"][donneur], nb)
    rang_r = nom_rang(etat["rangs"][receveur], nb)
    if nombre == 1:
        tes, ses = "ta meilleure carte", "sa meilleure carte"
    else:
        tes, ses = f"tes {nombre} meilleures cartes", f"ses {nombre} meilleures cartes"
    if donneur == 0:
        return f"Tu donnes {tes} à {nom_joueur(receveur)} ({rang_r})."
    if receveur == 0:
        return f"{nom_joueur(donneur)} ({rang_d}) te donne {ses}."
    return f"{nom_joueur(donneur)} ({rang_d}) donne {ses} à {nom_joueur(receveur)} ({rang_r})."


def _commencer_les_plis(etat: dict) -> None:
    """Après les échanges : le Pauvre de la manche précédente entame."""
    etat["phase"] = "pli"
    etat["pli"] = _pli_vide()
    etat["passes"] = []
    etat["actif"] = _par_rang(etat, etat["nb"] - 1)


def manche_suivante(etat: dict) -> str:
    """Nouvelle donne ; avec les échanges, les dons d'office puis la main au Président."""
    nb = etat["nb"]
    etat["manche"] += 1
    distribuer(etat)
    message = f"La manche {etat['manche']} commence."
    if not etat["options"]["echanges"]:
        _commencer_les_plis(etat)
        pauvre = etat["actif"]
        return f"{message} {'Tu entames' if pauvre == 0 else nom_joueur(pauvre) + ' entame'}."

    paires = [(nb - 1, 0, 2)]  # Pauvre -> Président, 2 cartes
    if nb >= 4:
        paires.append((nb - 2, 1, 1))  # Vice-pauvre -> Vice-président, 1 carte
    for rang_donneur, rang_receveur, nombre in paires:
        donneur, receveur = _par_rang(etat, rang_donneur), _par_rang(etat, rang_receveur)
        meilleures = trier(etat["mains"][donneur])[-nombre:]
        _donner(etat, donneur, receveur, meilleures)
        etat["a_rendre"].append({"donneur": receveur, "receveur": donneur, "nombre": nombre})
        message += " " + _message_don(etat, donneur, receveur, nombre)
    etat["phase"] = "echange"
    etat["actif"] = etat["a_rendre"][0]["donneur"]
    return message


def destinataire(etat: dict) -> str:
    """« Pauvre » ou « Vice-pauvre » : à qui le joueur actif doit rendre des cartes."""
    retour = etat["a_rendre"][0]
    return nom_rang(etat["rangs"][retour["receveur"]], etat["nb"])


def rendre(etat: dict, j: int, cartes: list[str]) -> str:
    """Le retour du Président ou du Vice-président : un coup privé, ce message est le sien."""
    _exiger_cartes(etat, j, cartes)
    retour = etat["a_rendre"].pop(0)
    message = f"{_verbe(j, 'donnes', 'donne')} {_etiquettes(cartes)} au " + nom_rang(
        etat["rangs"][retour["receveur"]], etat["nb"]
    ) + "."
    _donner(etat, j, retour["receveur"], list(cartes))
    if etat["a_rendre"]:
        etat["actif"] = etat["a_rendre"][0]["donneur"]
    else:
        _commencer_les_plis(etat)
    return message
