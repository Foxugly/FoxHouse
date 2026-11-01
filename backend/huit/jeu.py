"""Le 8 américain branché sur l'interface commune des jeux (spec §1). N'importe pas Django."""

import copy

from huit import adversaire as adversaire_huit
from huit import manche
from huit import vue as vue_huit
from huit.options import OPTIONS
from huit.rappel import REGLES
from tapis.cartes import est_carte
from tapis.jeu import CoupRefuse, Jeu, normaliser_coup
from tapis.options import valider


def _refus_hors_actions(etat: dict, joueur: int, action: str) -> CoupRefuse:
    """Pourquoi une action n'est pas proposée, quand c'est le tour du joueur."""
    if etat["actif"] == joueur and etat["phase"] == "couleur":
        return CoupRefuse("Annonce d'abord une couleur.")
    if etat["actif"] == joueur and etat["phase"] == "jouer":
        if action == "piocher":
            return CoupRefuse("Tu as déjà pioché.")
        if action == "passer":
            return CoupRefuse("Pioche d'abord une carte.")
    return CoupRefuse("Action impossible maintenant.")


def _exiger_cartes(action: dict, etat: dict, joueur: int, cartes: list[str]) -> None:
    if action["cartes_max"] == 0:
        if cartes:
            raise CoupRefuse("Cette action ne prend pas de carte.")
        return
    if len(cartes) != 1:
        raise CoupRefuse("Choisis 1 carte.")
    if not est_carte(cartes[0]):
        raise CoupRefuse("Carte inconnue.")
    if cartes[0] not in etat["mains"][joueur]:
        raise CoupRefuse("Cette carte n'est pas dans ta main.")


class Huit(Jeu):
    code = "huit"
    nom = "8 américain"
    min_joueurs = 2
    max_joueurs = 6

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

    def actions_permises(self, etat, joueur: int) -> list[dict]:
        return vue_huit.actions_permises(etat, joueur)

    def appliquer(self, etat, joueur: int, coup) -> tuple[dict, str]:
        """Aucun coup n'est privé au 8 américain : le message est toujours public."""
        coup = normaliser_coup(coup)
        etat = copy.deepcopy(etat)
        action = next(
            (a for a in self.actions_permises(etat, joueur) if a["id"] == coup["action"]), None
        )
        if action is None:
            raise _refus_hors_actions(etat, joueur, coup["action"])
        cartes = coup["cartes"]
        _exiger_cartes(action, etat, joueur, cartes)
        match action["id"]:
            case "jouer":
                message = manche.jouer(etat, joueur, cartes[0])
            case "piocher":
                message = manche.piocher(etat, joueur)
            case "passer":
                message = manche.passer(etat, joueur)
            case "manche_suivante":
                manche.manche_suivante(etat)
                message = f"La manche {etat['manche']} commence."
            case annonce:  # couleur_S, couleur_H, couleur_D, couleur_C
                message = manche.annoncer(etat, joueur, annonce.removeprefix("couleur_"))
        return etat, message

    def vue(self, etat, joueur: int) -> dict:
        return vue_huit.vue(etat, joueur)

    def adversaire(self, etat, joueur: int) -> dict:
        return adversaire_huit.choisir(etat, joueur)
