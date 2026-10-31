"""Options de la dame de pique (spec jeux §2.2). N'importe pas Django."""

from tapis.options import Option

OPTIONS = [
    Option("echange", "Échange de 3 cartes", "booleen", True),
    Option("score_fin", "Score de fin de partie", "entier", 100, minimum=20, maximum=200),
    Option("valet_carreau", "Valet de carreau à −10", "booleen", False),
]
