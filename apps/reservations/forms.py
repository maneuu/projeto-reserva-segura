from django import forms
from django.core.exceptions import ValidationError

from apps.rooms.models import Room

from .models import Reservation, ReservationStatus


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ["room", "start_datetime", "end_datetime", "description"]
        widgets = {
            "start_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = Room.objects.filter(is_active=True).order_by("name")

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get("room")
        start_datetime = cleaned_data.get("start_datetime")
        end_datetime = cleaned_data.get("end_datetime")

        if not room or not start_datetime or not end_datetime:
            return cleaned_data

        if end_datetime <= start_datetime:
            raise ValidationError("A data/hora de término deve ser posterior ao início.")

        conflict_qs = Reservation.objects.filter(
            room=room,
            status=ReservationStatus.ACTIVE,
            start_datetime__lt=end_datetime,
            end_datetime__gt=start_datetime,
        )

        if self.instance.pk:
            conflict_qs = conflict_qs.exclude(pk=self.instance.pk)

        if conflict_qs.exists():
            raise ValidationError(
                "Já existe uma reserva ativa para esta sala no intervalo informado."
            )

        return cleaned_data
