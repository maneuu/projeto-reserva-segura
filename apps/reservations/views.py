import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.rooms.models import Room

from .forms import ReservationForm
from .models import Reservation, ReservationStatus
from .services import create_reservation


logger = logging.getLogger(__name__)


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
		logger.warning(
			"Tentativa de reservar sala inativa: user=%s room=%s",
			request.user.pk,
			selected_room.pk,
		)
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
				logger.warning(
					"Falha de validação ao criar reserva: user=%s room=%s errors=%s",
					request.user.pk,
					cleaned_data["room"].pk,
					exc.messages,
				)
				form.add_error(None, exc.messages[0] if exc.messages else str(exc))
			except Exception:
				logger.exception(
					"Erro inesperado ao criar reserva: user=%s room=%s",
					request.user.pk,
					cleaned_data["room"].pk,
				)
				form.add_error(None, "Não foi possível criar a reserva no momento.")
			else:
				logger.info(
					"Reserva criada com sucesso: user=%s room=%s reservation=%s",
					request.user.pk,
					reservation.room_id,
					reservation.pk,
				)
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
		logger.warning(
			"Tentativa de visualizar reserva sem permissão: user=%s reservation=%s",
			request.user.pk,
			reservation.pk,
		)
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
@require_POST
def reservation_cancel(request, reservation_id):
	try:
		with transaction.atomic():
			reservation = get_object_or_404(
				Reservation.objects.select_for_update().select_related("room", "user"),
				pk=reservation_id,
			)

			if not _can_manage_reservation(request.user, reservation):
				logger.warning(
					"Tentativa de cancelar reserva sem permissão: user=%s reservation=%s",
					request.user.pk,
					reservation.pk,
				)
				messages.error(request, "Você não tem permissão para cancelar esta reserva.")
				return redirect("reservations:reservation_list")

			if reservation.cancel():
				logger.info(
					"Reserva cancelada com sucesso: user=%s reservation=%s",
					request.user.pk,
					reservation.pk,
				)
				messages.success(request, "Reserva cancelada com sucesso.")
			else:
				logger.info(
					"Tentativa de cancelar reserva já cancelada: user=%s reservation=%s",
					request.user.pk,
					reservation.pk,
				)
				messages.info(request, "Esta reserva já estava cancelada.")
	except Exception:
		logger.exception(
			"Erro inesperado ao cancelar reserva: user=%s reservation=%s",
			request.user.pk,
			reservation_id,
		)
		messages.error(request, "Não foi possível cancelar a reserva no momento.")
		return redirect("reservations:reservation_list")

	return redirect("reservations:reservation_detail", reservation_id=reservation.pk)
