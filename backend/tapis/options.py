"""Options de partie : description et validation. N'importe pas Django."""

from dataclasses import dataclass


class OptionsInvalides(ValueError):
    """Message en français, destiné au joueur."""


@dataclass(frozen=True)
class Option:
    code: str
    libelle: str
    type: str  # "choix" | "booleen" | "entier"
    defaut: object
    choix: tuple = ()  # tuples (valeur, libelle)
    minimum: int | None = None
    maximum: int | None = None

    def decrire(self) -> dict:
        d = {"code": self.code, "libelle": self.libelle, "type": self.type, "defaut": self.defaut}
        if self.type == "choix":
            d["choix"] = [{"valeur": v, "libelle": lib} for v, lib in self.choix]
        if self.type == "entier":
            d["minimum"] = self.minimum
            d["maximum"] = self.maximum
        return d

    def verifier(self, valeur):
        erreur = OptionsInvalides(f"Valeur invalide pour l'option « {self.libelle} ».")
        if self.type == "booleen":
            if not isinstance(valeur, bool):
                raise erreur
        elif self.type == "entier":
            if isinstance(valeur, bool) or not isinstance(valeur, int):
                raise erreur
            if (self.minimum is not None and valeur < self.minimum) or (
                self.maximum is not None and valeur > self.maximum
            ):
                raise erreur
        elif self.type == "choix":
            if isinstance(valeur, bool) or valeur not in [v for v, _ in self.choix]:
                raise erreur
        else:
            raise ValueError(f"Type d'option inconnu : {self.type!r}")
        return valeur


def valider(options: list[Option], donnees: dict) -> dict:
    """Vérifie les valeurs données et complète les absentes par les défauts."""
    if not isinstance(donnees, dict):
        raise OptionsInvalides("Les options doivent être un objet.")
    connues = {o.code: o for o in options}
    for cle in donnees:
        if cle not in connues:
            raise OptionsInvalides(f"Option inconnue : « {cle} ».")
    return {
        code: o.verifier(donnees[code]) if code in donnees else o.defaut
        for code, o in connues.items()
    }
