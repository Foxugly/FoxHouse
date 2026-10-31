from django.apps import AppConfig


class RamiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rami"

    def ready(self):
        from rami.jeu import Rami
        from tapis import registre

        registre.inscrire(Rami())
