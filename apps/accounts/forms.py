import re

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags

from .models import User


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _normalize_text(value):
    if value is None:
        return ""

    value = _CONTROL_CHARS_RE.sub("", str(value))
    value = strip_tags(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _validate_person_name(value, field_label):
    if len(value) < 2:
        raise ValidationError(f"Informe um {field_label.lower()} válido.")

    tokens = re.split(r"[\s\-']+", value)
    if not all(token.isalpha() for token in tokens if token):
        raise ValidationError(f"Informe um {field_label.lower()} válido.")

    return value


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="E-mail",
        max_length=254,
        error_messages={
            "max_length": "O e-mail informado é muito longo.",
        },
    )
    password = forms.CharField(
        label="Senha",
        max_length=128,
        widget=forms.PasswordInput,
        error_messages={
            "max_length": "A senha informada é muito longa.",
        },
    )

    def clean_email(self):
        return _normalize_text(self.cleaned_data["email"]).lower()


class RegisterForm(forms.Form):
    first_name = forms.CharField(
        label="Nome",
        max_length=150,
        error_messages={
            "max_length": "O nome informado é muito longo.",
        },
    )
    last_name = forms.CharField(
        label="Sobrenome",
        max_length=150,
        error_messages={
            "max_length": "O sobrenome informado é muito longo.",
        },
    )
    email = forms.EmailField(
        label="E-mail",
        max_length=254,
        error_messages={
            "max_length": "O e-mail informado é muito longo.",
        },
    )
    password1 = forms.CharField(
        label="Senha",
        max_length=128,
        widget=forms.PasswordInput,
        error_messages={
            "max_length": "A senha informada é muito longa.",
        },
    )
    password2 = forms.CharField(
        label="Confirmar senha",
        max_length=128,
        widget=forms.PasswordInput,
        error_messages={
            "max_length": "A confirmação de senha é muito longa.",
        },
    )

    def clean_first_name(self):
        name = _normalize_text(self.cleaned_data["first_name"])
        return _validate_person_name(name, "nome")

    def clean_last_name(self):
        name = _normalize_text(self.cleaned_data["last_name"])
        return _validate_person_name(name, "sobrenome")

    def clean_email(self):
        email = _normalize_text(self.cleaned_data["email"]).lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Já existe uma conta com este e-mail.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "As senhas não coincidem.")
            return cleaned_data

        if password1:
            user = User(
                email=cleaned_data.get("email", ""),
                first_name=cleaned_data.get("first_name", ""),
                last_name=cleaned_data.get("last_name", ""),
            )
            try:
                validate_password(password1, user=user)
            except ValidationError as exc:
                self.add_error("password1", exc)

        return cleaned_data

    def save(self):
        cleaned_data = self.cleaned_data
        return User.objects.create_user(
            email=cleaned_data["email"],
            password=cleaned_data["password1"],
            first_name=cleaned_data["first_name"],
            last_name=cleaned_data["last_name"],
        )