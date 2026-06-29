from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.forms import LoginForm, RegisterForm


User = get_user_model()


class AccountSecurityTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			email="usuario@exemplo.com",
			password="Senha@123",
			first_name="Usuario",
			last_name="Teste",
		)

	def test_login_form_normaliza_email(self):
		form = LoginForm(data={"email": "  USUARIO@EXEMPLO.COM  ", "password": "Senha@123"})
		self.assertTrue(form.is_valid(), form.errors)
		self.assertEqual(form.cleaned_data["email"], "usuario@exemplo.com")

	def test_register_form_limpa_e_valida_nomes(self):
		form = RegisterForm(
			data={
				"first_name": "  João  ",
				"last_name": "  Silva  ",
				"email": "novo@exemplo.com",
				"password1": "Senha@123",
				"password2": "Senha@123",
			}
		)
		self.assertTrue(form.is_valid(), form.errors)
		self.assertEqual(form.cleaned_data["first_name"], "João")
		self.assertEqual(form.cleaned_data["last_name"], "Silva")

	def test_register_form_rejeita_nome_invalido(self):
		form = RegisterForm(
			data={
				"first_name": "João123",
				"last_name": "Silva",
				"email": "novo2@exemplo.com",
				"password1": "Senha@123",
				"password2": "Senha@123",
			}
		)
		self.assertFalse(form.is_valid())
		self.assertIn("first_name", form.errors)

	def test_login_view_autentica_email_com_espacos_e_maiusculas(self):
		with self.assertLogs("apps.accounts.views", level="INFO") as logs:
			response = self.client.post(
				reverse("accounts:login"),
				data={"email": "  USUARIO@EXEMPLO.COM  ", "password": "Senha@123"},
			)

		self.assertEqual(response.status_code, 302)
		self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
		self.assertTrue(any("Login realizado com sucesso" in entry for entry in logs.output))

	def test_login_view_mensagem_generica_para_credenciais_invalidas(self):
		response = self.client.post(
			reverse("accounts:login"),
			data={"email": "usuario@exemplo.com", "password": "senha-incorreta"},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Não foi possível entrar com as credenciais informadas.")

	def test_logout_requer_post(self):
		self.client.force_login(self.user)
		response = self.client.get(reverse("accounts:logout"))
		self.assertEqual(response.status_code, 405)

	def test_logout_post_loga_evento_e_redireciona(self):
		self.client.force_login(self.user)

		with self.assertLogs("apps.accounts.views", level="INFO") as logs:
			response = self.client.post(reverse("accounts:logout"))

		self.assertEqual(response.status_code, 302)
		self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
		self.assertTrue(any("Logout realizado" in entry for entry in logs.output))
