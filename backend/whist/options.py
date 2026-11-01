"""Options du whist à la couleur (spec whist §3). N'importe pas Django."""

from tapis.options import Option

OPTIONS = [
    Option("donnes", "Nombre de donnes", "entier", 8, minimum=4, maximum=24),
    Option("trou", "Trou (trois as)", "booleen", True),
    Option("misere", "Misère et misère ouverte", "booleen", True),
]
