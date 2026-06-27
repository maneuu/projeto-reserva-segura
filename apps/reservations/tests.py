from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.rooms.models import Room

from .models import Reservation, ReservationStatus
from .services import create_reservation

User = get_user_model()


class ReservationFlowTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(email="user1@example.com", password="123456")
		self.other_user = User.objects.create_user(email="user2@example.com", password="123456")
		self.admin_user = User.objects.create_user(
			email="admin@example.com",
			password="123456",
			is_staff=True,
		)
		self.room = Room.objects.create(
			name="Sala 101",
			location="Bloco A",
			capacity=30,
			is_active=True,
		)

	def test_create_reservation_success(self):
		self.client.login(email="user1@example.com", password="123456")
		start = timezone.now() + timedelta(hours=2)
		end = start + timedelta(hours=1)

		response = self.client.post(
			reverse("reservations:reservation_create_for_room", args=[self.room.id]),
			{
				"room": self.room.id,
				"start_datetime": timezone.localtime(start).strftime("%Y-%m-%dT%H:%M"),
				"end_datetime": timezone.localtime(end).strftime("%Y-%m-%dT%H:%M"),
				"description": "Reunião de projeto",
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(Reservation.objects.count(), 1)
		reservation = Reservation.objects.first()
		self.assertEqual(reservation.user, self.user)
		self.assertEqual(reservation.status, ReservationStatus.ACTIVE)

	def test_create_reservation_conflict(self):
		start = timezone.now() + timedelta(hours=3)
		end = start + timedelta(hours=2)
		Reservation.objects.create(
			room=self.room,
			user=self.user,
			start_datetime=start,
			end_datetime=end,
			status=ReservationStatus.ACTIVE,
		)

		self.client.login(email="user2@example.com", password="123456")
		response = self.client.post(
			reverse("reservations:reservation_create_for_room", args=[self.room.id]),
			{
				"room": self.room.id,
				"start_datetime": timezone.localtime(start + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M"),
				"end_datetime": timezone.localtime(end + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M"),
				"description": "Tentativa com conflito",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Este horário já está ocupado nessa sala.")
		self.assertEqual(Reservation.objects.count(), 1)

	def test_cancel_is_logical(self):
		reservation = Reservation.objects.create(
			room=self.room,
			user=self.user,
			start_datetime=timezone.now() + timedelta(hours=4),
			end_datetime=timezone.now() + timedelta(hours=5),
			status=ReservationStatus.ACTIVE,
		)

		self.client.login(email="user1@example.com", password="123456")
		response = self.client.post(reverse("reservations:reservation_cancel", args=[reservation.id]))

		self.assertEqual(response.status_code, 302)
		reservation.refresh_from_db()
		self.assertEqual(reservation.status, ReservationStatus.CANCELED)
		self.assertEqual(Reservation.objects.count(), 1)

	def test_user_cannot_cancel_another_user_reservation(self):
		reservation = Reservation.objects.create(
			room=self.room,
			user=self.user,
			start_datetime=timezone.now() + timedelta(hours=6),
			end_datetime=timezone.now() + timedelta(hours=7),
			status=ReservationStatus.ACTIVE,
		)

		self.client.login(email="user2@example.com", password="123456")
		response = self.client.post(reverse("reservations:reservation_cancel", args=[reservation.id]))

		self.assertEqual(response.status_code, 302)
		reservation.refresh_from_db()
		self.assertEqual(reservation.status, ReservationStatus.ACTIVE)

	def test_admin_can_cancel_any_reservation(self):
		reservation = Reservation.objects.create(
			room=self.room,
			user=self.user,
			start_datetime=timezone.now() + timedelta(hours=8),
			end_datetime=timezone.now() + timedelta(hours=9),
			status=ReservationStatus.ACTIVE,
		)

		self.client.login(email="admin@example.com", password="123456")
		response = self.client.post(reverse("reservations:reservation_cancel", args=[reservation.id]))

		self.assertEqual(response.status_code, 302)
		reservation.refresh_from_db()
		self.assertEqual(reservation.status, ReservationStatus.CANCELED)

	def test_service_blocks_conflict(self):
		start = timezone.now() + timedelta(hours=10)
		end = start + timedelta(hours=1)
		Reservation.objects.create(
			room=self.room,
			user=self.user,
			start_datetime=start,
			end_datetime=end,
			status=ReservationStatus.ACTIVE,
		)

		with self.assertRaises(ValidationError):
			create_reservation(
				user=self.other_user,
				room=self.room,
				start_datetime=start + timedelta(minutes=15),
				end_datetime=end + timedelta(minutes=15),
				description="Conflito",
			)
