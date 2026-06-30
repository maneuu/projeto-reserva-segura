from django.contrib import admin
from django.urls import path, include

from config.views import home

# Identidade visual do painel administrativo (substitui os textos padrão
# "Django administration"). As cores e o logotipo são aplicados pelo template
# templates/admin/base_site.html + static/admin/css/ifpb-admin.css.
admin.site.site_header = "IFPB · Reserva Segura"
admin.site.site_title = "Administração | Reserva Segura IFPB"
admin.site.index_title = "Painel administrativo"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('accounts/', include('apps.accounts.urls')),
    path('rooms/', include('apps.rooms.urls')),
    path('reservations/', include('apps.reservations.urls')),

]