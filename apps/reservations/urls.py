from django.urls import path

from .views import reservation_create, reservation_list

app_name = "reservations"

urlpatterns = [
    path("", reservation_list, name="reservation_list"),
    path("new/", reservation_create, name="reservation_create"),
]