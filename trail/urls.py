from django.urls import path

from . import views

urlpatterns = [
    path("", views.resumen, name="resumen"),
    path("simular/", views.panel, name="panel"),
    path("historial/", views.historial, name="historial"),
    path("evento/<uuid:event_id>/", views.detalle, name="detalle"),
    path("exportar/", views.exportar, name="exportar"),
    path("integridad/", views.integridad, name="integridad"),
]
