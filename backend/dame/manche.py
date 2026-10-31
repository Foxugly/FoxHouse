"""Règles de la dame de pique : donne, échange, plis, points (spec jeux §2). N'importe pas Django.

Les fonctions modifient l'état reçu ; c'est l'appelant qui le copie.

L'échange se joue un siège après l'autre, dans l'ordre 1, 2, …, n − 1, puis 0 : le joueur
humain (siège 0) choisit donc en dernier, et le message de son don peut lui dire ce qu'il
reçoit. Les cartes choisies quittent la main mais attendent dans `dons` : personne ne reçoit
avant que tous aient choisi.
"""

from tapis.cartes import enseigne, melanger, paquet, valeur
from tapis.jeu import CoupRefuse

DEUX_TREFLE = "2C-1"
DAME_PIQUE = "QS-1"
VALET_CARREAU = "JD-1"
NB_DONNEES = 3
POINTS_CHELEM = 26

RETIREES = {3: ["2D-1"], 4: [], 5: ["2D-1", "2S-1"], 6: ["2D-1", "2S-1", "3D-1", "3S-1"]}
SENS_A_QUATRE = ("gauche", "droite", "en_face", "aucun")
SENS_AUTRES = ("gauche", "droite", "aucun")
LIBELLES_SENS = {
    "gauche": "vers la gauche", "droite": "vers la droite", "en_face": "en face", "aucun": "aucun",
}
COULEURS = {"S": "pique", "H": "cœur", "D": "carreau", "C": "trèfle"}
_SYMBOLES = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
_FIGURES = {"A": "A", "K": "R", "Q": "D", "J": "V"}
_RANGS = {v: r for r, v in enumerate(["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"])}
ORDRE_COULEURS = {"S": 0, "H": 1, "C": 2, "D": 3}  # couleurs alternées dans la main


def nom_joueur(j: int) -> str:
    return "Toi" if j == 0 else f"Ordinateur {j}"


def _verbe(j: int, humain: str, ordi: str) -> str:
    return f"Tu {humain}" if j == 0 else f"{nom_joueur(j)} {ordi}"


def _a(j: int) -> str:
    return "à toi" if j == 0 else f"à {nom_joueur(j)}"


def _de(j: int) -> str:
    return "de toi" if j == 0 else f"d'{nom_joueur(j)}"


def etiquette(carte: str) -> str:
    v = valeur(carte)
    return f"{_FIGURES.get(v, v)}{_SYMBOLES[enseigne(carte)]}"


def enumerer(cartes: list[str]) -> str:
    noms = [etiquette(c) for c in cartes]
    return noms[0] if len(noms) == 1 else f"{', '.join(noms[:-1])} et {noms[-1]}"


def rang(carte: str) -> int:
    return _RANGS[valeur(carte)]


def trier(main: list[str]) -> list[str]:
    return sorted(main, key=lambda c: (ORDRE_COULEURS[enseigne(c)], rang(c)))


def _points_s(n: int) -> str:
    return f"{n} point" if abs(n) <= 1 else f"{n} points"


# --- Donne et échange --------------------------------------------------------------------


def sens_de_la_manche(options: dict, nb: int, manche: int) -> str:
    if not options["echange"]:
        return "aucun"
    cycle = SENS_A_QUATRE if nb == 4 else SENS_AUTRES
    return cycle[(manche - 1) % len(cycle)]


def destinataire(etat: dict, s: int) -> int:
    decalage = {"gauche": 1, "droite": -1, "en_face": 2}[etat["sens"]]
    return (s + decalage) % etat["nb"]


def ordre_echange(nb: int) -> list[int]:
    return list(range(1, nb)) + [0]


def nouvel_etat(options: dict, nb: int, graine: int) -> dict:
    etat = {
        "options": options,
        "graine": graine,
        "nb": nb,
        "manche": 1,
        "scores": [],
    }
    distribuer(etat)
    return etat


def distribuer(etat: dict) -> None:
    nb = etat["nb"]
    cartes = [c for c in paquet(1, 0) if c not in RETIREES[nb]]
    cartes = melanger(cartes, etat["graine"] * 100 + etat["manche"])
    par_main = len(cartes) // nb
    etat["mains"] = [trier(cartes[k * par_main:(k + 1) * par_main]) for k in range(nb)]
    etat["sens"] = sens_de_la_manche(etat["options"], nb, etat["manche"])
    etat["dons"] = [None] * nb
    etat["recues"] = [[] for _ in range(nb)]
    etat["pli"] = []
    etat["dernier_pli"] = []
    etat["ramassees"] = [[] for _ in range(nb)]
    etat["coeurs_ouverts"] = False
    etat["plis_joues"] = 0
    if etat["sens"] == "aucun":
        _commencer_les_plis(etat)
    else:
        etat["phase"] = "echange"
        etat["actif"] = ordre_echange(nb)[0]


def _commencer_les_plis(etat: dict) -> None:
    etat["phase"] = "plis"
    etat["actif"] = next(s for s, main in enumerate(etat["mains"]) if DEUX_TREFLE in main)


def donner(etat: dict, j: int, cartes: list[str]) -> str:
    """Met les cartes de côté ; le dernier don fait l'échange. Rend le message de l'auteur."""
    if len(set(cartes)) != len(cartes):
        raise CoupRefuse("Choisis 3 cartes différentes.")
    for c in cartes:
        etat["mains"][j].remove(c)
    etat["dons"][j] = list(cartes)
    receveur = destinataire(etat, j)
    message = f"{_verbe(j, 'donnes', 'donne')} {enumerer(cartes)} {_a(receveur)}."
    ordre = ordre_echange(etat["nb"])
    suivant = ordre.index(j) + 1
    if suivant < len(ordre):
        etat["actif"] = ordre[suivant]
        return message
    _echanger(etat)
    donneur = next(s for s in range(etat["nb"]) if destinataire(etat, s) == j)
    recu = f"{_verbe(j, 'reçois', 'reçoit')} {enumerer(etat['recues'][j])} {_de(donneur)}."
    return f"{message} {recu}"


def _echanger(etat: dict) -> None:
    for s, cartes in enumerate(etat["dons"]):
        receveur = destinataire(etat, s)
        etat["mains"][receveur] = trier(etat["mains"][receveur] + cartes)
        etat["recues"][receveur] = trier(cartes)
    etat["dons"] = [None] * etat["nb"]
    _commencer_les_plis(etat)


# --- Plis ----------------------------------------------------------------------------------


def _est_coeur(c: str) -> bool:
    return enseigne(c) == "H"


def motif_de_refus(etat: dict, j: int, carte: str) -> str | None:
    """Pourquoi le joueur j ne peut pas jouer `carte` (qu'il a en main) ; None s'il le peut."""
    main = etat["mains"][j]
    pli = etat["pli"]
    premier_pli = etat["plis_joues"] == 0
    if not pli:
        if premier_pli and carte != DEUX_TREFLE:
            return "Entame avec le 2♣."
        if _est_coeur(carte) and not etat["coeurs_ouverts"] and not all(map(_est_coeur, main)):
            return "Les cœurs ne sont pas encore ouverts."
        return None
    demandee = enseigne(pli[0][1])
    if enseigne(carte) != demandee:
        if any(enseigne(c) == demandee for c in main):
            return f"Tu dois fournir : {COULEURS[demandee]}."
        if premier_pli and (_est_coeur(carte) or carte == DAME_PIQUE):
            if any(not _est_coeur(c) and c != DAME_PIQUE for c in main):
                return "Pas de cœur ni de dame de pique au premier pli."
    return None


def cartes_jouables(etat: dict, j: int) -> list[str]:
    return [c for c in etat["mains"][j] if motif_de_refus(etat, j, c) is None]


def points_des_cartes(cartes: list[str], options: dict) -> int:
    points = sum(1 for c in cartes if _est_coeur(c))
    if DAME_PIQUE in cartes:
        points += 13
    if options["valet_carreau"] and VALET_CARREAU in cartes:
        points -= 10
    return points


def jouer(etat: dict, j: int, carte: str) -> str:
    motif = motif_de_refus(etat, j, carte)
    if motif:
        raise CoupRefuse(motif)
    etat["mains"][j].remove(carte)
    etat["dernier_pli"] = []
    etat["pli"].append([j, carte])
    if _est_coeur(carte):
        etat["coeurs_ouverts"] = True
    message = f"{_verbe(j, 'joues', 'joue')} {etiquette(carte)}."
    if len(etat["pli"]) < etat["nb"]:
        etat["actif"] = (j + 1) % etat["nb"]
        return message
    return f"{message} {_ramasser(etat)}"


def gagnant_du_pli(pli: list) -> int:
    demandee = enseigne(pli[0][1])
    return max((p for p in pli if enseigne(p[1]) == demandee), key=lambda p: rang(p[1]))[0]


def _ramasser(etat: dict) -> str:
    pli = etat["pli"]
    gagnant = gagnant_du_pli(pli)
    cartes = [c for _, c in pli]
    etat["ramassees"][gagnant] += cartes
    etat["plis_joues"] += 1
    etat["dernier_pli"] = pli
    etat["pli"] = []
    etat["actif"] = gagnant
    points = points_des_cartes(cartes, etat["options"])
    message = f"{_verbe(gagnant, 'remportes', 'remporte')} le pli ({_points_s(points)})."
    if not any(etat["mains"]):
        message += _fin_de_manche(etat)
    return message


def _fin_de_manche(etat: dict) -> str:
    """Compte les points de la manche ; rend la fin du message du dernier pli."""
    options = etat["options"]
    ramassees = etat["ramassees"]
    chelem = next(
        (s for s, r in enumerate(ramassees)
         if DAME_PIQUE in r and sum(1 for c in r if _est_coeur(c)) == 13),
        None,
    )
    valet = options["valet_carreau"]
    if chelem is None:
        ligne = [points_des_cartes(r, options) for r in ramassees]
        message = ""
    else:
        ligne = [
            (0 if s == chelem else POINTS_CHELEM) - (10 if valet and VALET_CARREAU in r else 0)
            for s, r in enumerate(ramassees)
        ]
        message = (
            f" {_verbe(chelem, 'réussis', 'réussit')} le grand chelem : "
            f"chacun des autres marque {POINTS_CHELEM}."
        )
    etat["scores"].append(ligne)
    etat["actif"] = 0
    if max(totaux(etat)) >= options["score_fin"]:
        etat["phase"] = "terminee"
        return f"{message} La partie est terminée."
    etat["phase"] = "fin_manche"
    return f"{message} La manche est terminée."


def totaux(etat: dict) -> list[int]:
    return [sum(ligne[s] for ligne in etat["scores"]) for s in range(etat["nb"])]


def manche_suivante(etat: dict) -> str:
    etat["manche"] += 1
    distribuer(etat)
    if etat["sens"] == "aucun":
        return f"La manche {etat['manche']} commence, sans échange."
    return f"La manche {etat['manche']} commence : échange {LIBELLES_SENS[etat['sens']]}."
