from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.rooms.models import Room


class ReservationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Ativa"
    CANCELED = "CANCELED", "Cancelada"


class Reservation(models.Model):
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="reservations",
        verbose_name="Sala",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
        verbose_name="Usuário",
    )

    start_datetime = models.DateTimeField(
        verbose_name="Data e hora de início"
    )

    end_datetime = models.DateTimeField(
        verbose_name="Data e hora de término"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Descrição"
    )

    status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.ACTIVE,
        verbose_name="Status",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em",
    )

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ["-start_datetime"]

    @classmethod
    def has_conflict(
        cls,
        room,
        start_datetime,
        end_datetime,
        exclude_reservation_id=None,
        lock=False,
    ):
        conflict_qs = cls.objects.filter(
            room=room,
            status=ReservationStatus.ACTIVE,
            start_datetime__lt=end_datetime,
            end_datetime__gt=start_datetime,
        )

        if exclude_reservation_id is not None:
            conflict_qs = conflict_qs.exclude(pk=exclude_reservation_id)

        if lock:
            conflict_qs = conflict_qs.select_for_update()

        return conflict_qs.exists()

    def clean(self):
        errors = {}

        if self.start_datetime and self.end_datetime and self.end_datetime <= self.start_datetime:
            errors["end_datetime"] = (
                "O horário de término precisa ser depois do horário de início."
            )

        if (
            self.start_datetime
            and self.status == ReservationStatus.ACTIVE
            and self.start_datetime < timezone.now()
        ):
            errors["start_datetime"] = (
                "Esse horário já passou. Escolha um horário futuro para continuar."
            )

        if self.room_id and self.status == ReservationStatus.ACTIVE and not self.room.is_active:
            errors["room"] = "Esta sala está inativa e não está disponível para reservas."

        if (
            self.room_id
            and self.start_datetime
            and self.end_datetime
            and self.status == ReservationStatus.ACTIVE
            and self.has_conflict(
                room=self.room,
                start_datetime=self.start_datetime,
                end_datetime=self.end_datetime,
                exclude_reservation_id=self.pk,
            )
        ):
            errors["__all__"] = (
                "Este horário já está ocupado nessa sala. "
                "Confira a agenda abaixo e escolha outro período."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def cancel(self):
        if self.status == ReservationStatus.CANCELED:
            return False

        self.status = ReservationStatus.CANCELED
        self.save(update_fields=["status", "updated_at"])
        return True

    def __str__(self):
        return (
            f"{self.room.name} | "
            f"{self.user.get_full_name() or self.user.email} | "
            f"{self.start_datetime:%d/%m/%Y %H:%M}"
        )