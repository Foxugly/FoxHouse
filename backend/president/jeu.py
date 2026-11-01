"""Le président branché sur l'interface commune des jeux. N'importe pas Django."""

import copy

from president import adversaire as adversaire_president
from president import manche
from president import vue as vue_president
from president.options import OPTIONS
from president.rappel import REGLES
from tapis.jeu import CoupRefuse, Jeu, normaliser_coup
from tapis.options import valider


def _exiger_nombre(action: dict, cartes: list[str]) -> None:
    mini, maxi = action["cartes_min"], action["cartes_max"]
    if mini <= len(cartes) <= maxi:
        return
    if maxi == 0:
        raise CoupRefuse("Cette action ne prend pas de carte.")
    if mini == maxi:
        raise CoupRefuse("Choisis 1 carte." if mini == 1 else f"Choisis {mini} cartes.")
    raise CoupRefuse(f"Choisis de {mini} à {maxi} cartes.")


class President(Jeu):
    code = "president"
    nom = "Président"
    min_joueurs = 3
    max_joueurs = 7

    def options(self):
        return OPTIONS

    def regles(self):
        return REGLES

    def nouvelle_partie(self, options: dict, nb_joueurs: int, graine: int) -> dict:
        if not self.min_joueurs <= nb_joueurs <= self.max_joueurs:
            raise ValueError(f"Nombre de joueurs invalide : {nb_joueurs}")
        return manche.nouvel_etat(valider(OPTIONS, options), nb_joueurs, graine)

    def joueur_actif(self, etat) -> int | None:
        return None if etat["phase"] == "terminee" else etat["actif"]

    def actions_permises(self, etat, j: int) -> list[dict]:
        return vue_president.actions_permises(etat, j)

    def appliquer(self, etat, joueur: int, coup) -> tuple[dict, str | None]:
        """Le retour du Président ou du Vice-président est privé : il rend None."""
        etat, message, prive = self._jouer(etat, joueur, coup)
        return etat, None if prive else message

    def message_prive(self, etat, joueur: int, coup) -> str:
        """Rejoue le coup privé pour retrouver le message de son auteur."""
        return self._jouer(etat, joueur, coup)[1]

    def _jouer(self, etat, joueur: int, coup) -> tuple[dict, str, bool]:
        """Nouvel état, message de l'auteur et « coup privé » ; ne modifie pas `etat`."""
        coup = normaliser_coup(coup)
        if self.joueur_actif(etat) is None:
            raise CoupRefuse("La partie est terminée.")
        if joueur != etat["actif"]:
            raise CoupRefuse("Ce n'est pas ton tour.")
        etat = copy.deepcopy(etat)
        action = next(
            (a for a in self.actions_permises(etat, joueur) if a["id"] == coup["action"]), None
        )
        if action is None:
            if coup["action"] == "passer" and etat["phase"] == "pli":
                raise CoupRefuse("Tu entames : tu ne peux pas passer.")
            raise CoupRefuse("Action impossible maintenant.")
        cartes = coup["cartes"]
        _exiger_nombre(action, cartes)

        match action["id"]:
            case "jouer":
                return etat, manche.jouer(etat, joueur, cartes), False
            case "passer":
                return etat, manche.passer(etat, joueur), False
            case "rendre":
                return etat, manche.rendre(etat, joueur, cartes), True
            case "manche_suivante":
                return etat, manche.manche_suivante(etat), False
        raise CoupRefuse("Action impossible maintenant.")

    def vue(self, etat, joueur: int) -> dict:
        return vue_president.vue(etat, joueur)

    def adversaire(self, etat, joueur: int) -> dict:
        return adversaire_president.choisir(etat, joueur)
