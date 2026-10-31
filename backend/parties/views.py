"""API JSON des parties, commune à tous les jeux.

Règles :
- toutes les réponses sont en JSON ; une erreur vaut `{"erreur": "…"}` en français ;
- une partie d'un autre joueur, ou inconnue, répond **404** (jamais 403 : ne
  pas confirmer qu'elle existe) ;
- tout est calculé pour le siège de celui qui demande ;
- chaque action est jouée sous verrou de ligne (`select_for_update`) et porte
  la `version` de la partie : deux requêtes simultanées ou un double clic ne
  jouent pas deux coups depuis le même état.
"""

import json
import secrets
from functools import wraps

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from parties import deroulement
from parties.joueur import jeton_du_joueur
from parties.models import Partie
from tapis import registre
from tapis.jeu import CoupRefuse
from tapis.options import OptionsInvalides, valider


def _erreur(message, statut, **extra):
    return JsonResponse({"erreur": message} | extra, status=statut)


def _methodes(*permises):
    def decorateur(vue):
        @wraps(vue)
        def enveloppe(request, *args, **kwargs):
            if request.method not in permises:
                reponse = _erreur("Méthode non permise.", 405)
                reponse["Allow"] = ", ".join(permises)
                return reponse
            return vue(request, *args, **kwargs)

        return enveloppe

    return decorateur


def echec_csrf(request, reason=""):
    """`CSRF_FAILURE_VIEW` : le refus CSRF, en JSON lui aussi."""
    return _erreur("Jeton CSRF manquant ou invalide.", 403)


class CorpsIllisible(Exception):
    pass


def _corps(request) -> dict:
    try:
        donnees = json.loads(request.body)
    except (ValueError, UnicodeDecodeError, RecursionError):  # RecursionError : trop imbriqué
        raise CorpsIllisible("Le corps de la requête n'est pas du JSON valide.") from None
    if not isinstance(donnees, dict):
        raise CorpsIllisible("Le corps de la requête doit être un objet JSON.")
    return donnees


def _est_entier(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _parties_du_joueur(request):
    """Les parties de ce joueur dont le jeu est encore inscrit ; `None` sans jeton."""
    jeton = jeton_du_joueur(request)
    if jeton is None:
        return None
    return Partie.objects.filter(joueur=jeton, jeu__in=[j.code for j in registre.tous()])


def _siege(partie, jeton) -> int:
    return next(
        i for i, s in enumerate(partie.sieges)
        if s["type"] == "humain" and s["joueur"] == jeton
    )


def _vue(jeu, etat, siege, version) -> dict:
    vue = jeu.vue(etat, siege)
    vue["version"] = version
    return vue


def _etapes(etapes, version) -> list[dict]:
    for etape in etapes:
        etape["vue"]["version"] = version
    return etapes


def _vue_de(request, partie) -> dict:
    jeu = registre.obtenir(partie.jeu)
    return _vue(jeu, partie.etat, _siege(partie, jeton_du_joueur(request)), partie.version)


@_methodes("GET")
@ensure_csrf_cookie
def jeux(request):
    return JsonResponse([j.decrire() for j in registre.tous()], safe=False)


@_methodes("POST")
def creer(request):
    try:
        corps = _corps(request)
    except CorpsIllisible as e:
        return _erreur(str(e), 400)
    try:
        jeu = registre.obtenir(corps.get("jeu"))
    except (KeyError, TypeError):
        return _erreur("Jeu inconnu.", 400)
    nb = corps.get("nb_joueurs")
    if not _est_entier(nb) or not jeu.min_joueurs <= nb <= jeu.max_joueurs:
        return _erreur(
            f"Nombre de joueurs invalide : de {jeu.min_joueurs} à {jeu.max_joueurs}.", 400
        )
    try:
        options = valider(jeu.options(), corps.get("options", {}))
    except OptionsInvalides as e:
        return _erreur(str(e), 400)

    jeton = jeton_du_joueur(request, creer=True)
    sieges = [{"type": "humain", "joueur": jeton}] + [{"type": "machine"} for _ in range(nb - 1)]
    # 128 bits : la graine ne peut pas être retrouvée par force brute depuis les cartes vues.
    etat = jeu.nouvelle_partie(options, nb, secrets.randbits(128))
    etat, etapes = deroulement.avancer(jeu, etat, sieges, pour=0)
    with transaction.atomic():
        Partie.objects.filter(joueur=jeton).delete()
        partie = Partie.objects.create(
            jeu=jeu.code, joueur=jeton, sieges=sieges, etat=etat,
            terminee=jeu.joueur_actif(etat) is None,
        )
    return JsonResponse(
        {"id": str(partie.id), "vue": _vue(jeu, etat, 0, partie.version),
         "etapes": _etapes(etapes, partie.version)},
        status=201,
    )


@_methodes("GET")
@ensure_csrf_cookie
def courante(request):
    parties = _parties_du_joueur(request)
    partie = parties.order_by("-modifie_le").first() if parties is not None else None
    if partie is None:
        return HttpResponse(status=204)
    return JsonResponse({"id": str(partie.id), "vue": _vue_de(request, partie)})


@_methodes("GET")
def detail(request, pk):
    parties = _parties_du_joueur(request)
    partie = parties.filter(pk=pk).first() if parties is not None else None
    if partie is None:
        return _erreur("Partie introuvable.", 404)
    return JsonResponse({"id": str(partie.id), "vue": _vue_de(request, partie)})


@_methodes("POST")
def action(request, pk):
    try:
        corps = _corps(request)
    except CorpsIllisible as e:
        return _erreur(str(e), 400)
    version = corps.get("version")
    if not _est_entier(version):
        return _erreur("Version manquante ou invalide.", 400)
    coup = {"action": corps.get("action"), "cartes": corps.get("cartes", []),
            "cible": corps.get("cible")}

    parties = _parties_du_joueur(request)
    if parties is None:
        return _erreur("Partie introuvable.", 404)
    with transaction.atomic():
        partie = parties.select_for_update().filter(pk=pk).first()
        if partie is None:
            return _erreur("Partie introuvable.", 404)
        jeu = registre.obtenir(partie.jeu)
        siege = _siege(partie, jeton_du_joueur(request))
        if version != partie.version:
            return _erreur(
                "La partie a changé entre-temps.", 409,
                vue=_vue(jeu, partie.etat, siege, partie.version),
            )
        try:
            etat, etapes = deroulement.jouer(jeu, partie.etat, partie.sieges, siege, coup)
        except CoupRefuse as refus:
            return _erreur(str(refus), 400, vue=_vue(jeu, partie.etat, siege, partie.version))
        partie.etat = etat
        partie.version += 1
        partie.terminee = jeu.joueur_actif(etat) is None
        partie.save()
    return JsonResponse(
        {"vue": _vue(jeu, etat, siege, partie.version), "etapes": _etapes(etapes, partie.version)}
    )
