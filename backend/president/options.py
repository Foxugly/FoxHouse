"""Options du président (spec des jeux §3.2). N'importe pas Django."""

from tapis.options import Option

OPTIONS = [
    Option("deux_ferme", "Le 2 ferme le pli", "booleen", True),
    Option("echanges", "Échanges entre manches", "booleen", True),
    Option("manches", "Nombre de manches", "entier", 5, minimum=1, maximum=10),
]
