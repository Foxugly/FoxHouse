from django.urls import path

from parties import views

urlpatterns = [
    path("jeux/", views.jeux, name="jeux"),
    path("parties/", views.creer, name="creer"),
    path("parties/courante/", views.courante, name="courante"),
    path("parties/<uuid:pk>/", views.detail, name="detail"),
    path("parties/<uuid:pk>/actions/", views.action, name="action"),
]
