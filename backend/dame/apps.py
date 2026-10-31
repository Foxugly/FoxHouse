from django.apps import AppConfig


class DameConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dame"

    def ready(self):
        from dame.jeu import Dame
        from tapis import registre

        registre.inscrire(Dame())
