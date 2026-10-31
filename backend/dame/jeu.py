"""La dame de pique branchée sur l'interface commune des jeux. N'importe pas Django."""

import copy

from dame import adversaire as adversaire_dame
from dame import manche
from dame import vue as vue_dame
from dame.options import OPTIONS
from tapis.cartes import est_carte
from tapis.jeu import CoupRefuse, Jeu, normaliser_coup
from tapis.options import valider


def _exiger_nombre(action: dict, cartes: list[str]) -> None:
    mini, maxi = action["cartes_min"], action["cartes_max"]
    if mini <= len(cartes) <= maxi:
        return
    if maxi == 0:
        raise CoupRefuse("Cette action ne prend pas de carte.")
    if mini == maxi:
        raise CoupRefuse(f"Choisis {mini} carte{'s' if mini > 1 else ''}.")
    raise CoupRefuse(f"Choisis de {mini} à {maxi} cartes.")


def _exiger_cartes_en_main(etat: dict, j: int, cartes: list[str]) -> None:
    for c in cartes:
        if not est_carte(c):
            raise CoupRefuse("Carte inconnue.")
        if c not in etat["mains"][j]:
            raise CoupRefuse("Cette carte n'est pas dans ta main.")


class Dame(Jeu):
    code = "dame"
    nom = "Dame de pique"
    min_joueurs = 3
    max_joueurs = 6

    def options(self):
        return OPTIONS

    def nouvelle_partie(self, options: dict, nb_joueurs: int, graine: int) -> dict:
        if not self.min_joueurs <= nb_joueurs <= self.max_joueurs:
            raise ValueError(f"Nombre de joueurs invalide : {nb_joueurs}")
        return manche.nouvel_etat(valider(OPTIONS, options), nb_joueurs, graine)

    def joueur_actif(self, etat) -> int | None:
        return None if etat["phase"] == "terminee" else etat["actif"]

    def actions_permises(self, etat, j: int) -> list[dict]:
        return vue_dame.actions_permises(etat, j)

    def appliquer(self, etat, joueur: int, coup) -> tuple[dict, str | None]:
        """Le don de l'échange est privé (spec jeux §2.1) : il rend None."""
        etat, message, prive = self._jouer(etat, joueur, coup)
        return etat, None if prive else message

    def message_prive(self, etat, joueur: int, coup) -> str:
        """Rejoue le don pour retrouver le message de son auteur."""
        return self._jouer(etat, joueur, coup)[1]

    def _jouer(self, etat, joueur: int, coup) -> tuple[dict, str, bool]:
        """Nouvel état, message de l'auteur et « coup privé » ; ne modifie pas `etat`."""
        coup = normaliser_coup(coup)
        etat = copy.deepcopy(etat)
        action = next(
            (a for a in self.actions_permises(etat, joueur) if a["id"] == coup["action"]), None
        )
        if action is None:
            raise CoupRefuse("Action impossible maintenant.")
        cartes = coup["cartes"]
        _exiger_nombre(action, cartes)
        _exiger_cartes_en_main(etat, joueur, cartes)
        match action["id"]:
            case "donner":
                return etat, manche.donner(etat, joueur, cartes), True
            case "jouer":
                return etat, manche.jouer(etat, joueur, cartes[0]), False
            case "manche_suivante":
                return etat, manche.manche_suivante(etat), False
        raise CoupRefuse("Action impossible maintenant.")

    def vue(self, etat, joueur: int) -> dict:
        return vue_dame.vue(etat, joueur)

    def adversaire(self, etat, joueur: int) -> dict:
        return adversaire_dame.choisir(etat, joueur)
