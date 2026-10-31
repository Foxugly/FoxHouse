"""Le déroulement d'une partie : le coup d'un humain, puis ceux de la machine.

Une étape vaut `{"message": str, "vue": dict}` ; chaque vue est calculée pour
le siège de celui qui la demande. Ne dépend d'aucun jeu en particulier.
"""

from tapis.jeu import CoupRefuse

MAX_COUPS = 2000


def _est_machine(sieges, siege):
    return siege is not None and sieges[siege]["type"] == "machine"


def avancer(jeu, etat, sieges, pour: int) -> tuple[dict, list[dict]]:
    """Fait jouer la machine tant que c'est le tour d'un siège machine.

    Un coup refusé de la machine est un bug : il remonte en `RuntimeError`
    (500, vu par Sentry), jamais en `CoupRefuse` (400, la faute du joueur).
    """
    etapes = []
    while _est_machine(sieges, siege := jeu.joueur_actif(etat)):
        if len(etapes) >= MAX_COUPS:
            raise RuntimeError(f"La machine a joué {MAX_COUPS} coups sans rendre la main.")
        coup = jeu.adversaire(etat, siege)
        try:
            etat, message = jeu.appliquer(etat, siege, coup)
        except CoupRefuse as refus:
            raise RuntimeError(
                f"Coup refusé de la machine au siège {siege} ({coup!r}) : {refus}"
            ) from refus
        etapes.append({"message": message, "vue": jeu.vue(etat, pour)})
    return etat, etapes


def jouer(jeu, etat, sieges, siege: int, coup) -> tuple[dict, list[dict]]:
    """Joue le coup de l'humain au siège `siege`, puis la machine jusqu'à son tour."""
    actif = jeu.joueur_actif(etat)
    if actif is None:
        raise CoupRefuse("La partie est terminée.")
    if actif != siege:
        raise CoupRefuse("Ce n'est pas ton tour.")
    etat, message = jeu.appliquer(etat, siege, coup)
    etape = {"message": message, "vue": jeu.vue(etat, siege)}
    etat, suite = avancer(jeu, etat, sieges, pour=siege)
    return etat, [etape] + suite
