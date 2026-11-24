"""Regras de negócio de agenda: geração de datas recorrentes e detecção de conflito.

Mantemos a lógica aqui (fora das views e dos templates) para poder testar
isoladamente e reaproveitar entre a reserva única e a recorrente.
"""

from calendar import monthrange
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Recorrencia, Reserva, Sala

# Trava de segurança: nunca gerar uma série absurda de ocorrências.
MAX_OCORRENCIAS = 366


class ConflitosDeAgenda(Exception):
    def __init__(self, conflitos):
        self.conflitos = conflitos
        super().__init__('Já existe uma reserva em um ou mais horários solicitados.')


def _ultimo_dia_do_mes(ano, mes):
    return monthrange(ano, mes)[1]


def _somar_meses(base, meses):
    """Soma meses ancorando no dia original (dia 31 -> último dia do mês curto)."""
    total = (base.month - 1) + meses
    ano = base.year + total // 12
    mes = total % 12 + 1
    dia = min(base.day, _ultimo_dia_do_mes(ano, mes))
    return date(ano, mes, dia)


def gerar_datas(frequencia, intervalo, data_inicio, data_fim):
    """Expande a regra de recorrência em uma lista de datas (data_inicio..data_fim)."""
    intervalo = max(1, int(intervalo))
    datas = []

    if data_fim < data_inicio:
        return datas

    if frequencia == Recorrencia.DIARIA:
        atual = data_inicio
        while atual <= data_fim and len(datas) < MAX_OCORRENCIAS:
            datas.append(atual)
            atual = atual + timedelta(days=intervalo)

    elif frequencia == Recorrencia.SEMANAL:
        atual = data_inicio
        while atual <= data_fim and len(datas) < MAX_OCORRENCIAS:
            datas.append(atual)
            atual = atual + timedelta(weeks=intervalo)

    elif frequencia == Recorrencia.MENSAL:
        passo = 0
        atual = data_inicio
        while atual <= data_fim and len(datas) < MAX_OCORRENCIAS:
            datas.append(atual)
            passo += 1
            atual = _somar_meses(data_inicio, passo * intervalo)

    return datas


def reservas_em_conflito(sala, data, hora_inicio, hora_fim, excluir_ids=None):
    """Reservas da MESMA sala/dia cujo horário se sobrepõe ao intervalo dado.

    Sobreposição = inicio_existente < fim_novo E inicio_novo < fim_existente.
    Horários encostados (10-11 e 11-12) NÃO conflitam.
    """
    qs = Reserva.objects.filter(
        organizacao=sala.organizacao,
        sala=sala,
        data=data,
    )
    if excluir_ids:
        qs = qs.exclude(id__in=excluir_ids)
    return qs.filter(hora_inicio__lt=hora_fim, hora_fim__gt=hora_inicio)


def checar_conflitos_serie(sala, datas, hora_inicio, hora_fim):
    """Retorna a lista de conflitos (data, reserva_existente) para uma série.

    Como todas as ocorrências têm o mesmo horário em dias diferentes, não há
    conflito interno da série consigo mesma — só precisamos olhar o que já existe.
    """
    conflitos = []
    for d in datas:
        for existente in reservas_em_conflito(sala, d, hora_inicio, hora_fim):
            conflitos.append((d, existente))
    return conflitos


@transaction.atomic
def criar_reserva(reserva):
    """Revalida o conflito sob bloqueio da sala e grava a reserva."""
    sala = Sala.objects.select_for_update().get(pk=reserva.sala_id)
    if reserva.organizacao_id != sala.organizacao_id:
        raise ValueError('A sala e a reserva precisam pertencer à mesma organização.')
    reserva.full_clean()

    conflitos = list(reservas_em_conflito(
        sala,
        reserva.data,
        reserva.hora_inicio,
        reserva.hora_fim,
        excluir_ids=[reserva.pk] if reserva.pk else None,
    ))
    if conflitos:
        raise ConflitosDeAgenda([(reserva.data, item) for item in conflitos])

    reserva.save()
    return reserva


@transaction.atomic
def criar_serie(sala, titulo, responsavel, hora_inicio, hora_fim,
                frequencia, intervalo, data_inicio, data_fim, observacoes='',
                criado_por=None):
    """Cria a Recorrencia e todas as Reservas de uma vez (transação atômica).

    Revalida os conflitos enquanto a linha da sala está bloqueada.
    """
    sala = Sala.objects.select_for_update().select_related('organizacao').get(pk=sala.pk)
    if hora_inicio >= hora_fim:
        raise ValidationError({'hora_fim': 'Precisa ser posterior ao horário de início.'})
    if intervalo < 1:
        raise ValidationError({'intervalo': 'O intervalo precisa ser maior que zero.'})
    datas = gerar_datas(frequencia, intervalo, data_inicio, data_fim)
    if not datas:
        return None, []

    conflitos = checar_conflitos_serie(sala, datas, hora_inicio, hora_fim)
    if conflitos:
        raise ConflitosDeAgenda(conflitos)

    recorrencia = Recorrencia.objects.create(
        organizacao=sala.organizacao,
        frequencia=frequencia,
        intervalo=intervalo,
        data_inicio=data_inicio,
        data_fim=data_fim,
        criado_por=criado_por,
    )
    Reserva.objects.bulk_create([
        Reserva(
            organizacao=sala.organizacao,
            sala=sala,
            titulo=titulo,
            responsavel=responsavel,
            data=d,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            observacoes=observacoes,
            recorrencia=recorrencia,
            criado_por=criado_por,
        )
        for d in datas
    ])
    return recorrencia, datas
