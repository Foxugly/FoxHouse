"""Les adversaires de la machine au rami (spec §6.5). N'importe pas Django.

Sans stratégie, mais ils font avancer la partie : ils ne choisissent que parmi les actions
permises et respectent les mêmes conditions que les règles, pour que `Rami.appliquer`
accepte toujours leur coup. Le choix est déterministe. Ils ne récupèrent jamais de joker.
"""

from rami.combinaisons import Combinaison, ajouter, analyser, depuis_dict, penalite, points
from rami.poses import OUVERTURE_MINIMUM
from rami.vue import actions_permises
from tapis.cartes import VALEURS, enseigne, est_joker, valeur

_RANG_AS_HAUT = len(VALEURS)


def _coup(action: str, cartes=(), cible=None) -> dict:
    return {"action": action, "cartes": list(cartes), "cible": cible}


# --- Le plan : les combinaisons sans joker que la main permet de poser ---------------------


def _une_par_nature(main: list[str]) -> dict[tuple[str, str], str]:
    """(valeur, enseigne) -> la plus petite carte de cette nature (l'autre paquet attend)."""
    cartes = {}
    for c in sorted(main):
        if not est_joker(c):
            cartes.setdefault((valeur(c), enseigne(c)), c)
    return cartes


def _brelans(natures: dict) -> list[list[str]]:
    """Par valeur : les 3 ou 4 enseignes distinctes, et chaque brelan tiré d'un carré."""
    par_valeur: dict[str, list[str]] = {}
    for (v, _), c in natures.items():
        par_valeur.setdefault(v, []).append(c)
    brelans = []
    for cartes in par_valeur.values():
        if len(cartes) >= 3:
            brelans.append(cartes)
        if len(cartes) == 4:
            brelans += [[c for c in cartes if c != sans] for sans in cartes]
    return brelans


def _suites(natures: dict) -> list[list[str]]:
    """Par enseigne, les suites maximales ; l'as compte en bas (rang 0) et en haut (rang 13)."""
    par_enseigne: dict[str, dict[int, str]] = {}
    for (v, e), c in natures.items():
        rangs = par_enseigne.setdefault(e, {})
        rangs[VALEURS.index(v)] = c
        if v == "A":
            rangs[_RANG_AS_HAUT] = c
    suites = []
    for rangs in par_enseigne.values():
        r = 0
        while r <= _RANG_AS_HAUT:
            if r not in rangs:
                r += 1
                continue
            debut = r
            while r + 1 in rangs:
                r += 1
            fin = min(r, _RANG_AS_HAUT - 1) if debut == 0 else r  # l'as ne sert qu'une fois
            if fin - debut + 1 >= 3:
                suites.append([rangs[k] for k in range(debut, fin + 1)])
            r += 1
    return suites


def plan(main: list[str], regle_as: str) -> list[Combinaison]:
    """Les combinaisons sans joker et disjointes que l'adversaire vise.

    Brelans et suites maximales, triés par points décroissants puis id de la première
    carte. On retient la sélection disjointe qui vaut le plus de points ; à égalité, celle
    que préfère l'ordre du tri (le choix glouton quand il n'y a pas de conflit). Un choix
    purement glouton garderait le carré de 9 de 7♥ 8♥ 9♥ 9♠ 9♦ 9♣ (36 points) plutôt que la
    suite et le brelan (51 points), qui ouvrent.
    """
    natures = _une_par_nature(main)
    combs = {analyser(cartes) for cartes in _brelans(natures) + _suites(natures)}
    candidats = sorted(
        ((points(c, regle_as), c) for c in combs if c is not None),
        key=lambda pc: (-pc[0], pc[1].cartes[0], pc[1].cartes),
    )
    reste = [0] * (len(candidats) + 1)  # points encore disponibles à partir de l'indice i
    for i in range(len(candidats) - 1, -1, -1):
        reste[i] = reste[i + 1] + candidats[i][0]
    meilleur: list = [0, []]

    def explorer(i: int, prises: frozenset, choisis: list[int], total: int) -> None:
        if total > meilleur[0]:
            meilleur[:] = [total, list(choisis)]
        if i == len(candidats) or total + reste[i] <= meilleur[0]:
            return
        pts, comb = candidats[i]
        if prises.isdisjoint(comb.cartes):
            choisis.append(i)
            explorer(i + 1, prises | set(comb.cartes), choisis, total + pts)
            choisis.pop()
        explorer(i + 1, prises, choisis, total)

    explorer(0, frozenset(), [], 0)
    return [candidats[i][1] for i in meilleur[1]]


# --- Ce que les règles exigent ------------------------------------------------------------


def _garde_une_carte(etat: dict) -> bool:
    return etat["options"]["finir_par_defausse"]


def _amputer(comb: Combinaison, epargner: str | None) -> list[str] | None:
    """La combinaison moins une carte (ni `epargner`), encore valide ; None si impossible."""
    if len(comb.cartes) < 4:
        return None
    if comb.type == "suite":
        bouts = [comb.cartes[-1], comb.cartes[0]]  # en haut d'abord
    else:
        bouts = list(reversed(comb.cartes))
    retiree = next(c for c in bouts if c != epargner)
    return [c for c in comb.cartes if c != retiree]


def _ouverture(etat: dict, cartes: list[str]) -> list[list[str]]:
    """Les combinaisons d'ouverture tirées de ces cartes (la main et le brouillon)."""
    combs = [list(c.cartes) for c in plan(cartes, etat["options"]["as"])]
    if combs and _garde_une_carte(etat) and sum(map(len, combs)) == len(cartes):
        amputee = _amputer(analyser(combs[-1]), None)
        combs[-1:] = [amputee] if amputee else []
    return combs


def _ouverture_suffit(etat: dict, combs: list[list[str]]) -> bool:
    analyses = [analyser(c) for c in combs]
    total = sum(points(c, etat["options"]["as"]) for c in analyses)
    if total < OUVERTURE_MINIMUM:
        return False
    return not etat["options"]["ouverture_suite_sans_joker"] or any(
        c.type == "suite" and not c.jokers for c in analyses
    )


def _va_sur_la_table(etat: dict, carte: str) -> str | None:
    """L'id du premier groupe de la table que cette carte complète, ou None."""
    joker = est_joker(carte)
    for g in etat["table"]:
        # Tri rapide avant l'analyse complète : même enseigne pour une suite, même valeur
        # pour un brelan (un groupe contient toujours au moins deux cartes normales).
        repere = next(c for c in g["cartes"] if not est_joker(c))
        lien = enseigne if g["type"] == "suite" else valeur
        if not joker and lien(carte) != lien(repere):
            continue
        if ajouter(depuis_dict(g), [carte]) is not None:
            return g["id"]
    return None


# --- Les choix, phase par phase -----------------------------------------------------------


def _piocher_ou_prendre(etat: dict, j: int, permises: set[str]) -> dict:
    """Prendre la défausse seulement après l'ouverture, pour la poser, avec 2 cartes de reste."""
    if "prendre_defausse" in permises and etat["ouvert"][j]:
        carte = etat["defausse"][-1]
        main = etat["mains"][j] + [carte]
        for comb in plan(main, etat["options"]["as"]):
            if carte in comb.cartes and len(main) - len(comb.cartes) >= 2:
                return _coup("prendre_defausse")
        if len(main) - 1 >= 2 and _va_sur_la_table(etat, carte) is not None:
            return _coup("prendre_defausse")
    return _coup("piocher")


def _defausse(etat: dict, j: int, main: list[str], plan_cartes: set[str]) -> dict:
    """La carte de plus forte pénalité hors du plan, ni joker, ni la carte prise ce tour."""
    prise = etat["prise"]
    if etat["options"]["defausse_a_poser"] and prise in main:
        return _coup("rendre_defausse")  # la défausserait sinon : refusé par les règles
    opts = etat["options"]

    def cout(c: str) -> tuple[int, str]:
        return (-penalite(c, opts["as"], opts["penalite_joker"]), c)

    autres = [c for c in main if c != prise] or main
    normales = [c for c in autres if not est_joker(c)]
    choix = [c for c in normales if c not in plan_cartes] or normales or autres
    return _coup("defausser", [min(choix, key=cout)])


def _avant_ouverture(etat: dict, j: int, permises: set[str]) -> dict:
    """L'ouverture se calcule sur la main et le brouillon : elle ne change pas en cours de
    pose, et l'adversaire n'alterne jamais poser et annuler."""
    main = etat["mains"][j]
    brouillon = [d["cartes"] for d in etat["brouillon"]]
    cartes = main + [c for d in brouillon for c in d]
    ouverture = _ouverture(etat, cartes)
    if _ouverture_suffit(etat, ouverture):
        deja = [set(d) for d in brouillon]
        if deja == [set(c) for c in ouverture[: len(deja)]]:
            if len(deja) < len(ouverture):
                return _coup("poser", sorted(ouverture[len(deja)]))
            return _coup("valider_ouverture")
        return _coup("annuler")  # un brouillon qui n'est pas le nôtre : on repart de la main
    if brouillon and _ouverture_suffit(etat, brouillon) and "valider_ouverture" in permises:
        return _coup("valider_ouverture")
    if brouillon:
        return _coup("annuler")
    return _defausse(etat, j, main, {c for comb in ouverture for c in comb})


def _apres_ouverture(etat: dict, j: int) -> dict:
    main = etat["mains"][j]
    combs = plan(main, etat["options"]["as"])
    for comb in combs[:1]:
        cartes = list(comb.cartes)
        if _garde_une_carte(etat) and len(cartes) == len(main):
            cartes = _amputer(comb, etat["prise"])
        if cartes:
            return _coup("poser", sorted(cartes))
    if not (_garde_une_carte(etat) and len(main) == 1):
        for carte in sorted(main):
            groupe = _va_sur_la_table(etat, carte)
            if groupe is not None:
                return _coup("ajouter", [carte], groupe)
    return _defausse(etat, j, main, {c for comb in combs for c in comb.cartes})


def choisir(etat: dict, j: int) -> dict:
    """Le coup de l'adversaire j, toujours parmi ses actions permises."""
    permises = {a["id"] for a in actions_permises(etat, j)}
    if not permises:
        raise ValueError(f"Le joueur {j} n'a rien à jouer.")
    if etat["phase"] == "fin_manche":
        return _coup("manche_suivante")
    if etat["phase"] == "piocher":
        return _piocher_ou_prendre(etat, j, permises)
    if not etat["ouvert"][j]:
        return _avant_ouverture(etat, j, permises)
    return _apres_ouverture(etat, j)
