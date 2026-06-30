import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags

from apps.rooms.models import Room

from .models import Reservation


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_DANGEROUS_BLOCKS_RE = re.compile(
    r"<(script|style|iframe|object|embed)[^>]*>.*?</(script|style|iframe|object|embed)>",
    re.IGNORECASE | re.DOTALL,
)
_INLINE_WHITESPACE_RE = re.compile(r"[ \t]+")


def _clean_text(value):
    if not value:
        return ""

    value = _CONTROL_CHARS_RE.sub("", str(value))
    value = _DANGEROUS_BLOCKS_RE.sub("", value)
    value = strip_tags(value)
    value = value.replace("\r", " ").replace("\n", " ")
    value = _INLINE_WHITESPACE_RE.sub(" ", value)
    return value.strip()


class ReservationForm(forms.ModelForm):
    description = forms.CharField(
        label="Descrição",
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3, "class": "input-control"}),
        error_messages={
            "max_length": "A descrição deve ter no máximo 500 caracteres.",
        },
    )

    class Meta:
        model = Reservation
        fields = ["room", "start_datetime", "end_datetime", "description"]
        # O seletor visual (calendário + relógio) é o flatpickr, inicializado no
        # template sobre os campos com a classe 'js-flatpickr'. Mantemos o
        # 'format' em ISO (%Y-%m-%dT%H:%M) para que, ao reexibir o formulário
        # após um erro, o flatpickr consiga reler o valor; ao usuário, ele
        # mostra a data em formato amigável (dd/mm/aaaa hh:mm) e ainda permite
        # digitar ("colocar por escrito").
        widgets = {
            "start_datetime": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "input-control js-flatpickr",
                    "placeholder": "dd/mm/aaaa --:--",
                    "autocomplete": "off",
                },
            ),
            "end_datetime": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "input-control js-flatpickr",
                    "placeholder": "dd/mm/aaaa --:--",
                    "autocomplete": "off",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        selected_room = kwargs.pop("room", None)
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = Room.objects.filter(is_active=True).order_by("name")
        self.fields["start_datetime"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["end_datetime"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["room"].widget.attrs["class"] = "input-control"

        if selected_room is not None:
            self.fields["room"].queryset = Room.objects.filter(pk=selected_room.pk)
            self.fields["room"].initial = selected_room

    def clean_description(self):
        return _clean_text(self.cleaned_data.get("description"))

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
