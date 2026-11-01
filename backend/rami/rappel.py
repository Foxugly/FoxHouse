"""Rappel des règles du rami 51 pour la page « Règles » (spec §6). N'importe pas Django."""

REGLES = [
    {
        "titre": "Le jeu",
        "points": [
            "De 2 à 6 joueurs, avec 2 jeux de 52 cartes et 4 jokers. Chacun reçoit 13 cartes.",
            "Le reste forme la pioche, face cachée ; une carte retournée commence la défausse.",
            "Le premier joueur change à chaque manche.",
        ],
    },
    {
        "titre": "Un tour",
        "points": [
            "Prends une carte : celle de la pioche ou celle du dessus de la défausse.",
            "Pose des combinaisons si tu le peux, puis défausse-toi d'une carte, face visible.",
        ],
    },
    {
        "titre": "Les combinaisons",
        "points": [
            "Suite : au moins 3 cartes qui se suivent, de la même couleur. Une suite ne fait pas "
            "le tour (pas de R-A-2).",
            "Brelan ou carré : 3 ou 4 cartes de même valeur, de couleurs différentes.",
            "Un joker remplace une carte manquante, un seul par combinaison. Placé au bout d'une "
            "suite, il la prolonge vers le haut si c'est possible.",
        ],
    },
    {
        "titre": "L'ouverture",
        "points": [
            "Ta première pose doit valoir au moins 51 points, en une fois : 2 à 10 leur valeur, "
            "valet, dame et roi 10, le joker la carte qu'il remplace.",
            "Pose tes combinaisons une par une : elles restent en attente, puis « Valider "
            "l'ouverture » les rend définitives dès que le total atteint 51. « Annuler » te les "
            "rend.",
            "Une fois ouvert, tu poses sans minimum, tu complètes les combinaisons de la table (y "
            "compris celles des autres) et tu peux récupérer un joker en le remplaçant par la "
            "carte qu'il représente, pour le reposer dans le même tour.",
        ],
    },
    {
        "titre": "Fin de manche et de partie",
        "points": [
            "La manche s'arrête quand un joueur n'a plus de cartes.",
            "Les autres comptent les cartes restées en main comme pénalités : l'as 11, le joker "
            "selon l'option choisie.",
            "Les pénalités s'additionnent ; après la dernière manche, le plus petit total gagne.",
        ],
    },
    {
        "titre": "Options",
        "points": [
            "Valeur de l'as : 1 en bas de suite et 11 ailleurs, toujours 1 ou toujours 11.",
            "Ouverture avec une suite sans joker obligatoire, ou non.",
            "Récupération du joker après sa propre ouverture, ou jamais.",
            "Pénalité d'un joker resté en main (20 par défaut).",
            "Finir par une défausse : il faut garder une carte pour se défausser.",
            "Carte de la défausse à poser : la carte prise doit servir dans le tour.",
            "Nombre de manches, de 1 à 10.",
        ],
    },
]
