from rest_framework.routers import DefaultRouter
from django.urls import include, path

from .api_views import (
    DashboardAPIView,
    RecorrenciaViewSet,
    ReservaViewSet,
    RecursoViewSet,
    SalaViewSet,
)


router = DefaultRouter()
router.register('recursos', RecursoViewSet, basename='api-recurso')
router.register('salas', SalaViewSet, basename='api-sala')
router.register('reservas', ReservaViewSet, basename='api-reserva')
router.register('series', RecorrenciaViewSet, basename='api-serie')

urlpatterns = [
    path('dashboard/', DashboardAPIView.as_view(), name='api-dashboard'),
    path('', include(router.urls)),
]
