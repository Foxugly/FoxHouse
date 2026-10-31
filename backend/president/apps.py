from django.apps import AppConfig


class PresidentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "president"

    def ready(self):
        from president.jeu import President
        from tapis import registre

        registre.inscrire(President())
