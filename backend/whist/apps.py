from django.apps import AppConfig


class WhistConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "whist"

    def ready(self):
        from tapis import registre
        from whist.jeu import Whist

        registre.inscrire(Whist())
