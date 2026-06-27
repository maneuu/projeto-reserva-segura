from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.rooms.models import Room

from .models import Reservation


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ["room", "start_datetime", "end_datetime", "description"]
        widgets = {
            "start_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "input-control", "step": "300"}
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "input-control", "step": "300"}
            ),
            "description": forms.Textarea(attrs={"rows": 3, "class": "input-control"}),
        }

    def __init__(self, *args, **kwargs):
        selected_room = kwargs.pop("room", None)
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = Room.objects.filter(is_active=True).order_by("name")
        self.fields["start_datetime"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["end_datetime"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["room"].widget.attrs["class"] = "input-control"

        min_datetime_value = timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M")
        self.fields["start_datetime"].widget.attrs["min"] = min_datetime_value
        self.fields["end_datetime"].widget.attrs["min"] = min_datetime_value

        if selected_room is not None:
            self.fields["room"].queryset = Room.objects.filter(pk=selected_room.pk)
            self.fields["room"].initial = selected_room

    def clean_description(self):
        return (self.cleaned_data.get("description") or "").strip()

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get("room")
        start_datetime = cleaned_data.get("start_datetime")
        end_datetime = cleaned_data.get("end_datetime")

        if not room or not start_datetime or not end_datetime:
            return cleaned_data

        # All business-rule validation is handled by model.clean() via
        # ModelForm._post_clean(), so we only do structural checks here
        # to keep error messages in one authoritative place.
        if end_datetime <= start_datetime:
            raise ValidationError(
                "O horário de término precisa ser depois do horário de início."
            )

        return cleaned_data
