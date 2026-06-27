from django.urls import path

from .views import (
    reservation_cancel,
    reservation_create,
    reservation_detail,
    reservation_list,
)

app_name = "reservations"

urlpatterns = [
    path("", reservation_list, name="reservation_list"),
    path("my/", reservation_list, name="my_reservations"),
    path("new/", reservation_create, name="reservation_create"),
    path("create/<int:room_id>/", reservation_create, name="reservation_create_for_room"),
    path("<int:reservation_id>/", reservation_detail, name="reservation_detail"),
    path("<int:reservation_id>/cancel/", reservation_cancel, name="reservation_cancel"),
]