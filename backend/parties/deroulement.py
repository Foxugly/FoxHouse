"""Le déroulement d'une partie : le coup d'un humain, puis ceux de la machine.

Une étape vaut `{"message": str, "vue": dict}` ; chaque vue est calculée pour
le siège de celui qui la demande. Un coup privé (le jeu rend un message None,
voir `tapis.jeu.Jeu.appliquer`) ne fait une étape que pour son auteur : ni son
message ni même son existence n'atteignent les autres joueurs. Ne dépend
d'aucun jeu en particulier.
"""

from tapis.jeu import CoupRefuse

MAX_COUPS = 2000


def _est_machine(sieges, siege):
    return siege is not None and sieges[siege]["type"] == "machine"


def avancer(jeu, etat, sieges, pour: int) -> tuple[dict, list[dict]]:
    """Fait jouer la machine tant que c'est le tour d'un siège machine.

    Les coups privés de la machine ne font pas d'étape. Un coup refusé de la
    machine est un bug : il remonte en `RuntimeError` (500, vu par Sentry),
    jamais en `CoupRefuse` (400, la faute du joueur).
    """
    etapes = []
    coups = 0
    while _est_machine(sieges, siege := jeu.joueur_actif(etat)):
        if coups >= MAX_COUPS:
            raise RuntimeError(f"La machine a joué {MAX_COUPS} coups sans rendre la main.")
        coups += 1
        coup = jeu.adversaire(etat, siege)
        try:
            etat, message = jeu.appliquer(etat, siege, coup)
        except CoupRefuse as refus:
            raise RuntimeError(
                f"Coup refusé de la machine au siège {siege} ({coup!r}) : {refus}"
            ) from refus
        if message is not None:
            etapes.append({"message": message, "vue": jeu.vue(etat, pour)})
    return etat, etapes


def jouer(jeu, etat, sieges, siege: int, coup) -> tuple[dict, list[dict]]:
    """Joue le coup de l'humain au siège `siege`, puis la machine jusqu'à son tour.

    Le coup de l'humain fait toujours une étape, privé ou non : c'est lui qui l'a joué.
    """
    actif = jeu.joueur_actif(etat)
    if actif is None:
        raise CoupRefuse("La partie est terminée.")
    if actif != siege:
        raise CoupRefuse("Ce n'est pas ton tour.")
    avant = etat
    etat, message = jeu.appliquer(etat, siege, coup)
    if message is None:
        message = jeu.message_prive(avant, siege, coup)
    etape = {"message": message, "vue": jeu.vue(etat, siege)}
    etat, suite = avancer(jeu, etat, sieges, pour=siege)
    return etat, [etape] + suite
