"""Rappel des règles du président pour la page « Règles » (spec jeux §3). N'importe pas Django."""

REGLES = [
    {
        "titre": "Le jeu",
        "points": [
            "De 3 à 7 joueurs, un paquet de 52 cartes entièrement distribué.",
            "Ordre des valeurs : 3, 4… 10, valet, dame, roi, as, et le 2, le plus fort. Les "
            "couleurs ne comptent pas.",
            "But : vider sa main le premier.",
        ],
    },
    {
        "titre": "Les plis",
        "points": [
            "À la première manche, le détenteur du 3 de trèfle entame ; ensuite, c'est le Pauvre.",
            "Celui qui entame pose 1 à 4 cartes de même valeur. Les suivants posent autant de "
            "cartes, de même valeur et plus fortes, ou passent ; on peut rejouer au tour suivant "
            "du même pli.",
            "Le pli se ferme quand tous les autres ont passé ; celui qui a posé en dernier entame "
            "le suivant.",
        ],
    },
    {
        "titre": "Rangs et points",
        "points": [
            "Le premier qui vide sa main est Président, le deuxième Vice-président ; "
            "l'avant-dernier est Vice-pauvre, le dernier Pauvre, les autres Neutres. À 3 joueurs : "
            "Président, Neutre, Pauvre.",
            "Le Président marque le nombre de joueurs moins 1, puis un de moins à chaque rang ; le "
            "Pauvre marque 0.",
            "Après la dernière manche, le plus grand total gagne.",
        ],
    },
    {
        "titre": "Les échanges",
        "points": [
            "À partir de la deuxième manche, le Pauvre donne d'office ses 2 meilleures cartes au "
            "Président, qui lui rend 2 cartes de son choix.",
            "À 4 joueurs et plus, le Vice-pauvre et le Vice-président échangent de même 1 carte.",
        ],
    },
    {
        "titre": "Options",
        "points": [
            "Le 2 ferme le pli : son auteur entame aussitôt le suivant.",
            "Échanges entre manches.",
            "Nombre de manches, de 1 à 10.",
        ],
    },
]
