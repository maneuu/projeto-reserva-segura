from django.contrib import admin
from django.urls import path, include

from config.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('accounts/', include('apps.accounts.urls')),
    path('rooms/', include('apps.rooms.urls')),
    path('reservations/', include('apps.reservations.urls')),

]