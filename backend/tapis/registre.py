"""Registre des jeux disponibles. N'importe pas Django."""

from tapis.jeu import Jeu

_JEUX: dict[str, Jeu] = {}


def inscrire(jeu: Jeu) -> None:
    if jeu.code in _JEUX:
        raise ValueError(f"Le jeu « {jeu.code} » est déjà inscrit.")
    _JEUX[jeu.code] = jeu


def obtenir(code: str) -> Jeu:
    return _JEUX[code]


def tous() -> list[Jeu]:
    return sorted(_JEUX.values(), key=lambda j: j.nom)


def retirer(code: str) -> None:
    """Pour les tests."""
    _JEUX.pop(code, None)
