from django.db import models


class Room(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name="Nome"
    )

    location = models.CharField(
        max_length=255,
        verbose_name="Localização"
    )

    capacity = models.PositiveIntegerField(
        verbose_name="Capacidade"
    )

    resources = models.TextField(
        blank=True,
        verbose_name="Recursos"
    )

    description = models.TextField(
        blank=True,
        verbose_name="Descrição"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Ativa"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )

    class Meta:
        verbose_name = "Sala"
        verbose_name_plural = "Salas"
        ordering = ["name"]

    def __str__(self):
        return self.name