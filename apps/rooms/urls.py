from django.urls import path
from .views import room_list

urlpatterns = [
    path('', room_list, name='room_list'),
]