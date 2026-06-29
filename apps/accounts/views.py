import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import LoginForm, RegisterForm


logger = logging.getLogger(__name__)


def login_view(request):
	if request.user.is_authenticated:
		return redirect("home")

	form = LoginForm(request.POST or None)
	next_url = request.POST.get("next") or request.GET.get("next", "")

	if request.method == "POST":
		if form.is_valid():
			email = form.cleaned_data["email"]
			password = form.cleaned_data["password"]

			try:
				user = authenticate(request, email=email, password=password)
			except Exception:
				logger.exception("Falha inesperada ao autenticar usuário: %s", email)
				form.add_error(None, "Não foi possível acessar o sistema no momento.")
			else:
				if user is not None:
					login(request, user)
					logger.info("Login realizado com sucesso: %s", email)

					if next_url and url_has_allowed_host_and_scheme(
						next_url,
						allowed_hosts={request.get_host()},
					):
						return redirect(next_url)

					return redirect("home")

				logger.warning("Tentativa de login inválida: %s", email)
				form.add_error(None, "Não foi possível entrar com as credenciais informadas.")

	return render(
		request,
		"accounts/login.html",
		{
			"form": form,
			"next": next_url,
		},
	)


def register_view(request):
	if request.user.is_authenticated:
		return redirect("home")

	form = RegisterForm(request.POST or None)

	if request.method == "POST":
		if form.is_valid():
			try:
				user = form.save()
			except Exception:
				logger.exception("Falha inesperada ao cadastrar usuário: %s", form.cleaned_data.get("email"))
				form.add_error(None, "Não foi possível concluir o cadastro no momento.")
			else:
				logger.info("Usuário cadastrado com sucesso: %s", user.email)
				messages.success(request, "Cadastro realizado com sucesso. Faça login para continuar.")
				return redirect("accounts:login")

	return render(request, "accounts/register.html", {"form": form})


@require_POST
def logout_view(request):
	logger.info("Logout realizado: %s", getattr(request.user, "email", "desconhecido"))
	logout(request)
	return redirect("accounts:login")
