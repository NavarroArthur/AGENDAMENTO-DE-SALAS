from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .api_permissions import (
    AdminParaEscrita,
    DonoOuAdminDaOrganizacao,
    PerfilOrganizacionalRequired,
)
from .dashboard import calcular_metricas, filtrar_periodo
from .forms import PeriodoForm
from .models import Recorrencia, Reserva, Recurso, Sala
from .serializers import (
    RecorrenciaSerializer,
    ReservaSerializer,
    RecursoSerializer,
    SalaSerializer,
)


class RecursoViewSet(viewsets.ModelViewSet):
    serializer_class = RecursoSerializer
    permission_classes = [IsAuthenticated, AdminParaEscrita]

    def get_queryset(self):
        return Recurso.objects.filter(
            organizacao=self.request.user.perfil.organizacao
        )

    def perform_create(self, serializer):
        serializer.save(organizacao=self.request.user.perfil.organizacao)


class SalaViewSet(viewsets.ModelViewSet):
    serializer_class = SalaSerializer
    permission_classes = [IsAuthenticated, AdminParaEscrita]

    def get_queryset(self):
        return Sala.objects.filter(
            organizacao=self.request.user.perfil.organizacao
        ).prefetch_related('recursos')


class ReservaViewSet(viewsets.ModelViewSet):
    serializer_class = ReservaSerializer
    permission_classes = [IsAuthenticated, DonoOuAdminDaOrganizacao]

    def get_queryset(self):
        return (
            Reserva.objects.filter(organizacao=self.request.user.perfil.organizacao)
            .select_related('sala', 'recorrencia')
        )


class RecorrenciaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RecorrenciaSerializer
    permission_classes = [IsAuthenticated, PerfilOrganizacionalRequired]

    def get_queryset(self):
        return Recorrencia.objects.filter(
            organizacao=self.request.user.perfil.organizacao
        )


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated, PerfilOrganizacionalRequired]

    def get(self, request):
        form = PeriodoForm(request.query_params)
        if not form.is_valid():
            raise ValidationError({
                campo: [str(erro) for erro in erros]
                for campo, erros in form.errors.items()
            })
        base = Reserva.objects.filter(organizacao=request.user.perfil.organizacao)
        metricas = calcular_metricas(filtrar_periodo(base, form))
        if request.user.perfil.papel != 'admin':
            metricas['reservas_por_mes'] = []
            metricas['reservas_por_dia'] = []
        return Response(metricas)
