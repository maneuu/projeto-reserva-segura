from django.contrib import admin

from .forms import RoomForm
from .models import Room


# O decorator @admin.register(Room) registra o model no Django Admin usando
# a classe de configuração abaixo (equivale a admin.site.register(Room, RoomAdmin)).
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    # Reaproveita o MESMO formulário sanitizado das views, garantindo que as
    # validações/limpeza de entrada também valham quando um admin edita pelo
    # painel /admin (RNF03).
    form = RoomForm

    # Colunas exibidas na listagem de salas do painel.
    list_display = ("name", "location", "capacity", "is_active", "updated_at")
    # Filtro lateral por status ativo/inativo.
    list_filter = ("is_active",)
    # Caixa de busca por nome e localização.
    search_fields = ("name", "location")
    # Permite ligar/desligar 'is_active' direto na listagem (gestão rápida, RF08).
    list_editable = ("is_active",)
    ordering = ("name",)
    # Campos só de leitura: preenchidos automaticamente pelo model.
    readonly_fields = ("created_at", "updated_at")
