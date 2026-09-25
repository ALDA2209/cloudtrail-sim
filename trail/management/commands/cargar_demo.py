from django.core.management.base import BaseCommand

from trail.models import Evento
from trail.simulador import generar_aleatorios, simular_ataque


class Command(BaseCommand):
    help = "Borra todos los eventos y carga datos de demostración (últimos 7 días + escenario de ataque)."

    def add_arguments(self, parser):
        parser.add_argument("--cantidad", type=int, default=150)

    def handle(self, *args, **opciones):
        Evento.objects.all().delete()
        generar_aleatorios(opciones["cantidad"], horas=168)
        pasos = simular_ataque()
        self.stdout.write(self.style.SUCCESS(
            f"Listo: {opciones['cantidad']} eventos aleatorios + {pasos} eventos del escenario de ataque."
        ))

