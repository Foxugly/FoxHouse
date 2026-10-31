"""Combinaisons du rami : suites, brelans (et carrés), jokers, points. N'importe pas Django.

Une « nature » est une carte sans son numéro de paquet ("7H"). Ce que représente
un joker est une nature, ou "<valeur>*" (« un <valeur> d'une enseigne manquante »)
dans un brelan de trois cartes.
"""

from dataclasses import dataclass

from tapis.cartes import ENSEIGNES, VALEURS, enseigne, est_carte, est_joker, nature, valeur

REGLES_AS = ("bas1_haut11", "toujours1", "toujours11")
_RANG_AS_HAUT = len(VALEURS)  # l'as placé au-dessus du roi


@dataclass(frozen=True)
class Combinaison:
    type: str  # "suite" | "brelan" (un carré est un brelan)
    cartes: tuple[str, ...]  # ordre d'affichage ; une suite va du bas vers le haut
    jokers: tuple[tuple[str, str], ...]  # (id du joker, ce qu'il représente)


def _decouper(nat: str) -> tuple[str, str]:
    """"10H" -> ("10", "H") ; "K*" -> ("K", "*")."""
    return nat[:-1], nat[-1]


def _est_nature(nat) -> bool:
    return isinstance(nat, str) and est_carte(f"{nat}-1") and not est_joker(f"{nat}-1")


def _suite(elements: list[tuple[str, str]], libre: str | None) -> Combinaison | None:
    """elements : (id, nature) des cartes placées ; libre : un joker à placer, ou None."""
    enseignes = {_decouper(n)[1] for _, n in elements}
    if len(enseignes) != 1:
        return None
    e = enseignes.pop()
    vals = [_decouper(n)[0] for _, n in elements]
    if len(set(vals)) != len(vals):
        return None
    # L'as est soit en bas (rang 0), soit en haut (rang 13), jamais les deux :
    # chaque lecture ne place les rangs que sur 13 valeurs, donc ni tour ni 14 cartes.
    for as_haut in (False, True):
        if as_haut and "A" not in vals:
            continue
        rangs = {
            _RANG_AS_HAUT if (as_haut and v == "A") else VALEURS.index(v): id_
            for (id_, _), v in zip(elements, vals)
        }
        bas, haut = min(rangs), max(rangs)
        trous = [r for r in range(bas, haut + 1) if r not in rangs]
        if libre is not None:
            if len(trous) > 1:
                continue
            if trous:
                r = trous[0]
            elif haut + 1 < _RANG_AS_HAUT or (haut + 1 == _RANG_AS_HAUT and "A" not in vals):
                # En haut si possible : l'as au-dessus du roi aussi, sauf si la suite
                # a déjà un as en bas ; rien au-dessus d'un as en haut.
                r = haut + 1
            elif bas > (1 if as_haut else 0):
                r = bas - 1
            else:
                continue
            rangs[r] = libre
        elif trous:
            continue
        ordre = sorted(rangs)
        jokers = tuple(
            (rangs[r], f"{VALEURS[r % len(VALEURS)]}{e}") for r in ordre if est_joker(rangs[r])
        )
        return Combinaison("suite", tuple(rangs[r] for r in ordre), jokers)
    return None


def _brelan(elements: list[tuple[str, str]], libre: str | None) -> Combinaison | None:
    total = len(elements) + (libre is not None)
    if total not in (3, 4):
        return None
    vals = {_decouper(n)[0] for _, n in elements}
    if len(vals) != 1:
        return None
    v = vals.pop()
    enseignes = [_decouper(n)[1] for _, n in elements]
    if len(set(enseignes)) != len(enseignes):
        return None
    places = sorted(zip(enseignes, elements), key=lambda x: ENSEIGNES.index(x[0]))
    cartes = [id_ for _, (id_, _) in places]
    jokers = [(id_, n) for id_, n in elements if est_joker(id_)]
    if libre is not None:
        if total == 4:
            manquante = next(e for e in ENSEIGNES if e not in enseignes)
            cartes.insert(ENSEIGNES.index(manquante), libre)
            jokers.append((libre, f"{v}{manquante}"))
        else:
            cartes.append(libre)
            jokers.append((libre, f"{v}*"))
    return Combinaison("brelan", tuple(cartes), tuple(jokers))


def analyser(cartes: list[str], jokers_fixes: dict[str, str] | None = None) -> Combinaison | None:
    """La combinaison formée par ces cartes (dans n'importe quel ordre), ou None.

    jokers_fixes : ce que représentent les jokers déjà posés ; ils le gardent, sauf
    un "<valeur>*" qui devient l'enseigne manquante quand le brelan devient carré.
    """
    jokers_fixes = jokers_fixes or {}
    if not all(est_carte(c) for c in cartes) or len(set(cartes)) != len(cartes):
        return None
    jokers = [c for c in cartes if est_joker(c)]
    normales = [c for c in cartes if not est_joker(c)]
    if len(cartes) < 3 or len(jokers) > 1 or len(normales) < 2:
        return None
    elements = [(c, nature(c)) for c in normales]
    libre = None
    valeur_imposee = None
    if jokers:
        joker = jokers[0]
        fixe = jokers_fixes.get(joker)
        if fixe is None:
            libre = joker
        elif isinstance(fixe, str) and fixe.endswith("*"):
            libre = joker
            valeur_imposee = fixe[:-1]
        elif _est_nature(fixe):
            elements.append((joker, fixe))
        else:
            return None
    if valeur_imposee is not None:
        comb = _brelan(elements, libre)
        if comb is None or valeur(normales[0]) != valeur_imposee:
            return None
        return comb
    return _suite(elements, libre) or _brelan(elements, libre)


def ajouter(comb: Combinaison, cartes: list[str]) -> Combinaison | None:
    """La combinaison complétée par ces cartes, les jokers gardant ce qu'ils représentent."""
    return analyser(list(comb.cartes) + list(cartes), dict(comb.jokers))


def recuperer_joker(comb: Combinaison, carte: str) -> tuple[Combinaison, str] | None:
    """Remplace le joker par cette carte : (nouvelle combinaison, id du joker libéré), ou None."""
    if not comb.jokers or not est_carte(carte) or est_joker(carte):
        return None
    joker, represente = comb.jokers[0]
    v, e = _decouper(represente)
    if e == "*":
        presentes = {enseigne(c) for c in comb.cartes if not est_joker(c)}
        if valeur(carte) != v or enseigne(carte) in presentes:
            return None
    elif nature(carte) != represente:
        return None
    restantes = [carte if c == joker else c for c in comb.cartes]
    nouvelle = analyser(restantes)
    if nouvelle is None:
        return None
    return nouvelle, joker


def _valeur_points(v: str, regle_as: str, as_en_bas: bool) -> int:
    if v == "A":
        if regle_as == "toujours1":
            return 1
        if regle_as == "toujours11":
            return 11
        return 1 if as_en_bas else 11
    if v in ("J", "Q", "K"):
        return 10
    return int(v)


def _verifier_regle(regle_as: str) -> None:
    if regle_as not in REGLES_AS:
        raise ValueError(f"Règle de l'as inconnue : {regle_as!r}")


def points(comb: Combinaison, regle_as: str) -> int:
    """Points de la combinaison posée ; un joker vaut la carte qu'il représente."""
    _verifier_regle(regle_as)
    represente = dict(comb.jokers)
    total = 0
    for i, c in enumerate(comb.cartes):
        v = _decouper(represente[c])[0] if est_joker(c) else valeur(c)
        as_en_bas = comb.type == "suite" and i == 0
        total += _valeur_points(v, regle_as, as_en_bas)
    return total


def penalite(carte: str, regle_as: str, penalite_joker: int) -> int:
    """Pénalité d'une carte restée en main : un as vaut 1 avec "toujours1", 11 sinon."""
    _verifier_regle(regle_as)
    if est_joker(carte):
        return penalite_joker
    return _valeur_points(valeur(carte), regle_as, as_en_bas=False)


def vers_dict(comb: Combinaison) -> dict:
    return {"type": comb.type, "cartes": list(comb.cartes), "jokers": dict(comb.jokers)}


def depuis_dict(d: dict) -> Combinaison:
    return Combinaison(d["type"], tuple(d["cartes"]), tuple(d["jokers"].items()))
