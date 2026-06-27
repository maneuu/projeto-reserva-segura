from django.contrib import admin

from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
	list_display = (
		"id",
		"room",
		"user",
		"start_datetime",
		"end_datetime",
		"status",
		"created_at",
	)
	list_filter = ("status", "room", "created_at")
	search_fields = ("room__name", "user__username", "user__email", "description")
	ordering = ("-start_datetime",)