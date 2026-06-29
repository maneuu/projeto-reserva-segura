"""
Testes de segurança e funcionais para o módulo de Gestão de Salas.

Cada classe de teste cobre um vetor específico do OWASP Top 10:
  - TestAccessControl       → A01: Broken Access Control
  - TestCSRFProtection      → A01/A05: CSRF em operações de escrita
  - TestInputSanitization   → A03: Injection / XSS via formulário
  - TestFormValidation      → A03: Validação de entradas
  - TestSecureErrorHandling → A05: Nenhuma mensagem de erro expõe detalhes internos
  - TestRoomVisibility      → A01: Salas inativas invisíveis para usuários comuns
"""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.rooms.forms import RoomForm
from apps.rooms.models import Room


# ---------------------------------------------------------------------------
# Helpers compartilhados
# ---------------------------------------------------------------------------

def make_user(email, password="Senha@123", is_staff=False, is_superuser=False):
    """Cria um usuário para os testes."""
    return User.objects.create_user(
        email=email,
        password=password,
        first_name="Teste",
        last_name="User",
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


def make_room(**kwargs):
    """Cria uma sala com valores padrão substituíveis."""
    defaults = {
        "name": "Sala de Testes",
        "location": "Bloco A",
        "capacity": 30,
        "resources": "Projetor, Ar-condicionado",
        "is_active": True,
    }
    defaults.update(kwargs)
    return Room.objects.create(**defaults)


# ---------------------------------------------------------------------------
# A01 – Broken Access Control
# Garante que APENAS staff/superuser acessa as rotas de gerenciamento.
# ---------------------------------------------------------------------------

class TestAccessControl(TestCase):

    def setUp(self):
        self.common_user = make_user("comum@teste.com")
        self.staff_user  = make_user("staff@teste.com", is_staff=True)
        self.room        = make_room()

    # -- Usuário não autenticado deve ser redirecionado ao login ------------

    def test_anonimo_create_redireciona_para_login(self):
        """A01: anônimo tentando criar sala → redirecionado ao login."""
        response = self.client.get(reverse("rooms:room_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_anonimo_update_redireciona_para_login(self):
        """A01: anônimo tentando editar sala → redirecionado ao login."""
        response = self.client.get(reverse("rooms:room_update", kwargs={"pk": self.room.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_anonimo_toggle_redireciona_para_login(self):
        """A01: anônimo tentando ativar/desativar sala → redirecionado ao login."""
        response = self.client.post(reverse("rooms:room_toggle_active", kwargs={"pk": self.room.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    # -- Usuário comum autenticado deve receber 403 -------------------------

    def test_usuario_comum_create_retorna_403(self):
        """A01: usuário sem staff tentando criar sala → 403 Forbidden."""
        self.client.force_login(self.common_user)
        response = self.client.get(reverse("rooms:room_create"))
        self.assertEqual(response.status_code, 403)

    def test_usuario_comum_update_retorna_403(self):
        """A01: usuário sem staff tentando editar sala → 403 Forbidden."""
        self.client.force_login(self.common_user)
        response = self.client.get(reverse("rooms:room_update", kwargs={"pk": self.room.pk}))
        self.assertEqual(response.status_code, 403)

    def test_usuario_comum_toggle_post_retorna_403(self):
        """A01: usuário sem staff tentando fazer toggle → 403 Forbidden."""
        self.client.force_login(self.common_user)
        response = self.client.post(
            reverse("rooms:room_toggle_active", kwargs={"pk": self.room.pk})
        )
        self.assertEqual(response.status_code, 403)

    # -- Staff tem acesso liberado ------------------------------------------

    def test_staff_acessa_create(self):
        """A01: staff consegue acessar o formulário de criação (200 OK)."""
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("rooms:room_create"))
        self.assertEqual(response.status_code, 200)

    def test_staff_acessa_update(self):
        """A01: staff consegue acessar o formulário de edição (200 OK)."""
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("rooms:room_update", kwargs={"pk": self.room.pk}))
        self.assertEqual(response.status_code, 200)

    # -- Acesso via URL direta (bypass tentativa) ---------------------------

    def test_usuario_comum_nao_acessa_url_direta_de_criacao(self):
        """A01: digitando a URL /rooms/new/ diretamente, usuário comum recebe 403."""
        self.client.force_login(self.common_user)
        response = self.client.get("/rooms/new/")
        self.assertEqual(response.status_code, 403)

    def test_usuario_comum_nao_acessa_url_direta_de_edicao(self):
        """A01: digitando /rooms/<pk>/edit/ diretamente, usuário comum recebe 403."""
        self.client.force_login(self.common_user)
        response = self.client.get(f"/rooms/{self.room.pk}/edit/")
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# A01/A05 – CSRF Protection
# Operações de escrita exigem método POST com token CSRF válido.
# ---------------------------------------------------------------------------

class TestCSRFProtection(TestCase):

    def setUp(self):
        self.staff_user = make_user("staff@teste.com", is_staff=True)
        self.room       = make_room()

    def test_toggle_via_get_retorna_405(self):
        """CSRF: toggle via GET (sem POST) deve retornar 405 Method Not Allowed."""
        self.client.force_login(self.staff_user)
        response = self.client.get(
            reverse("rooms:room_toggle_active", kwargs={"pk": self.room.pk})
        )
        self.assertEqual(response.status_code, 405)

    def test_toggle_sem_csrf_retorna_403(self):
        """CSRF: POST sem token CSRF deve ser rejeitado com 403."""
        # enforce_csrf_checks=True ativa a validação do token nos testes.
        client_com_csrf = self.client_class(enforce_csrf_checks=True)
        client_com_csrf.force_login(self.staff_user)
        response = client_com_csrf.post(
            reverse("rooms:room_toggle_active", kwargs={"pk": self.room.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_create_sem_csrf_retorna_403(self):
        """CSRF: POST de criação sem token CSRF deve ser rejeitado com 403."""
        client_com_csrf = self.client_class(enforce_csrf_checks=True)
        client_com_csrf.force_login(self.staff_user)
        response = client_com_csrf.post(
            reverse("rooms:room_create"),
            data={"name": "Nova", "location": "Bloco B", "capacity": 10},
        )
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# A03 – Injection / XSS
# O formulário deve sanitizar entradas antes de salvar no banco.
# ---------------------------------------------------------------------------

class TestInputSanitization(TestCase):

    def _form(self, **overrides):
        """Cria um RoomForm com dados válidos sobrescrevíveis."""
        data = {
            "name": "Sala Normal",
            "location": "Bloco C",
            "capacity": 20,
            "resources": "",
            "description": "",
            "is_active": True,
        }
        data.update(overrides)
        return RoomForm(data=data)

    # -- Nome e localização -------------------------------------------------

    def test_nome_com_tag_script_e_removido(self):
        """A03: tag <script> no nome deve ser removida pelo clean."""
        form = self._form(name="<script>alert('xss')</script>Sala")
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["name"], "Sala")

    def test_nome_com_html_e_removido(self):
        """A03: HTML em geral no nome deve ser removido."""
        form = self._form(name="<b>Sala</b> <em>01</em>")
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["name"], "Sala 01")

    def test_localizacao_com_tag_html_e_removida(self):
        """A03: tag HTML na localização deve ser removida."""
        form = self._form(location="<img src=x onerror=alert(1)>Bloco A")
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["location"], "Bloco A")

    def test_recursos_com_markup_e_removido(self):
        """A03: HTML nos recursos (campo multilinha) deve ser removido."""
        form = self._form(resources="Projetor<script>evil()</script>, Lousa")
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["resources"], "Projetor, Lousa")

    def test_descricao_com_markup_e_removida(self):
        """A03: HTML na descrição deve ser removido."""
        form = self._form(description="<h1>Sala</h1> para reuniões")
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["description"], "Sala para reuniões")

    def test_null_byte_e_rejeitado_pelo_django(self):
        """A03 (2 camadas): null byte (\x00) é rejeitado pelo validador nativo do
        Django (ProhibitNullCharactersValidator) antes mesmo do nosso clean_name.
        Isso demonstra duas camadas de defesa funcionando em conjunto."""
        form = self._form(name="Sala\x00Normal")
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_outros_caracteres_de_controle_sao_removidos(self):
        """A03: outros caracteres de controle (\x01, \x1f) são removidos pela
        sanitização _sanitize() no clean_name."""
        form = self._form(name="Sala\x01\x1f Normal")
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["name"], "Sala Normal")

    def test_espacos_multiplos_sao_normalizados(self):
        """A03: múltiplos espaços viram um único (evita bypass de validações)."""
        form = self._form(name="Sala    202")
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["name"], "Sala 202")

    def test_quebras_de_linha_em_campo_single_line_viram_espaco(self):
        """A03: quebras de linha no nome (campo single-line) viram espaço."""
        form = self._form(name="Sala\nInjetada")
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["name"], "Sala Injetada")


# ---------------------------------------------------------------------------
# A03 – Validação de entradas (regras de negócio)
# ---------------------------------------------------------------------------

class TestFormValidation(TestCase):

    def _form(self, **overrides):
        data = {
            "name": "Sala Válida",
            "location": "Bloco D",
            "capacity": 15,
            "resources": "",
            "description": "",
            "is_active": True,
        }
        data.update(overrides)
        return RoomForm(data=data)

    def test_nome_muito_curto_e_invalido(self):
        """Validação: nome com menos de 3 caracteres deve ser rejeitado."""
        form = self._form(name="AB")
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_capacidade_zero_e_invalida(self):
        """Validação: capacidade 0 deve ser rejeitada."""
        form = self._form(capacity=0)
        self.assertFalse(form.is_valid())
        self.assertIn("capacity", form.errors)

    def test_capacidade_negativa_e_invalida(self):
        """Validação: capacidade negativa deve ser rejeitada."""
        form = self._form(capacity=-5)
        self.assertFalse(form.is_valid())
        self.assertIn("capacity", form.errors)

    def test_capacidade_absurda_e_invalida(self):
        """Validação: capacidade acima de 10.000 deve ser rejeitada."""
        form = self._form(capacity=99999)
        self.assertFalse(form.is_valid())
        self.assertIn("capacity", form.errors)

    def test_nome_duplicado_e_rejeitado(self):
        """Validação (RF05): nome igual ao de sala existente deve ser rejeitado."""
        Room.objects.create(name="Sala Existente", location="X", capacity=10)
        form = self._form(name="Sala Existente")
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_nome_duplicado_case_insensitive(self):
        """Validação (RF05): duplicata deve ser detectada ignorando maiúsculas."""
        Room.objects.create(name="sala existente", location="X", capacity=10)
        form = self._form(name="SALA EXISTENTE")
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_edicao_propria_sala_nao_gera_duplicata(self):
        """Validação (RF07): editar a própria sala não deve disparar erro de duplicata."""
        sala = Room.objects.create(name="Sala Única", location="Bloco Y", capacity=5)
        form = RoomForm(data={
            "name": "Sala Única",
            "location": "Bloco Y",
            "capacity": 5,
            "resources": "",
            "description": "",
            "is_active": True,
        }, instance=sala)
        self.assertTrue(form.is_valid(), form.errors)

    def test_formulario_valido_completo(self):
        """Validação: formulário completamente válido deve ser aceito."""
        form = self._form(
            name="Laboratório de Redes",
            location="Bloco TI, 2º andar",
            capacity=40,
            resources="Computadores, Switch, Projetor",
            description="Uso exclusivo para aulas práticas.",
        )
        self.assertTrue(form.is_valid(), form.errors)


# ---------------------------------------------------------------------------
# A05 – Security Misconfiguration / Tratamento seguro de erros
# Nenhuma resposta deve revelar stack trace ou detalhes internos.
# ---------------------------------------------------------------------------

class TestSecureErrorHandling(TestCase):

    def setUp(self):
        self.common_user = make_user("comum@teste.com")
        self.staff_user  = make_user("staff@teste.com", is_staff=True)

    def test_403_nao_expoe_stack_trace(self):
        """A05: resposta 403 não deve conter 'Traceback' ou 'Exception'."""
        self.client.force_login(self.common_user)
        response = self.client.get(reverse("rooms:room_create"))
        self.assertEqual(response.status_code, 403)
        content = response.content.decode()
        self.assertNotIn("Traceback", content)
        self.assertNotIn("Exception", content)
        self.assertNotIn("django.core", content)

    def test_404_para_sala_inexistente_nao_expoe_internos(self):
        """A05: sala inexistente retorna 404 sem expor dados internos."""
        self.client.force_login(self.staff_user)
        response = self.client.get("/rooms/99999/")
        self.assertEqual(response.status_code, 404)
        content = response.content.decode()
        self.assertNotIn("Traceback", content)

    def test_post_invalido_retorna_form_com_erros_amigaveis(self):
        """A05: POST inválido não deve exibir stack trace, apenas erros do form."""
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse("rooms:room_create"), data={
            "name": "",       # inválido
            "location": "",   # inválido
            "capacity": -1,   # inválido
        })
        # Re-renderiza o form (200), não 500.
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("Traceback", content)
        self.assertNotIn("Exception", content)


# ---------------------------------------------------------------------------
# A01 – Visibilidade de salas inativas
# Usuários comuns não devem ver nem acessar salas desativadas.
# ---------------------------------------------------------------------------

class TestRoomVisibility(TestCase):

    def setUp(self):
        self.common_user = make_user("comum@teste.com")
        self.staff_user  = make_user("staff@teste.com", is_staff=True)
        self.sala_ativa   = make_room(name="Sala Ativa",   is_active=True)
        self.sala_inativa = make_room(name="Sala Inativa", is_active=False)

    # -- Listagem -----------------------------------------------------------

    def test_usuario_comum_nao_ve_sala_inativa_na_lista(self):
        """A01 (RF08): sala inativa não aparece na listagem para usuário comum."""
        self.client.force_login(self.common_user)
        response = self.client.get(reverse("rooms:room_list"))
        self.assertEqual(response.status_code, 200)
        nomes = [c["room"].name for c in response.context["room_cards"]]
        self.assertIn("Sala Ativa", nomes)
        self.assertNotIn("Sala Inativa", nomes)

    def test_staff_ve_sala_inativa_na_lista(self):
        """A01 (RF08): staff enxerga todas as salas, inclusive as inativas."""
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("rooms:room_list"))
        nomes = [c["room"].name for c in response.context["room_cards"]]
        self.assertIn("Sala Ativa", nomes)
        self.assertIn("Sala Inativa", nomes)

    def test_lista_de_salas_exibe_no_maximo_10_por_pagina(self):
        """A paginação da listagem deve limitar a tela a 10 salas por vez."""
        self.client.force_login(self.staff_user)

        for indice in range(12):
            make_room(name=f"Sala Extra {indice:02d}")

        response = self.client.get(reverse("rooms:room_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["room_cards"]), 10)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertTrue(response.context["is_paginated"])

        response_pagina_2 = self.client.get(reverse("rooms:room_list"), {"page": 2})
        self.assertEqual(response_pagina_2.status_code, 200)
        self.assertEqual(len(response_pagina_2.context["room_cards"]), 4)
        self.assertEqual(response_pagina_2.context["page_obj"].number, 2)

    # -- Detalhe ------------------------------------------------------------

    def test_usuario_comum_nao_acessa_detalhe_de_sala_inativa(self):
        """A01 (RF08): tentativa de acessar detalhe de sala inativa retorna 404 para comum."""
        self.client.force_login(self.common_user)
        response = self.client.get(
            reverse("rooms:room_detail", kwargs={"room_id": self.sala_inativa.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_staff_acessa_detalhe_de_sala_inativa(self):
        """A01 (RF08): staff pode ver o detalhe de sala inativa para poder reativá-la."""
        self.client.force_login(self.staff_user)
        response = self.client.get(
            reverse("rooms:room_detail", kwargs={"room_id": self.sala_inativa.pk})
        )
        self.assertEqual(response.status_code, 200)

    # -- Toggle de status ---------------------------------------------------

    def test_staff_pode_desativar_sala_ativa(self):
        """RF08: staff pode desativar uma sala ativa."""
        self.client.force_login(self.staff_user)
        self.client.post(
            reverse("rooms:room_toggle_active", kwargs={"pk": self.sala_ativa.pk})
        )
        self.sala_ativa.refresh_from_db()
        self.assertFalse(self.sala_ativa.is_active)

    def test_staff_pode_reativar_sala_inativa(self):
        """RF08: staff pode reativar uma sala que estava inativa."""
        self.client.force_login(self.staff_user)
        self.client.post(
            reverse("rooms:room_toggle_active", kwargs={"pk": self.sala_inativa.pk})
        )
        self.sala_inativa.refresh_from_db()
        self.assertTrue(self.sala_inativa.is_active)

    def test_usuario_comum_nao_pode_fazer_toggle(self):
        """A01 (RF08): usuário comum não pode desativar/ativar salas."""
        self.client.force_login(self.common_user)
        status_antes = self.sala_ativa.is_active
        self.client.post(
            reverse("rooms:room_toggle_active", kwargs={"pk": self.sala_ativa.pk})
        )
        self.sala_ativa.refresh_from_db()
        # O status NÃO deve ter mudado.
        self.assertEqual(self.sala_ativa.is_active, status_antes)


# ---------------------------------------------------------------------------
# Fluxo completo (CRUD) para staff
# ---------------------------------------------------------------------------

class TestRoomCRUD(TestCase):

    def setUp(self):
        self.staff_user = make_user("staff@teste.com", is_staff=True)
        self.client.force_login(self.staff_user)

    def test_staff_cria_sala_com_sucesso(self):
        """RF05: staff pode criar uma sala com dados válidos."""
        response = self.client.post(reverse("rooms:room_create"), data={
            "name": "Auditório Principal",
            "location": "Bloco Central",
            "capacity": 200,
            "resources": "Microfone, Projetor",
            "description": "Para eventos e palestras.",
            "is_active": True,
        })
        # Redireciona para o detalhe (criação bem-sucedida).
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Room.objects.filter(name="Auditório Principal").exists())

    def test_staff_edita_sala_com_sucesso(self):
        """RF07: staff pode editar uma sala existente."""
        sala = make_room(name="Sala Original")
        response = self.client.post(
            reverse("rooms:room_update", kwargs={"pk": sala.pk}),
            data={
                "name": "Sala Atualizada",
                "location": "Bloco B",
                "capacity": 25,
                "resources": "",
                "description": "",
                "is_active": True,
            }
        )
        self.assertEqual(response.status_code, 302)
        sala.refresh_from_db()
        self.assertEqual(sala.name, "Sala Atualizada")

    def test_dados_sao_salvos_sanitizados(self):
        """A03 + RF05: HTML no nome deve ser removido antes de salvar no banco."""
        self.client.post(reverse("rooms:room_create"), data={
            "name": "<b>Sala</b> Segura",
            "location": "Bloco S",
            "capacity": 10,
            "resources": "",
            "description": "",
            "is_active": True,
        })
        sala = Room.objects.filter(name="Sala Segura").first()
        self.assertIsNotNone(sala, "Sala deveria ter sido criada com nome sanitizado")
        self.assertNotIn("<b>", sala.name)
        self.assertNotIn("</b>", sala.name)
