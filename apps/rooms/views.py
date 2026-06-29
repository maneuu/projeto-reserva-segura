from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, UpdateView

from apps.reservations.models import Reservation, ReservationStatus

from .forms import RoomForm
from .models import Room


def _is_room_manager(user):
    """Regra única de autorização: só staff/superuser gerencia salas.

    Centralizar essa checagem em uma função evita repetir a mesma condição
    em vários lugares (e o risco de esquecer parte dela). Usada tanto pelas
    views de leitura quanto pelo mixin de proteção (RNF02 / OWASP A01).
    """
    return user.is_authenticated and (user.is_staff or user.is_superuser)


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin que restringe uma view baseada em classe a administradores.

    Como funciona a combinação dos dois mixins:
      - ``LoginRequiredMixin`` roda primeiro: se o usuário NÃO está logado,
        ele é redirecionado para a tela de login (LOGIN_URL).
      - ``UserPassesTestMixin`` roda em seguida: chama ``test_func()`` e, se
        retornar False, dispara ``handle_no_permission()``.

    Sobrescrevemos ``handle_no_permission`` para diferenciar os dois casos:
      - anônimo  -> comportamento padrão (redireciona para o login);
      - logado, mas sem permissão -> levanta PermissionDenied, que o Django
        traduz em uma resposta 403 Forbidden usando o template de erro padrão,
        sem expor stack trace ou detalhes internos (RNF04 / OWASP A05).
    """

    def test_func(self):
        # Retorna True se o usuário pode acessar; False caso contrário.
        return _is_room_manager(self.request.user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            # Usuário não logado: deixa o comportamento padrão agir
            # (redirecionar para a página de login).
            return super().handle_no_permission()
        # Usuário logado sem privilégio: 403 explícito.
        raise PermissionDenied


@login_required
def room_list(request):
    """Lista de salas com busca e filtro de disponibilidade.

    Continua sendo uma view baseada em função (só leitura). A diferença de
    permissão aqui é o que cada perfil ENXERGA, não o acesso à página.
    """
    now = timezone.now()
    # .strip() remove espaços nas pontas do termo de busca.
    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "all")
    can_manage = _is_room_manager(request.user)

    # Subconsulta: existe alguma reserva ATIVA acontecendo AGORA para cada sala?
    # OuterRef("pk") referencia a sala da consulta externa (correlação).
    active_reservations = Reservation.objects.filter(
        room=OuterRef("pk"),
        status=ReservationStatus.ACTIVE,
        start_datetime__lte=now,   # já começou
        end_datetime__gt=now,      # ainda não terminou
    )

    # Administradores enxergam também as salas inativas (para poder reativá-las,
    # RF08); usuários comuns recebem apenas as ativas. Esse filtro no QUERYSET
    # é a real proteção — não basta esconder botões no template.
    base_queryset = Room.objects.all() if can_manage else Room.objects.filter(is_active=True)

    # annotate adiciona o campo virtual 'has_active_reservation' (True/False)
    # em cada sala, usando a subconsulta acima.
    rooms = (
        base_queryset
        .annotate(has_active_reservation=Exists(active_reservations))
        .order_by("name")
    )

    # Filtro por nome (icontains = "contém", ignorando maiúsc./minúsc.).
    if search:
        rooms = rooms.filter(name__icontains=search)

    # Filtro por disponibilidade no momento.
    if status == "available":
        rooms = rooms.filter(has_active_reservation=False)
    elif status == "unavailable":
        rooms = rooms.filter(has_active_reservation=True)
    else:
        status = "all"  # normaliza qualquer valor inesperado para "all"

    paginator = Paginator(rooms, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Monta uma lista de dicionários para o template: cada item tem a sala e
    # um booleano 'is_available' já calculado (sala precisa estar ativa E sem
    # reserva ativa no momento).
    room_cards = [
        {
            "room": room,
            "is_available": room.is_active and not room.has_active_reservation,
        }
        for room in page_obj.object_list
    ]

    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "rooms/room_list.html",
        {
            "room_cards": room_cards,
            "search": search,
            "status": status,
            "page_obj": page_obj,
            "is_paginated": page_obj.paginator.num_pages > 1,
            "query_string": query_params.urlencode(),
            # Flags booleanas para marcar a opção selecionada no <select>.
            "status_all": status == "all",
            "status_available": status == "available",
            "status_unavailable": status == "unavailable",
            "can_manage": can_manage,
        },
    )


@login_required
def room_detail(request, room_id):
    """Detalhe de uma sala específica."""
    now = timezone.now()
    can_manage = _is_room_manager(request.user)

    # Salas inativas só podem ser abertas por administradores. Para o usuário
    # comum, uma sala inativa simplesmente "não existe" (404) — não revelamos
    # sua existência. get_object_or_404 devolve a sala ou levanta 404.
    if can_manage:
        room = get_object_or_404(Room, pk=room_id)
    else:
        room = get_object_or_404(Room, pk=room_id, is_active=True)

    # Checa se há uma reserva ativa acontecendo neste exato momento.
    has_active_reservation = Reservation.objects.filter(
        room=room,
        status=ReservationStatus.ACTIVE,
        start_datetime__lte=now,
        end_datetime__gt=now,
    ).exists()

    return render(
        request,
        "rooms/room_detail.html",
        {
            "room": room,
            "is_available": room.is_active and not has_active_reservation,
            "can_manage": can_manage,
        },
    )


class RoomCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    """Cadastro de nova sala (RF05).

    Ordem dos mixins (importa por causa da MRO do Python):
      - StaffRequiredMixin  -> bloqueia quem não é admin ANTES de tudo;
      - SuccessMessageMixin -> exibe 'success_message' após salvar com sucesso;
      - CreateView          -> cuida do GET (mostra form) e POST (valida/salva).
    """

    model = Room
    form_class = RoomForm                       # usa nosso form sanitizado
    template_name = "rooms/room_form.html"
    success_message = "Sala cadastrada com sucesso."

    def get_context_data(self, **kwargs):
        # Adiciona textos de tela ao contexto. Como create e update usam o
        # MESMO template, passamos título/botão variáveis para reaproveitá-lo.
        context = super().get_context_data(**kwargs)
        context["form_title"] = "Cadastrar nova sala"
        context["submit_label"] = "Cadastrar sala"
        return context

    def get_success_url(self):
        # Para onde redirecionar após salvar: a página de detalhe da sala criada.
        # self.object é a sala recém-criada.
        return reverse("rooms:room_detail", kwargs={"room_id": self.object.pk})

    def form_valid(self, form):
        # form_valid roda quando o formulário passou na validação. Envolvemos
        # o salvamento em try/except para que uma eventual falha de banco vire
        # uma mensagem amigável, sem vazar o erro técnico (RNF04 / OWASP A05).
        try:
            return super().form_valid(form)
        except DatabaseError:
            messages.error(
                self.request,
                "Não foi possível salvar a sala no momento. Tente novamente.",
            )
            # Re-renderiza o formulário (sem 500) para o usuário tentar de novo.
            return self.form_invalid(form)


class RoomUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    """Atualização das informações de uma sala existente (RF07).

    Praticamente idêntica à CreateView, mas o UpdateView carrega a sala
    existente (pela 'pk' da URL) e preenche o formulário com seus dados.
    """

    model = Room
    form_class = RoomForm
    template_name = "rooms/room_form.html"
    success_message = "Sala atualizada com sucesso."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_title"] = "Editar sala"
        context["submit_label"] = "Salvar alterações"
        return context

    def get_success_url(self):
        return reverse("rooms:room_detail", kwargs={"room_id": self.object.pk})

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except DatabaseError:
            messages.error(
                self.request,
                "Não foi possível atualizar a sala no momento. Tente novamente.",
            )
            return self.form_invalid(form)


class RoomToggleActiveView(StaffRequiredMixin, View):
    """Ativa/desativa uma sala (RF08).

    Herda de View "pura" porque não renderiza um template próprio: apenas
    processa um POST e redireciona. Definimos só o método ``post`` — assim, um
    acesso via GET (ex.: alguém colando a URL no navegador) recebe 405 Method
    Not Allowed, evitando alterar estado por engano. O POST exige CSRF.
    """

    def post(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        # Inverte o status atual: ativa -> inativa e vice-versa.
        room.is_active = not room.is_active

        try:
            # update_fields limita o UPDATE a essas duas colunas (mais eficiente
            # e evita sobrescrever outros campos sem querer).
            room.save(update_fields=["is_active", "updated_at"])
        except DatabaseError:
            messages.error(
                request,
                "Não foi possível alterar o status da sala. Tente novamente.",
            )
        else:
            # Bloco 'else' do try roda só se NÃO houve exceção.
            if room.is_active:
                messages.success(request, f"Sala '{room.name}' ativada com sucesso.")
            else:
                messages.warning(
                    request,
                    f"Sala '{room.name}' desativada. Ela não poderá ser reservada.",
                )

        # Redireciona de volta para a página de origem (campo 'next' do form).
        # IMPORTANTE: validamos 'next' com url_has_allowed_host_and_scheme para
        # impedir "open redirect" — um atacante poderia colocar um link externo
        # malicioso em 'next'. Só aceitamos URLs do nosso próprio host.
        next_url = request.POST.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect("rooms:room_list")
