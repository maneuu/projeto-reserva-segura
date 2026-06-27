from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.rooms.models import Room

from .forms import ReservationForm
from .models import Reservation, ReservationStatus
from .services import create_reservation


def _can_manage_reservation(user, reservation):
	return user.is_staff or user.is_superuser or reservation.user_id == user.id


@login_required
def reservation_list(request):
	if request.user.is_staff or request.user.is_superuser:
		reservations = Reservation.objects.select_related("room", "user").order_by("-start_datetime")
	else:
		reservations = (
			Reservation.objects.select_related("room", "user")
			.filter(user=request.user)
			.order_by("-start_datetime")
		)

	return render(
		request,
		"reservations/reservation_list.html",
		{
			"reservations": reservations,
			"is_admin_view": request.user.is_staff or request.user.is_superuser,
		},
	)


@login_required
def reservation_create(request, room_id=None):
	selected_room = None
	if room_id is not None:
		selected_room = get_object_or_404(Room, pk=room_id)
	else:
		room_from_query = request.GET.get("room")
		if room_from_query:
			selected_room = get_object_or_404(Room, pk=room_from_query)

	if selected_room is not None and not selected_room.is_active:
		messages.error(request, "Não é possível reservar uma sala inativa.")
		return redirect("rooms:room_list")

	if request.method == "POST":
		form = ReservationForm(request.POST, room=selected_room)
		if form.is_valid():
			cleaned_data = form.cleaned_data
			try:
				reservation = create_reservation(
					user=request.user,
					room=cleaned_data["room"],
					start_datetime=cleaned_data["start_datetime"],
					end_datetime=cleaned_data["end_datetime"],
					description=cleaned_data.get("description", ""),
				)
			except ValidationError as exc:
				form.add_error(None, exc.messages[0] if exc.messages else str(exc))
			else:
				messages.success(request, "Reserva criada com sucesso.")
				return redirect("reservations:reservation_detail", reservation_id=reservation.pk)
	else:
		initial = {"room": selected_room} if selected_room else None
		form = ReservationForm(initial=initial, room=selected_room)

	room_schedule = []
	selected_room_id = None
	if selected_room is not None:
		selected_room_id = selected_room.pk
	elif form["room"].value():
		selected_room_id = form["room"].value()

	if selected_room_id:
		room_schedule = (
			Reservation.objects.select_related("user")
			.filter(room_id=selected_room_id, status=ReservationStatus.ACTIVE)
			.order_by("start_datetime")[:10]
		)

	return render(
		request,
		"reservations/reservation_form.html",
		{
			"form": form,
			"selected_room": selected_room,
			"room_schedule": room_schedule,
		},
	)


@login_required
def reservation_detail(request, reservation_id):
	reservation = get_object_or_404(
		Reservation.objects.select_related("room", "user"),
		pk=reservation_id,
	)

	if not _can_manage_reservation(request.user, reservation):
		messages.error(request, "Você não tem permissão para visualizar esta reserva.")
		return redirect("reservations:reservation_list")

	return render(
		request,
		"reservations/reservation_detail.html",
		{
			"reservation": reservation,
			"can_cancel": _can_manage_reservation(request.user, reservation),
		},
	)


@login_required
def reservation_cancel(request, reservation_id):
	if request.method != "POST":
		return redirect("reservations:reservation_detail", reservation_id=reservation_id)

	with transaction.atomic():
		reservation = get_object_or_404(
			Reservation.objects.select_for_update().select_related("room", "user"),
			pk=reservation_id,
		)

		if not _can_manage_reservation(request.user, reservation):
			messages.error(request, "Você não tem permissão para cancelar esta reserva.")
			return redirect("reservations:reservation_list")

		if reservation.cancel():
			messages.success(request, "Reserva cancelada com sucesso.")
		else:
			messages.info(request, "Esta reserva já estava cancelada.")

	return redirect("reservations:reservation_detail", reservation_id=reservation.pk)
