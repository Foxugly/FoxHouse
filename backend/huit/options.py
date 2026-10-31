"""Options du 8 américain (spec §1.2). N'importe pas Django."""

from tapis.options import Option

OPTIONS = [
    Option("cartes_speciales", "Cartes spéciales (2, valet, as)", "booleen", True),
    Option("jokers", "Jokers (+4, sur tout)", "booleen", False),
    Option("manches", "Nombre de manches", "entier", 3, minimum=1, maximum=10),
]
