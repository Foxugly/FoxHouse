"""Le rami 51 branché sur l'interface commune des jeux. N'importe pas Django."""

import copy

from rami import adversaire as adversaire_rami
from rami import manche, poses
from rami import vue as vue_rami
from rami.manche import _verbe, etiquette_carte
from rami.options import OPTIONS
from rami.rappel import REGLES
from tapis.cartes import est_carte
from tapis.jeu import CoupRefuse, Jeu, normaliser_coup
from tapis.options import valider


def _exiger_nombre(action: dict, cartes: list[str]) -> None:
    mini, maxi = action["cartes_min"], action["cartes_max"]
    if mini <= len(cartes) <= maxi:
        return
    if maxi == 0:
        raise CoupRefuse("Cette action ne prend pas de carte.")
    if mini == maxi == 1:
        raise CoupRefuse("Choisis 1 carte.")
    raise CoupRefuse(f"Choisis de {mini} à {maxi} cartes.")


def _exiger_cartes_en_main(etat: dict, j: int, cartes: list[str]) -> None:
    for c in cartes:
        if not est_carte(c):
            raise CoupRefuse("Carte inconnue.")
        if c not in etat["mains"][j]:
            raise CoupRefuse("Cette carte n'est pas dans ta main.")


def _defausser(etat: dict, j: int, carte: str) -> str:
    """Se défausser sans avoir validé l'ouverture rend d'abord le brouillon à la main.

    Cette annulation ne fait pas de message à part : seul le message public de la
    défausse est rendu, et le brouillon reste privé.
    """
    if etat["brouillon"]:
        poses.annuler(etat, j)
    main = etat["mains"][j]
    if etat["joker_recupere"] in main:
        raise CoupRefuse("Utilise d'abord le joker récupéré.")
    if etat["options"]["defausse_a_poser"] and etat["prise"] in main:
        raise CoupRefuse("Pose d'abord la carte prise à la défausse.")
    return manche.defausser(etat, j, carte)


def _piocher(etat: dict, j: int) -> str:
    etat.pop("defausse_rendue", None)  # le tour reprend normalement
    return manche.piocher(etat, j)


def _rendre_defausse(etat: dict, j: int) -> str:
    """Avec « carte de la défausse à poser » : remet la carte prise et repasse à la pioche.

    Dans ce même tour, la défausse ne peut plus être reprise. Refusé tant que le joker
    récupéré est en main : il passerait au tour suivant, où la table pourrait ne plus
    l'accepter.
    """
    poses.exiger_joker_rejoue(etat, j, [])
    if etat["brouillon"]:
        poses.annuler(etat, j)
    prise = etat["prise"]
    etat["mains"][j].remove(prise)
    etat["defausse"].append(prise)
    etat["prise"] = None
    etat["phase"] = "piocher"
    etat["defausse_rendue"] = True
    return f"{_verbe(j, 'reposes', 'repose')} le {etiquette_carte(prise)} sur la défausse."


def _manche_suivante(etat: dict) -> str:
    manche.manche_suivante(etat)
    return f"La manche {etat['manche']} commence."


class Rami(Jeu):
    code = "rami"
    nom = "Rami 51"
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

    def actions_permises(self, etat, j: int) -> list[dict]:
        return vue_rami.actions_permises(etat, j)

    def appliquer(self, etat, joueur: int, coup) -> tuple[dict, str | None]:
        """Le brouillon est privé (spec §6.4) : le mettre en attente ou l'annuler rend None."""
        etat, message, prive = self._jouer(etat, joueur, coup)
        return etat, None if prive else message

    def message_prive(self, etat, joueur: int, coup) -> str:
        """Rejoue le coup privé pour retrouver le message de son auteur."""
        return self._jouer(etat, joueur, coup)[1]

    def _jouer(self, etat, joueur: int, coup) -> tuple[dict, str, bool]:
        """Nouvel état, message de l'auteur et « coup privé » ; ne modifie pas `etat`."""
        coup = normaliser_coup(coup)
        etat = copy.deepcopy(etat)
        action = next(
            (a for a in self.actions_permises(etat, joueur) if a["id"] == coup["action"]), None
        )
        if action is None:
            # Ces deux actions ne sont plus proposées : on dit pourquoi plutôt que « impossible ».
            if coup["action"] == "defausser" and etat["joker_recupere"] in etat["mains"][joueur]:
                raise CoupRefuse("Utilise d'abord le joker récupéré.")
            if coup["action"] == "rendre_defausse" and etat["joker_recupere"] in etat["mains"][joueur]:
                raise CoupRefuse("Rejoue d'abord le joker récupéré.")
            raise CoupRefuse("Action impossible maintenant.")
        cartes = coup["cartes"]
        _exiger_nombre(action, cartes)
        _exiger_cartes_en_main(etat, joueur, cartes)
        cible = coup["cible"]
        if action["cible"] == "groupe" and not any(g["id"] == cible for g in etat["table"]):
            raise CoupRefuse("Combinaison introuvable.")

        prive = False
        match action["id"]:
            case "piocher":
                message = _piocher(etat, joueur)
            case "prendre_defausse":
                message = manche.prendre_defausse(etat, joueur)
            case "poser":
                prive = not etat["ouvert"][joueur]  # avant l'ouverture : dans le brouillon
                message = poses.poser(etat, joueur, cartes)
            case "valider_ouverture":
                message = poses.valider_ouverture(etat, joueur)
            case "annuler":
                prive = True
                message = poses.annuler(etat, joueur)
            case "ajouter":
                message = poses.ajouter_a(etat, joueur, cartes, cible)
            case "recuperer_joker":
                message = poses.recuperer(etat, joueur, cartes[0], cible)
            case "defausser":
                message = _defausser(etat, joueur, cartes[0])
            case "rendre_defausse":
                message = _rendre_defausse(etat, joueur)
            case "manche_suivante":
                message = _manche_suivante(etat)
            case _:
                raise CoupRefuse("Action impossible maintenant.")
        return etat, message, prive

    def vue(self, etat, joueur: int) -> dict:
        return vue_rami.vue(etat, joueur)

    def adversaire(self, etat, joueur: int) -> dict:
        return adversaire_rami.choisir(etat, joueur)
