"""Règles du whist à la couleur : donne, trou, enchères, plis, points (spec whist). N'importe pas Django.

Les fonctions modifient l'état reçu ; c'est l'appelant qui le copie.

Une donne : distribution (13 cartes chacun, la dernière, celle du donneur, est retournée), trou
éventuel, enchères, choix de l'atout (abondance, solo slim), plis, bilan. Une donne où tout le
monde passe est rejouée par le donneur suivant et ne compte pas.
"""

from tapis.cartes import enseigne, melanger, paquet, valeur
from tapis.jeu import CoupRefuse

NB = 4
NB_PLIS = 13
COULEURS = {"S": "pique", "H": "cœur", "D": "carreau", "C": "trèfle"}
_SYMBOLES = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
_FIGURES = {"A": "A", "K": "R", "Q": "D", "J": "V"}
_ORDRE_VALEURS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
_RANGS = {v: r for r, v in enumerate(_ORDRE_VALEURS)}
ORDRE_COULEURS = {"S": 0, "H": 1, "C": 2, "D": 3}  # couleurs alternées dans la main

# Contrats : rang d'enchère, libellé, plis visés, preneurs à deux (2 contre 2) et atout
# (« retourne », « choisi » ou « sans »). Le rang de l'emballage est celui de la demande : une
# demande acceptée ne monte pas, seul un contrat plus haut la couvre.
CONTRATS = {
    "demande": (1, "Demande", 8, True, "retourne"),
    "emballage": (1, "Emballage", 8, True, "retourne"),
    "trou": (1, "Trou", 8, True, "retourne"),
    "seul": (2, "Seul", 5, False, "retourne"),
    "abondance_9": (3, "Abondance 9", 9, False, "choisi"),
    "misere": (4, "Misère", 0, False, "sans"),
    "abondance_10": (5, "Abondance 10", 10, False, "choisi"),
    "abondance_11": (6, "Abondance 11", 11, False, "choisi"),
    "misere_ouverte": (7, "Misère ouverte", 0, False, "sans"),
    "abondance_12": (8, "Abondance 12", 12, False, "choisi"),
    "solo": (9, "Solo", 13, False, "retourne"),
    "solo_slim": (10, "Solo slim", 13, False, "choisi"),
}
# Les annonces, dans l'ordre des boutons ; « demander » annonce la demande.
ANNONCES = [
    "demander", "seul", "abondance_9", "misere", "abondance_10", "abondance_11",
    "misere_ouverte", "abondance_12", "solo", "solo_slim",
]
MISERES = ("misere", "misere_ouverte")
VALEURS_FIXES = {
    "abondance_9": 5, "abondance_10": 7, "abondance_11": 10, "abondance_12": 15,
    "misere": 7, "misere_ouverte": 15, "solo": 25, "solo_slim": 30,
}


def contrat_de_l_annonce(annonce: str) -> str:
    return "demande" if annonce == "demander" else annonce


def libelle(code: str) -> str:
    return CONTRATS[code][1]


def rang_enchere(code: str) -> int:
    return CONTRATS[code][0]


def but(code: str) -> int:
    return CONTRATS[code][2]


def a_deux(code: str) -> bool:
    return CONTRATS[code][3]


# --- Textes --------------------------------------------------------------------------------


def nom_joueur(j: int) -> str:
    return "Toi" if j == 0 else f"Ordinateur {j}"


def _verbe(j: int, humain: str, ordi: str) -> str:
    return f"Tu {humain}" if j == 0 else f"{nom_joueur(j)} {ordi}"


def _complement(j: int) -> str:
    """Le nom en complément (« avec toi », « pour Ordinateur 2 »)."""
    return "toi" if j == 0 else nom_joueur(j)


def noms(sieges: list[int]) -> str:
    """« Ordinateur 1 et toi » : le joueur humain en dernier, « toi » en minuscules."""
    ordre = sorted(sieges, key=lambda s: (s == 0, s))
    textes = [_complement(s) for s in ordre]
    return textes[0] if len(textes) == 1 else f"{', '.join(textes[:-1])} et {textes[-1]}"


def majuscule(texte: str) -> str:
    return texte[0].upper() + texte[1:]


def etiquette(carte: str) -> str:
    v = valeur(carte)
    return f"{_FIGURES.get(v, v)}{_SYMBOLES[enseigne(carte)]}"


def nom_atout(atout: str | None) -> str:
    return "sans atout" if atout is None else COULEURS[atout]


def _signe(n: int) -> str:
    return f"+{n}" if n >= 0 else f"−{-n}"


def _plis_s(n: int) -> str:
    return f"{n} pli" if n <= 1 else f"{n} plis"


def rang(carte: str) -> int:
    return _RANGS[valeur(carte)]


def trier(main: list[str]) -> list[str]:
    return sorted(main, key=lambda c: (ORDRE_COULEURS[enseigne(c)], rang(c)))


# --- Donne et trou -------------------------------------------------------------------------


def nouvel_etat(options: dict, graine: int) -> dict:
    etat = {
        "options": options,
        "graine": graine,
        "nb": NB,
        "donneur": NB - 1,  # le joueur humain (siège 0), à sa gauche, parle et entame le premier
        "essais": 0,
        "scores": [],
    }
    distribuer(etat)
    return etat


def distribuer(etat: dict) -> str:
    """Une nouvelle donne du donneur courant ; rend le message du trou, s'il y en a un."""
    etat["essais"] += 1
    cartes = melanger(paquet(1, 0), etat["graine"] * 1000 + etat["essais"])
    donneur = etat["donneur"]
    mains = [[] for _ in range(NB)]
    # Une carte à chacun, en commençant à gauche du donneur : la dernière est au donneur.
    for k, c in enumerate(cartes):
        mains[(donneur + 1 + k) % NB].append(c)
    etat["mains"] = [trier(m) for m in mains]
    etat["retournee"] = cartes[-1]
    etat["enchere"] = None  # {"code", "preneur", "partenaire"}
    etat["passes"] = [False] * NB
    etat["contrat"] = None  # {"code", "preneurs"}
    etat["atout"] = None
    etat["pli"] = []
    etat["dernier_pli"] = []
    etat["jouees"] = []
    etat["plis"] = [0] * NB
    etat["plis_joues"] = 0
    etat["phase"] = "encheres"
    etat["actif"] = (donneur + 1) % NB
    return _trou(etat) if etat["options"]["trou"] else ""


def _detenteur(etat: dict, carte: str) -> int:
    return next(s for s, main in enumerate(etat["mains"]) if carte in main)


def _trou(etat: dict) -> str:
    for s, main in enumerate(etat["mains"]):
        as_ = [c for c in main if valeur(c) == "A"]
        if len(as_) < 3:
            continue
        if len(as_) == 3:
            quatrieme = next(f"A{e}-1" for e in COULEURS if f"A{e}-1" not in main)
            partenaire = _detenteur(etat, quatrieme)
            raison = _verbe(s, "as trois as", "a trois as")
            designe = "le quatrième as"
        else:
            # Les quatre as : le plus haut cœur qui lui manque désigne le partenaire.
            coeur = next(f"{v}H-1" for v in reversed(_ORDRE_VALEURS) if f"{v}H-1" not in main)
            partenaire = _detenteur(etat, coeur)
            raison = _verbe(s, "as les quatre as", "a les quatre as")
            designe = f"le {etiquette(coeur)}"
        joue = "joues" if s == 0 else "joue"
        qui = "as" if partenaire == 0 else "a"
        _fixer_contrat(etat, "trou", [s, partenaire])
        return (
            f"Trou ! {raison} et {joue} avec {_complement(partenaire)}, qui {qui} {designe} : "
            f"8 plis à deux, atout {nom_atout(etat['atout'])}."
        )
    return ""


# --- Enchères ------------------------------------------------------------------------------


def annonces_permises(etat: dict, j: int) -> list[str]:
    """Les annonces (hors « passer ») permises au joueur j pendant les enchères."""
    enchere = etat["enchere"]
    plus_haut = rang_enchere(enchere["code"]) if enchere else 0
    permises = []
    if (enchere and enchere["code"] == "demande" and enchere["partenaire"] is None
            and enchere["preneur"] != j):
        permises.append("accepter")
    for annonce in ANNONCES:
        if annonce in MISERES and not etat["options"]["misere"]:
            continue
        if rang_enchere(contrat_de_l_annonce(annonce)) > plus_haut:
            permises.append(annonce)
    return permises


def _detenteurs(enchere: dict | None) -> set[int]:
    if enchere is None:
        return set()
    return {s for s in (enchere["preneur"], enchere["partenaire"]) if s is not None}


def annoncer(etat: dict, j: int, annonce: str) -> str:
    if annonce == "passer":
        etat["passes"][j] = True
        message = f"{_verbe(j, 'passes', 'passe')}."
    elif annonce == "accepter":
        enchere = etat["enchere"]
        enchere["partenaire"] = j
        enchere["code"] = "emballage"
        message = (
            f"{_verbe(j, 'acceptes', 'accepte')} : emballage avec "
            f"{_complement(enchere['preneur'])}."
        )
    else:
        code = contrat_de_l_annonce(annonce)
        etat["enchere"] = {"code": code, "preneur": j, "partenaire": None}
        if code == "demande":
            message = f"{_verbe(j, 'demandes', 'demande')}."
        else:
            message = f"{_verbe(j, 'annonces', 'annonce')} {libelle(code).lower()}."
    return f"{message}{_suite_des_encheres(etat, j)}"


def _suite_des_encheres(etat: dict, j: int) -> str:
    enchere = etat["enchere"]
    detenteurs = _detenteurs(enchere)
    if not all(etat["passes"][s] for s in range(NB) if s not in detenteurs):
        etat["actif"] = next(
            s for s in ((j + k) % NB for k in range(1, NB))
            if not etat["passes"][s] and s not in detenteurs
        )
        return ""
    if enchere is None:
        return f" Tout le monde passe : {_rejouer(etat)}"
    if enchere["code"] == "demande":
        etat["phase"] = "demande_seule"
        etat["actif"] = enchere["preneur"]
        demandeur = enchere["preneur"]
        demande = "ta demande" if demandeur == 0 else f"la demande d'{nom_joueur(demandeur)}"
        return f" Personne n'accepte {demande}."
    return f" {_fixer_contrat(etat, enchere['code'], sorted(detenteurs))}"


def _rejouer(etat: dict) -> str:
    """Donne rejouée par le donneur suivant, sans point ; rend la fin du message."""
    etat["donneur"] = (etat["donneur"] + 1) % NB
    trou = distribuer(etat)
    message = f"la donne est rejouée, {_distribue(etat['donneur'])}."
    return f"{message} {trou}" if trou else message


def demande_seule(etat: dict, j: int, choix: str) -> str:
    """Demande que personne n'a acceptée : le demandeur joue seul ou passe."""
    if choix == "seul":
        etat["enchere"] = {"code": "seul", "preneur": j, "partenaire": None}
        return f"{_verbe(j, 'joues', 'joue')} seul. {_fixer_contrat(etat, 'seul', [j])}"
    return f"{_verbe(j, 'passes', 'passe')} : {_rejouer(etat)}"


def _fixer_contrat(etat: dict, code: str, preneurs: list[int]) -> str:
    etat["contrat"] = {"code": code, "preneurs": sorted(preneurs)}
    atout = CONTRATS[code][4]
    pour = f"Contrat : {libelle(code).lower()} pour {noms(preneurs)}"
    if atout == "choisi":
        etat["phase"] = "atout"
        etat["actif"] = preneurs[0]
        choisit = "choisis" if preneurs[0] == 0 else "choisit"
        return f"{pour}, qui {choisit} l'atout."
    etat["atout"] = enseigne(etat["retournee"]) if atout == "retourne" else None
    _commencer_les_plis(etat)
    if atout == "sans":
        return f"{pour}, sans atout."
    return f"{pour}, atout {nom_atout(etat['atout'])}."


def choisir_atout(etat: dict, j: int, couleur: str) -> str:
    etat["atout"] = couleur
    _commencer_les_plis(etat)
    return f"{_verbe(j, 'choisis', 'choisit')} l'atout : {COULEURS[couleur]}."


def _commencer_les_plis(etat: dict) -> None:
    etat["phase"] = "plis"
    etat["actif"] = (etat["donneur"] + 1) % NB


# --- Plis ----------------------------------------------------------------------------------


def motif_de_refus(etat: dict, j: int, carte: str) -> str | None:
    """Pourquoi le joueur j ne peut pas jouer `carte` (qu'il a en main) ; None s'il le peut."""
    pli = etat["pli"]
    if not pli:
        return None
    demandee = enseigne(pli[0][1])
    if enseigne(carte) != demandee and any(enseigne(c) == demandee for c in etat["mains"][j]):
        return f"Tu dois fournir : {COULEURS[demandee]}."
    return None


def cartes_jouables(etat: dict, j: int) -> list[str]:
    return [c for c in etat["mains"][j] if motif_de_refus(etat, j, c) is None]


def gagnant_du_pli(pli: list, atout: str | None) -> int:
    """Le plus haut atout, sinon la plus haute carte de la couleur demandée."""
    atouts = [p for p in pli if atout is not None and enseigne(p[1]) == atout]
    demandee = enseigne(pli[0][1])
    candidates = atouts or [p for p in pli if enseigne(p[1]) == demandee]
    return max(candidates, key=lambda p: rang(p[1]))[0]


def camp(etat: dict, j: int) -> set[int]:
    """Les sièges du camp de j (lui compris) : les preneurs ou leurs adversaires."""
    preneurs = set(etat["contrat"]["preneurs"])
    return preneurs if j in preneurs else set(range(NB)) - preneurs


def jouer(etat: dict, j: int, carte: str) -> str:
    motif = motif_de_refus(etat, j, carte)
    if motif:
        raise CoupRefuse(motif)
    etat["mains"][j].remove(carte)
    etat["dernier_pli"] = []
    etat["pli"].append([j, carte])
    etat["jouees"].append(carte)
    message = f"{_verbe(j, 'joues', 'joue')} {etiquette(carte)}."
    if len(etat["pli"]) < NB:
        etat["actif"] = (j + 1) % NB
        return message
    return f"{message} {_ramasser(etat)}"


def _ramasser(etat: dict) -> str:
    pli = etat["pli"]
    gagnant = gagnant_du_pli(pli, etat["atout"])
    etat["plis"][gagnant] += 1
    etat["plis_joues"] += 1
    etat["dernier_pli"] = pli
    etat["pli"] = []
    etat["actif"] = gagnant
    message = f"{_verbe(gagnant, 'remportes', 'remporte')} le pli."
    contrat = etat["contrat"]
    if contrat["code"] in MISERES and gagnant in contrat["preneurs"]:
        return f"{message} La misère est chutée.{_fin_de_donne(etat)}"
    if etat["plis_joues"] == NB_PLIS:
        return f"{message}{_fin_de_donne(etat)}"
    return message


# --- Points --------------------------------------------------------------------------------


def valeur_du_contrat(code: str, plis: int) -> tuple[bool, int]:
    """(réussi, valeur) d'un contrat dont les preneurs ont fait `plis` plis (spec §2)."""
    vise = but(code)
    if code in MISERES:
        return plis == 0, VALEURS_FIXES[code]
    reussi = plis >= vise
    if code in VALEURS_FIXES:
        return reussi, VALEURS_FIXES[code]
    base = 2 if a_deux(code) else 3
    if not reussi:
        return False, base + vise - plis
    if a_deux(code) and plis == NB_PLIS:
        return True, 2 * (base + NB_PLIS - vise)
    return True, base + plis - vise


def ligne_de_points(code: str, preneurs: list[int], plis: int) -> list[int]:
    """Les points de la donne pour chaque siège ; leur somme est nulle."""
    reussi, v = valeur_du_contrat(code, plis)
    gain = v if reussi else -v
    if len(preneurs) == 2:
        return [gain if s in preneurs else -gain for s in range(NB)]
    return [3 * gain if s in preneurs else -gain for s in range(NB)]


def _fin_de_donne(etat: dict) -> str:
    """Compte les points de la donne ; rend la fin du message du dernier pli."""
    contrat = etat["contrat"]
    preneurs = contrat["preneurs"]
    plis = sum(etat["plis"][s] for s in preneurs)
    reussi, _ = valeur_du_contrat(contrat["code"], plis)
    ligne = ligne_de_points(contrat["code"], preneurs, plis)
    etat["scores"].append(ligne)
    etat["actif"] = 0
    gain = ligne[preneurs[0]]
    perte = next(ligne[s] for s in range(NB) if s not in preneurs)
    if len(preneurs) == 2:
        marquent = "marquez" if 0 in preneurs else "marquent"
        bilan = (f"{majuscule(noms(preneurs))} {marquent} {_signe(gain)} chacun, "
                 f"les deux autres {_signe(perte)}.")
    else:
        preneur = preneurs[0]
        marque = "tu marques" if preneur == 0 else f"{nom_joueur(preneur)} marque"
        bilan = f"{marque} {_signe(gain)}, chacun des autres {_signe(perte)}."
    issue = "réussi" if reussi else "chuté"
    message = f" Contrat {issue} ({_plis_s(plis)}) : {bilan}"
    if len(etat["scores"]) >= etat["options"]["donnes"]:
        etat["phase"] = "terminee"
        return f"{message} La partie est terminée."
    etat["phase"] = "fin_donne"
    return f"{message} La donne est terminée."


def totaux(etat: dict) -> list[int]:
    return [sum(ligne[s] for ligne in etat["scores"]) for s in range(NB)]


def donne_suivante(etat: dict) -> str:
    etat["donneur"] = (etat["donneur"] + 1) % NB
    trou = distribuer(etat)
    debut = f"Donne {len(etat['scores']) + 1} : {_distribue(etat['donneur'])}."
    return f"{debut} {trou}" if trou else debut


def _distribue(donneur: int) -> str:
    return "tu distribues" if donneur == 0 else f"{nom_joueur(donneur)} distribue"
