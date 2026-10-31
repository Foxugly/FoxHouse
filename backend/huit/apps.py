from django.apps import AppConfig


class HuitConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "huit"

    def ready(self):
        from huit.jeu import Huit
        from tapis import registre

        registre.inscrire(Huit())
