from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import RegisterForm


def login_view(request):
	if request.user.is_authenticated:
		return redirect("home")

	error_message = None

	if request.method == "POST":
		email = request.POST.get("email", "").strip()
		password = request.POST.get("password", "")
		next_url = request.POST.get("next") or request.GET.get("next")

		user = authenticate(request, email=email, password=password)

		if user is not None:
			login(request, user)

			if next_url and url_has_allowed_host_and_scheme(
				next_url,
				allowed_hosts={request.get_host()},
			):
				return redirect(next_url)

			return redirect("home")

		error_message = "Email ou senha inválidos."

	return render(
		request,
		"accounts/login.html",
		{
			"error_message": error_message,
			"email_value": request.POST.get("email", "") if request.method == "POST" else "",
			"next": request.GET.get("next", ""),
		},
	)


def register_view(request):
	if request.user.is_authenticated:
		return redirect("home")

	if request.method == "POST":
		form = RegisterForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, "Cadastro realizado com sucesso. Faça login para continuar.")
			return redirect("accounts:login")
	else:
		form = RegisterForm()

	return render(request, "accounts/register.html", {"form": form})


def logout_view(request):
	logout(request)
	return redirect("accounts:login")
