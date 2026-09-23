from django.contrib import admin

from .models import Recorrencia, Reserva, Recurso, Sala

admin.site.register(Recurso)
admin.site.register(Sala)
admin.site.register(Recorrencia)
admin.site.register(Reserva)
