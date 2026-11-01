"""Le whist à la couleur branché sur l'interface commune des jeux. N'importe pas Django."""

import copy

from tapis.cartes import est_carte
from tapis.jeu import CoupRefuse, Jeu, normaliser_coup
from tapis.options import valider
from whist import adversaire as adversaire_whist
from whist import manche
from whist import vue as vue_whist
from whist.options import OPTIONS
from whist.rappel import REGLES


def _exiger_nombre(action: dict, cartes: list[str]) -> None:
    mini, maxi = action["cartes_min"], action["cartes_max"]
    if mini <= len(cartes) <= maxi:
        return
    if maxi == 0:
        raise CoupRefuse("Cette action ne prend pas de carte.")
    raise CoupRefuse(f"Choisis {mini} carte{'s' if mini > 1 else ''}.")


def _exiger_cartes_en_main(etat: dict, j: int, cartes: list[str]) -> None:
    for c in cartes:
        if not est_carte(c):
            raise CoupRefuse("Carte inconnue.")
        if c not in etat["mains"][j]:
            raise CoupRefuse("Cette carte n'est pas dans ta main.")


class Whist(Jeu):
    code = "whist"
    nom = "Whist à la couleur"
    min_joueurs = 4
    max_joueurs = 4

    def options(self):
        return OPTIONS

    def regles(self):
        return REGLES

    def nouvelle_partie(self, options: dict, nb_joueurs: int, graine: int) -> dict:
        if not self.min_joueurs <= nb_joueurs <= self.max_joueurs:
            raise ValueError(f"Nombre de joueurs invalide : {nb_joueurs}")
        return manche.nouvel_etat(valider(OPTIONS, options), graine)

    def joueur_actif(self, etat) -> int | None:
        return None if etat["phase"] == "terminee" else etat["actif"]

    def actions_permises(self, etat, j: int) -> list[dict]:
        return vue_whist.actions_permises(etat, j)

    def appliquer(self, etat, joueur: int, coup) -> tuple[dict, str]:
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
        ident = action["id"]
        match etat["phase"]:
            case "encheres":
                return etat, manche.annoncer(etat, joueur, ident)
            case "demande_seule":
                return etat, manche.demande_seule(etat, joueur, ident)
            case "atout":
                return etat, manche.choisir_atout(etat, joueur, ident.removeprefix("atout_"))
            case "plis":
                return etat, manche.jouer(etat, joueur, cartes[0])
        return etat, manche.donne_suivante(etat)

    def vue(self, etat, joueur: int) -> dict:
        return vue_whist.vue(etat, joueur)

    def adversaire(self, etat, joueur: int) -> dict:
        return adversaire_whist.choisir(etat, joueur)
