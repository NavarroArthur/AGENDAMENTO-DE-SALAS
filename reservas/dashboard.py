from django.db.models import Count, Q
from django.db.models.functions import ExtractWeekDay, TruncMonth


DIAS_DA_SEMANA = {
    1: 'Domingo',
    2: 'Segunda-feira',
    3: 'Terça-feira',
    4: 'Quarta-feira',
    5: 'Quinta-feira',
    6: 'Sexta-feira',
    7: 'Sábado',
}


def filtrar_periodo(queryset, form):
    if not form.is_valid():
        return queryset.none()

    inicio = form.cleaned_data.get('inicio')
    fim = form.cleaned_data.get('fim')
    if inicio:
        queryset = queryset.filter(data__gte=inicio)
    if fim:
        queryset = queryset.filter(data__lte=fim)
    return queryset


def calcular_metricas(queryset):
    kpis = queryset.aggregate(
        total=Count('id'),
        avulsas=Count('id', filter=Q(recorrencia__isnull=True)),
        recorrentes=Count('id', filter=Q(recorrencia__isnull=False)),
    )
    salas_mais_reservadas = list(
        queryset.values('sala__nome')
        .annotate(total=Count('id'))
        .order_by('-total', 'sala__nome')[:5]
    )
    reservas_por_mes = [
        {
            'mes': item['mes'].strftime('%m/%Y'),
            'total': item['total'],
        }
        for item in (
            queryset.annotate(mes=TruncMonth('data'))
            .values('mes')
            .annotate(total=Count('id'))
            .order_by('mes')
        )
    ]
    reservas_por_dia = [
        {
            'dia': DIAS_DA_SEMANA[item['dia_semana']],
            'total': item['total'],
        }
        for item in (
            queryset.annotate(dia_semana=ExtractWeekDay('data'))
            .values('dia_semana')
            .annotate(total=Count('id'))
            .order_by('dia_semana')
        )
    ]
    return {
        'kpis': kpis,
        'salas_mais_reservadas': salas_mais_reservadas,
        'reservas_por_mes': reservas_por_mes,
        'reservas_por_dia': reservas_por_dia,
    }
