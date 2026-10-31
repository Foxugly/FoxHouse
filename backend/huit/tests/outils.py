"""Outils communs aux tests du 8 américain."""

from collections import Counter

from huit.jeu import Huit
from huit.manche import nb_paquets
from huit.options import OPTIONS
from tapis.cartes import est_joker, paquet
from tapis.options import valider


def partie(nb=2, graine=7, **options):
    return Huit().nouvelle_partie(valider(OPTIONS, options), nb, graine)


def table(etat, mains: dict, dessus, actif=0):
    """Impose des mains et la défausse ; c'est au joueur `actif` de jouer.

    Chaque carte n'existe qu'une fois : les cartes imposées sont ôtées d'ailleurs, et les
    cartes qu'elles remplacent retournent sous la pioche, pour que le paquet reste entier.
    """
    defausse = [dessus] if isinstance(dessus, str) else list(dessus)
    imposees = set(defausse).union(*mains.values())
    rendues = []
    for j, main in mains.items():
        rendues += etat["mains"][j]
        etat["mains"][j] = []
    rendues += etat["defausse"]
    for pile in [etat["pioche"], *etat["mains"]]:
        pile[:] = [c for c in pile if c not in imposees]
    etat["pioche"][:0] = [c for c in rendues if c not in imposees]
    for j, main in mains.items():
        etat["mains"][j] = list(main)
    etat["defausse"] = defausse
    etat["reference"] = next(c for c in reversed(defausse) if not est_joker(c))
    etat["actif"] = actif
    return etat


def toutes_les_cartes(etat) -> Counter:
    return Counter(etat["pioche"] + etat["defausse"] + [c for m in etat["mains"] for c in m])


def paquet_complet(etat) -> Counter:
    jeux = nb_paquets(etat["nb"])
    return Counter(paquet(jeux, 2 * jeux if etat["options"]["jokers"] else 0))


def ids(actions):
    return [a["id"] for a in actions]
