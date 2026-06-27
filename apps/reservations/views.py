from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ReservationForm
from .models import Reservation


@login_required
def reservation_list(request):
	reservations = (
		Reservation.objects.select_related("room", "user")
		.filter(user=request.user)
		.order_by("-start_datetime")
	)
	return render(
		request,
		"reservations/reservation_list.html",
		{"reservations": reservations},
	)


@login_required
def reservation_create(request):
	initial = {}
	room_id = request.GET.get("room")
	if room_id:
		initial["room"] = room_id

	if request.method == "POST":
		form = ReservationForm(request.POST)
		if form.is_valid():
			reservation = form.save(commit=False)
			reservation.user = request.user
			reservation.save()
			messages.success(request, "Reserva criada com sucesso.")
			return redirect("reservations:reservation_list")
	else:
		form = ReservationForm(initial=initial)

	return render(request, "reservations/reservation_form.html", {"form": form})
