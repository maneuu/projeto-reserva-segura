from django.urls import path

from .views import room_detail, room_list

app_name = "rooms"

urlpatterns = [
    path('', room_list, name='room_list'),
    path('<int:room_id>/', room_detail, name='room_detail'),
]