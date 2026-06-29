from django.urls import path

from .views import (
    RoomCreateView,
    RoomToggleActiveView,
    RoomUpdateView,
    room_detail,
    room_list,
)

# 'app_name' cria o namespace 'rooms', usado nos templates como
# {% url 'rooms:room_list' %}. Evita conflito de nomes entre apps.
app_name = "rooms"

urlpatterns = [
    # Lista de salas (página inicial do app).
    path('', room_list, name='room_list'),
    # Rotas administrativas. Ficam ANTES da rota com <int:room_id> porque
    # 'new' e 'edit'/'toggle' são caminhos mais específicos; como '<int:...>'
    # só casa números, não há ambiguidade, mas manter o específico antes é boa
    # prática. As CBVs usam .as_view() para virar uma view chamável.
    path('new/', RoomCreateView.as_view(), name='room_create'),
    path('<int:pk>/edit/', RoomUpdateView.as_view(), name='room_update'),
    path('<int:pk>/toggle/', RoomToggleActiveView.as_view(), name='room_toggle_active'),
    # Detalhe da sala. Vem por último; o parâmetro vira 'room_id' na view.
    path('<int:room_id>/', room_detail, name='room_detail'),
]
