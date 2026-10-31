"""Options du rami (spec §6.2). N'importe pas Django."""

from tapis.options import Option

OPTIONS = [
    Option(
        "as",
        "Valeur de l'as",
        "choix",
        "bas1_haut11",
        choix=(
            ("bas1_haut11", "1 en bas de suite, 11 ailleurs"),
            ("toujours1", "Toujours 1"),
            ("toujours11", "Toujours 11"),
        ),
    ),
    Option("ouverture_suite_sans_joker", "Ouverture avec une suite sans joker", "booleen", False),
    Option(
        "recuperation_joker",
        "Récupération du joker",
        "choix",
        "apres_ouverture",
        choix=(("apres_ouverture", "Après sa propre ouverture"), ("jamais", "Jamais")),
    ),
    Option("penalite_joker", "Pénalité du joker", "entier", 20, minimum=0, maximum=50),
    Option("finir_par_defausse", "Finir par une défausse", "booleen", True),
    Option("defausse_a_poser", "Carte de la défausse à poser", "booleen", False),
    Option("manches", "Nombre de manches", "entier", 5, minimum=1, maximum=10),
]
