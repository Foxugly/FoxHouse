"""Rappel des règles du 8 américain pour la page « Règles » (spec jeux §1). N'importe pas Django."""

REGLES = [
    {
        "titre": "Le jeu",
        "points": [
            "De 2 à 6 joueurs ; un paquet de 52 cartes, deux à partir de 5 joueurs.",
            "Chacun reçoit 8 cartes (7 à partir de 5 joueurs). Le reste forme la pioche ; la "
            "première carte retournée commence la défausse.",
            "But : se débarrasser de toutes ses cartes.",
        ],
    },
    {
        "titre": "Un tour",
        "points": [
            "Pose une carte de la même couleur ou de la même valeur que celle du dessus de la "
            "défausse.",
            "Un 8 se pose sur n'importe quelle carte ; tu annonces ensuite la couleur à suivre.",
            "Si tu ne peux pas ou ne veux pas jouer, pioche une carte : tu peux la poser tout de "
            "suite si elle convient, sinon tu passes.",
            "Quand la pioche est vide, la défausse, sauf sa carte du dessus, est remélangée.",
        ],
    },
    {
        "titre": "Cartes spéciales (option)",
        "points": [
            "Un 2 fait piocher 2 cartes au joueur suivant, qui passe son tour, sauf s'il pose "
            "lui-même un 2 : la pénalité grossit et passe au suivant.",
            "Un valet fait passer son tour au joueur suivant.",
            "Un as change le sens du jeu ; à 2 joueurs, il vaut un valet.",
            "Avec les jokers : un joker se pose sur tout et fait piocher 4 cartes au suivant, que "
            "seul un autre joker peut contrer.",
            "Une carte spéciale posée en dernière carte termine la manche sans effet.",
        ],
    },
    {
        "titre": "Points",
        "points": [
            "La manche s'arrête dès qu'un joueur pose sa dernière carte.",
            "Les autres marquent leurs cartes restantes : 8 et joker 50, figure 10, as 1, les "
            "autres leur valeur.",
            "Après la dernière manche, le plus petit total gagne.",
        ],
    },
    {
        "titre": "Options",
        "points": [
            "Cartes spéciales (2, valet, as).",
            "Jokers (+4, sur tout).",
            "Nombre de manches, de 1 à 10.",
        ],
    },
]
