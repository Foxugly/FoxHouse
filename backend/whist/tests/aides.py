"""États construits pour les tests du whist."""

from tapis.options import valider
from whist.jeu import Whist
from whist.manche import NB_PLIS
from whist.options import OPTIONS


def partie(graine=7, **options):
    return Whist().nouvelle_partie(valider(OPTIONS, options), 4, graine)


def coup(action, cartes=()):
    return {"action": action, "cartes": list(cartes)}


def appliquer(e, j, action, cartes=()):
    return Whist().appliquer(e, j, coup(action, cartes))


def etat_encheres(donneur=3, graine=7, **options):
    """Une donne en enchères, sans trou, du donneur demandé."""
    options.setdefault("trou", False)
    e = partie(graine=graine, **options)
    while e["phase"] != "encheres":  # une graine qui ne donne pas d'enchères : on change
        graine += 1
        e = partie(graine=graine, **options)
    e["donneur"] = donneur
    e["actif"] = (donneur + 1) % 4
    return e


def etat_plis(mains, code="seul", preneurs=(0,), atout="H", actif=0, retournee=None,
              donneur=3, **options):
    """Phase des plis avec exactement ces mains (de même longueur) ; les plis déjà joués sont
    comptés pour qu'il en reste autant que de cartes en main."""
    e = partie(trou=False, **options)
    e["mains"] = [list(m) for m in mains]
    e["donneur"] = donneur
    e["retournee"] = retournee or "2C-1"
    e["contrat"] = {"code": code, "preneurs": sorted(preneurs)}
    e["atout"] = atout
    e["phase"] = "plis"
    e["actif"] = actif
    e["plis_joues"] = NB_PLIS - max(len(m) for m in mains)
    e["plis"] = [0] * 4
    return e


def jouer(e, j, carte):
    return appliquer(e, j, "jouer", [carte])


def jouer_le_pli(e, cartes):
    """Joue `cartes`, une par siège dans l'ordre du jeu à partir du joueur actif."""
    message = None
    for carte in cartes:
        e, message = jouer(e, e["actif"], carte)
    return e, message
