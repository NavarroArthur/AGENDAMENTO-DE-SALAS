from django.urls import path

from . import views

app_name = 'reservas'

urlpatterns = [
    # Agenda é a página inicial
    path('', views.reserva_lista, name='reserva_lista'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('relatorios/reservas.csv', views.exportar_csv, name='exportar_csv'),

    # Recursos
    path('recursos/', views.recurso_lista, name='recurso_lista'),
    path('recursos/novo/', views.recurso_form, name='recurso_novo'),
    path('recursos/<int:pk>/editar/', views.recurso_form, name='recurso_editar'),
    path('recursos/<int:pk>/excluir/', views.recurso_excluir, name='recurso_excluir'),

    # Salas
    path('salas/', views.sala_lista, name='sala_lista'),
    path('salas/nova/', views.sala_form, name='sala_nova'),
    path('salas/<int:pk>/editar/', views.sala_form, name='sala_editar'),
    path('salas/<int:pk>/excluir/', views.sala_excluir, name='sala_excluir'),

    # Reservas
    path('reservas/nova/', views.reserva_nova, name='reserva_nova'),
    path('reservas/<int:pk>/excluir/', views.reserva_excluir, name='reserva_excluir'),

    # Reservas recorrentes
    path('reservas/recorrente/nova/', views.recorrencia_nova, name='recorrencia_nova'),
    path('series/<int:pk>/excluir/', views.recorrencia_excluir, name='recorrencia_excluir'),
]
