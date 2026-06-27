from django.conf import settings
from django.db import models

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

    def __str__(self):
        return (
            f"{self.room.name} | "
            f"{self.user.get_full_name() or self.user.email} | "
            f"{self.start_datetime:%d/%m/%Y %H:%M}"
        )