from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.reservations.models import Reservation, ReservationStatus

from .models import Room


@login_required
def room_list(request):
    now = timezone.now()
    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "all")

    active_reservations = Reservation.objects.filter(
        room=OuterRef("pk"),
        status=ReservationStatus.ACTIVE,
        start_datetime__lte=now,
        end_datetime__gt=now,
    )

    rooms = (
        Room.objects.filter(is_active=True)
        .annotate(has_active_reservation=Exists(active_reservations))
        .order_by("name")
    )

    if search:
        rooms = rooms.filter(name__icontains=search)

    if status == "available":
        rooms = rooms.filter(has_active_reservation=False)
    elif status == "unavailable":
        rooms = rooms.filter(has_active_reservation=True)
    else:
        status = "all"

    room_cards = [
        {
            "room": room,
            "is_available": not room.has_active_reservation,
        }
        for room in rooms
    ]

    return render(
        request,
        "rooms/room_list.html",
        {
            "room_cards": room_cards,
            "search": search,
            "status": status,
            "status_all": status == "all",
            "status_available": status == "available",
            "status_unavailable": status == "unavailable",
        },
    )


@login_required
def room_detail(request, room_id):
    now = timezone.now()

    room = get_object_or_404(Room, pk=room_id, is_active=True)
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
            "is_available": not has_active_reservation,
        },
    )