import uuid

from django.db import models


class Partie(models.Model):
    """Une partie d'un jeu inscrit au registre.

    `sieges` dit qui occupe chaque siège : `{"type": "humain", "joueur": <jeton>}`
    ou `{"type": "machine"}`. `joueur` est le jeton du créateur (recherche, purge).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    jeu = models.CharField(max_length=30)
    joueur = models.CharField(max_length=32, db_index=True)
    sieges = models.JSONField()
    etat = models.JSONField()
    version = models.PositiveIntegerField(default=0)
    terminee = models.BooleanField(default=False)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.jeu} {self.id}"
