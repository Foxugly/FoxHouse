"""Jeu factice des tests : la preuve que `parties` ne dépend d'aucun jeu (spec §7).

Deux joueurs, une pile de 3 cartes chacun. L'unique action, « retourner »,
pose la carte du dessus de sa pile dans sa main, visible de tous. La partie
finit après 6 coups. Il n'utilise rien du rami.
"""

import copy

from tapis import registre
from tapis.cartes import CACHEE, decrire
from tapis.jeu import CoupRefuse, Jeu, normaliser_coup
from tapis.vue import SCHEMA

PILES = [["AS-1", "2S-1", "3S-1"], ["AH-1", "2H-1", "3H-1"]]
COUPS_PAR_PARTIE = 6
ACTION = {"id": "retourner", "libelle": "Retourner", "cartes_min": 0, "cartes_max": 0,
          "cible": None}


class Retourner(Jeu):
    code = "factice"
    nom = "Factice"
    min_joueurs = 2
    max_joueurs = 2

    def options(self):
        return []

    def nouvelle_partie(self, options, nb_joueurs, graine):
        return {"piles": copy.deepcopy(PILES), "mains": [[], []], "actif": 0, "coups": 0}

    def joueur_actif(self, etat):
        return None if etat["coups"] >= COUPS_PAR_PARTIE else etat["actif"]

    def appliquer(self, etat, joueur, coup):
        coup = normaliser_coup(coup)
        if joueur != self.joueur_actif(etat) or coup["action"] != "retourner":
            raise CoupRefuse("Action impossible maintenant.")
        etat = copy.deepcopy(etat)
        carte = etat["piles"][joueur].pop()
        etat["mains"][joueur].append(carte)
        etat["actif"] = 1 - joueur
        etat["coups"] += 1
        return etat, f"Le joueur {joueur} retourne une carte."

    def vue(self, etat, joueur):
        actif = self.joueur_actif(etat)
        sieges = [joueur, 1 - joueur]
        zones = []
        for s in sieges:
            zones.append({"id": f"pile-{s}", "type": "pile", "siege": s, "libelle": "Pile",
                          "cartes": [dict(CACHEE) for _ in etat["piles"][s]], "nombre": None,
                          "groupes": []})
            zones.append({"id": f"main-{s}", "type": "main", "siege": s, "libelle": "Main",
                          "cartes": [decrire(c) for c in etat["mains"][s]], "nombre": None,
                          "groupes": []})
        return {
            "schema": SCHEMA,
            "jeu": self.code,
            "version": 0,
            "terminee": actif is None,
            "sieges": [{"id": s, "nom": f"Joueur {s}", "actif": s == actif, "compteurs": []}
                       for s in sieges],
            "zones": zones,
            "menu": [],
            "actions": [dict(ACTION)] if actif == joueur else [],
            "resultat": None,
        }

    def adversaire(self, etat, joueur):
        return {"action": "retourner"}


class AvecFactice:
    """Mixin de test : inscrit le jeu factice pour la durée de la classe."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        registre.inscrire(Retourner())

    @classmethod
    def tearDownClass(cls):
        registre.retirer(Retourner.code)
        super().tearDownClass()
