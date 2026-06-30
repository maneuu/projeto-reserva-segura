import logging

from django.core.management.base import BaseCommand

from apps.reservations.models import Reservation


logger = logging.getLogger("apps.reservations")


class Command(BaseCommand):
    help = "Marca como 'Expirada' toda reserva ativa cujo término já passou."

    def handle(self, *args, **options):
        total = Reservation.expire_overdue()
        logger.info("Reservas expiradas pelo comando | total=%s", total)
        self.stdout.write(self.style.SUCCESS(f"{total} reserva(s) expirada(s)."))
