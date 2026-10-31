"""Interface commune des jeux. N'importe pas Django."""

from abc import ABC, abstractmethod

from tapis.options import Option


class CoupRefuse(Exception):
    """Coup refusé ; le message, en français, est destiné au joueur."""


def normaliser_coup(donnees) -> dict:
    """Rend {"action", "cartes", "cible"} ou lève CoupRefuse si la forme est mauvaise."""
    if not isinstance(donnees, dict):
        raise CoupRefuse("Coup mal formé.")
    action = donnees.get("action")
    if not isinstance(action, str) or not action:
        raise CoupRefuse("Action manquante.")
    cartes = donnees.get("cartes", [])
    if not isinstance(cartes, list) or not all(isinstance(c, str) for c in cartes):
        raise CoupRefuse("La liste de cartes est mal formée.")
    cible = donnees.get("cible")
    if cible is not None and not isinstance(cible, str):
        raise CoupRefuse("La cible est mal formée.")
    return {"action": action, "cartes": list(cartes), "cible": cible}


class Jeu(ABC):
    code: str
    nom: str
    min_joueurs: int
    max_joueurs: int

    @abstractmethod
    def options(self) -> list[Option]: ...

    @abstractmethod
    def nouvelle_partie(self, options: dict, nb_joueurs: int, graine: int) -> dict: ...

    @abstractmethod
    def joueur_actif(self, etat) -> int | None:
        """None = partie terminée."""

    @abstractmethod
    def appliquer(self, etat, joueur: int, coup: dict) -> tuple[dict, str | None]:
        """Nouvel état et message public, ou CoupRefuse. Ne modifie pas `etat`.

        Le message vaut None pour un coup privé, que les autres joueurs ne doivent pas voir
        (un brouillon de tour, spec §6.4) : il n'est alors rejoué comme étape que pour son
        auteur, avec `message_prive`.
        """

    def message_prive(self, etat, joueur: int, coup: dict) -> str:
        """Message de l'étape montrée au seul auteur d'un coup privé.

        `etat` est l'état d'avant le coup, que `appliquer` a accepté en rendant None.
        """
        return "Coup joué."

    @abstractmethod
    def vue(self, etat, joueur: int) -> dict: ...

    @abstractmethod
    def adversaire(self, etat, joueur: int) -> dict:
        """Coup choisi par l'ordinateur."""

    def decrire(self) -> dict:
        return {
            "code": self.code,
            "nom": self.nom,
            "min_joueurs": self.min_joueurs,
            "max_joueurs": self.max_joueurs,
            "options": [o.decrire() for o in self.options()],
        }
