"""Rappel des règles du whist à la couleur pour la page « Règles » (spec whist). N'importe pas Django."""

REGLES = [
    {
        "titre": "Le jeu",
        "points": [
            "4 joueurs, un paquet de 52 cartes, 13 cartes chacun. Les partenaires changent à "
            "chaque donne.",
            "La dernière carte, celle du donneur, est retournée : sa couleur est l'atout, sauf "
            "contrat qui en décide autrement. Le donneur tourne à chaque donne.",
            "L'as est la plus forte carte, puis roi, dame, valet, 10… 2.",
        ],
    },
    {
        "titre": "Les enchères",
        "points": [
            "En commençant à gauche du donneur, chacun passe ou annonce un contrat plus haut que "
            "le dernier. Qui a passé ne revient plus.",
            "Demander puis accepter : les deux joueurs font équipe en emballage et doivent faire "
            "8 plis ensemble.",
            "Une demande que personne n'accepte : son auteur joue seul (5 plis) ou passe.",
            "Si tout le monde passe, la donne est rejouée, sans points.",
        ],
    },
    {
        "titre": "Les contrats, du plus bas au plus haut",
        "points": [
            "Emballage (à deux) : 8 plis, à l'atout retourné.",
            "Seul : 5 plis, à l'atout retourné.",
            "Abondance 9 : 9 plis, atout choisi par le preneur.",
            "Misère : ne faire aucun pli, sans atout.",
            "Abondance 10, puis abondance 11 : 10 ou 11 plis, atout choisi.",
            "Misère ouverte : aucun pli, main étalée après le premier pli.",
            "Abondance 12 : 12 plis, atout choisi.",
            "Solo : les 13 plis, à l'atout retourné ; solo slim : les 13 plis, atout choisi.",
            "Trou (option) : qui a trois as joue d'office avec le détenteur du quatrième, pour "
            "8 plis à deux ; avec les quatre as, avec le détenteur du roi de cœur.",
        ],
    },
    {
        "titre": "Les plis",
        "points": [
            "Le joueur à gauche du donneur entame. Il faut fournir la couleur demandée ; sinon, "
            "on joue n'importe quelle carte, sans obligation de couper.",
            "Le plus haut atout prend le pli, sinon la plus haute carte de la couleur demandée ; "
            "le gagnant entame.",
            "Une misère s'arrête dès que le preneur prend un pli.",
            "Un clic sur une carte la joue.",
        ],
    },
    {
        "titre": "Points",
        "points": [
            "Chaque donne est à somme nulle. Seul contre trois, le preneur gagne ou perd trois "
            "fois la valeur, chaque adversaire une fois. À deux contre deux, chacun gagne ou perd "
            "la valeur.",
            "Emballage et trou : 2, plus 1 par pli au-delà de 8 (ou par pli manquant) ; les 13 "
            "plis valent 14.",
            "Seul : 3, plus 1 par pli au-delà de 5 (ou par pli manquant).",
            "Abondance 9, 10, 11, 12 : 5, 7, 10, 15.",
            "Misère 7, misère ouverte 15, solo 25, solo slim 30.",
            "Après la dernière donne, le plus haut total gagne.",
        ],
    },
    {
        "titre": "Options",
        "points": [
            "Nombre de donnes, de 4 à 24 (8 par défaut) ; une donne rejouée ne compte pas.",
            "Trou (trois as).",
            "Misère et misère ouverte.",
        ],
    },
]
