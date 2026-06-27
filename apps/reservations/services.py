from django.core.exceptions import ValidationError
from django.db import transaction

from apps.rooms.models import Room

from .models import Reservation, ReservationStatus


def create_reservation(*, user, room, start_datetime, end_datetime, description=""):
    with transaction.atomic():
        # Lock room row to serialize writes for the same room and avoid race conditions.
        locked_room = Room.objects.select_for_update().get(pk=room.pk)

        if not locked_room.is_active:
            raise ValidationError("Não é permitido reservar sala inativa.")

        if Reservation.has_conflict(
            room=locked_room,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            lock=True,
        ):
            raise ValidationError("Conflito de horário para esta sala.")

        return Reservation.objects.create(
            user=user,
            room=locked_room,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            description=description,
            status=ReservationStatus.ACTIVE,
        )
