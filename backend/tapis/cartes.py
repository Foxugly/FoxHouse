"""Cartes : identifiants, paquet, mélange. N'importe pas Django."""

import random
import re

VALEURS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
ENSEIGNES = ["S", "H", "D", "C"]
CACHEE = {"cachee": True}

_MOTIF = re.compile(r"^(?:(JK)|(.+?)([SHDC]))-(\d+)$")


def paquet(nb_jeux: int, nb_jokers: int) -> list[str]:
    """Paquet dans un ordre fixe : jeux 1..n (enseigne puis valeur), puis les jokers."""
    cartes = [
        f"{v}{e}-{p}"
        for p in range(1, nb_jeux + 1)
        for e in ENSEIGNES
        for v in VALEURS
    ]
    cartes += [f"JK-{i}" for i in range(1, nb_jokers + 1)]
    return cartes


def melanger(cartes: list[str], graine: int) -> list[str]:
    """Nouvelle liste mélangée de façon reproductible."""
    resultat = list(cartes)
    random.Random(graine).shuffle(resultat)
    return resultat


def _analyser(c) -> tuple[str, str] | None:
    """(valeur, enseigne) d'une carte normale, ("", "") d'un joker, None si inconnu."""
    if not isinstance(c, str):
        return None
    m = _MOTIF.match(c)
    if not m:
        return None
    if m.group(1):
        return ("", "")
    if m.group(2) in VALEURS:
        return (m.group(2), m.group(3))
    return None


def est_carte(c) -> bool:
    return _analyser(c) is not None


def _exiger(c) -> tuple[str, str]:
    analyse = _analyser(c)
    if analyse is None:
        raise ValueError(f"Carte inconnue : {c!r}")
    return analyse


def est_joker(c) -> bool:
    return _exiger(c) == ("", "")


def valeur(c) -> str:
    v, _ = _exiger(c)
    if not v:
        raise ValueError(f"Un joker n'a pas de valeur : {c!r}")
    return v


def enseigne(c) -> str:
    _, e = _exiger(c)
    if not e:
        raise ValueError(f"Un joker n'a pas d'enseigne : {c!r}")
    return e


def nature(c) -> str:
    """Identité sans le numéro de paquet : "10H-2" -> "10H" ; un joker -> "JK"."""
    _exiger(c)
    return c.split("-")[0]


def decrire(c) -> dict:
    if est_joker(c):
        return {"id": c, "joker": True}
    return {"id": c, "valeur": valeur(c), "enseigne": enseigne(c)}
