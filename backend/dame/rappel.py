"""Rappel des règles de la dame de pique pour la page « Règles » (spec jeux §2). N'importe pas Django."""

REGLES = [
    {
        "titre": "Le jeu",
        "points": [
            "De 3 à 6 joueurs, 4 étant le jeu normal. Toutes les cartes sont distribuées ; à 3, 5 "
            "ou 6 joueurs, quelques petits carreaux et piques sont retirés pour une donne égale.",
            "L'as est la plus forte carte, puis roi, dame, valet, 10… 2. Pas d'atout.",
            "But : ramasser le moins de points possible.",
        ],
    },
    {
        "titre": "L'échange",
        "points": [
            "Avant chaque manche, chacun choisit 3 cartes et les donne à un voisin.",
            "Le sens tourne : à gauche, à droite, en face, puis aucun échange (sans « en face » à "
            "3, 5 ou 6 joueurs).",
        ],
    },
    {
        "titre": "Les plis",
        "points": [
            "Le détenteur du 2 de trèfle entame le premier pli avec cette carte.",
            "Il faut fournir la couleur demandée ; sinon, joue ce que tu veux. Au premier pli, ni "
            "cœur ni dame de pique, sauf si tu n'as rien d'autre.",
            "On n'entame pas à cœur tant qu'aucun cœur n'a été joué, sauf avec une main de cœurs "
            "seulement.",
            "La plus haute carte de la couleur demandée prend le pli ; son gagnant entame le "
            "suivant.",
            "Un clic sur une carte la joue.",
        ],
    },
    {
        "titre": "Points",
        "points": [
            "Chaque cœur ramassé vaut 1 point, la dame de pique 13.",
            "Grand chelem : qui ramasse tous les cœurs et la dame marque 0, et chacun des autres "
            "26.",
            "La partie s'arrête à la fin de la manche où quelqu'un atteint le score de fin ; le "
            "plus petit total gagne.",
        ],
    },
    {
        "titre": "Options",
        "points": [
            "Échange de 3 cartes.",
            "Score de fin de partie, de 20 à 200 (100 par défaut).",
            "Valet de carreau à −10 pour qui le ramasse.",
        ],
    },
]
