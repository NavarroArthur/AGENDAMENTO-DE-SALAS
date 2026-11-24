import csv

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import admin_required, perfil_required
from core.models import Perfil
from .dashboard import calcular_metricas, filtrar_periodo
from .forms import (
    PeriodoForm,
    RecorrenciaForm,
    ReservaForm,
    RecursoForm,
    SalaForm,
)
from .models import Recorrencia, Reserva, Recurso, Sala
from .services import ConflitosDeAgenda, criar_reserva, criar_serie


def _responsavel_padrao(usuario):
    return usuario.get_full_name().strip() or usuario.get_username()


def _admin_do_perfil(request):
    return request.perfil.papel == Perfil.ADMIN


def _reserva_pode_ser_alterada(request, reserva):
    return _admin_do_perfil(request) or reserva.criado_por_id == request.user.pk


def _mensagens_de_conflito(request, conflitos):
    messages.error(
        request,
        f'A operação foi cancelada: {len(conflitos)} horário(s) já estão ocupados.',
    )
    for data, existente in conflitos:
        messages.warning(
            request,
            f'{data:%d/%m/%Y}: conflito com "{existente.titulo}" '
            f'({existente.hora_inicio:%H:%M}–{existente.hora_fim:%H:%M}).',
        )


# --------------------------------------------------------------------------- #
# Recursos (CRUD de administrador)                                            #
# --------------------------------------------------------------------------- #
@perfil_required
def recurso_lista(request):
    recursos = Recurso.objects.filter(organizacao=request.organizacao)
    return render(request, 'reservas/recurso_lista.html', {
        'recursos': recursos,
        'is_admin': _admin_do_perfil(request),
    })


@admin_required
def recurso_form(request, pk=None):
    instancia = (
        get_object_or_404(Recurso, pk=pk, organizacao=request.organizacao)
        if pk else None
    )
    if request.method == 'POST':
        form = RecursoForm(
            request.POST, instance=instancia, organizacao=request.organizacao
        )
        if form.is_valid():
            recurso = form.save(commit=False)
            recurso.organizacao = request.organizacao
            recurso.save()
            messages.success(request, 'Recurso salvo com sucesso.')
            return redirect('reservas:recurso_lista')
    else:
        form = RecursoForm(instance=instancia, organizacao=request.organizacao)
    return render(request, 'reservas/recurso_form.html', {
        'form': form,
        'editando': instancia is not None,
    })


@admin_required
def recurso_excluir(request, pk):
    recurso = get_object_or_404(
        Recurso, pk=pk, organizacao=request.organizacao
    )
    if request.method == 'POST':
        recurso.delete()
        messages.success(request, 'Recurso excluído.')
        return redirect('reservas:recurso_lista')
    return render(request, 'reservas/confirmar_exclusao.html', {
        'objeto': recurso,
        'tipo': 'recurso',
        'voltar': 'reservas:recurso_lista',
    })


# --------------------------------------------------------------------------- #
# Salas (CRUD de administrador)                                               #
# --------------------------------------------------------------------------- #
@perfil_required
def sala_lista(request):
    salas = Sala.objects.filter(organizacao=request.organizacao).prefetch_related('recursos')
    recursos = Recurso.objects.filter(organizacao=request.organizacao)

    q = request.GET.get('q', '').strip()
    recurso_id = request.GET.get('recurso', '')
    capacidade = request.GET.get('capacidade', '')

    if q:
        salas = salas.filter(nome__icontains=q)
    if recurso_id:
        salas = salas.filter(recursos__id=recurso_id)
    if capacidade.isdigit():
        salas = salas.filter(capacidade__gte=int(capacidade))

    return render(request, 'reservas/sala_lista.html', {
        'salas': salas.distinct(),
        'recursos': recursos,
        'is_admin': _admin_do_perfil(request),
    })


@admin_required
def sala_form(request, pk=None):
    instancia = (
        get_object_or_404(Sala, pk=pk, organizacao=request.organizacao)
        if pk else None
    )
    if request.method == 'POST':
        form = SalaForm(
            request.POST, instance=instancia, organizacao=request.organizacao
        )
        if form.is_valid():
            sala = form.save(commit=False)
            sala.organizacao = request.organizacao
            sala.save()
            form.save_m2m()
            messages.success(request, 'Sala salva com sucesso.')
            return redirect('reservas:sala_lista')
    else:
        form = SalaForm(instance=instancia, organizacao=request.organizacao)
    return render(request, 'reservas/sala_form.html', {
        'form': form,
        'editando': instancia is not None,
    })


@admin_required
def sala_excluir(request, pk):
    sala = get_object_or_404(Sala, pk=pk, organizacao=request.organizacao)
    if request.method == 'POST':
        sala.delete()
        messages.success(request, 'Sala excluída.')
        return redirect('reservas:sala_lista')
    return render(request, 'reservas/confirmar_exclusao.html', {
        'objeto': sala,
        'tipo': 'sala',
        'voltar': 'reservas:sala_lista',
    })


# --------------------------------------------------------------------------- #
# Reservas                                                                    #
# --------------------------------------------------------------------------- #
@perfil_required
def reserva_lista(request):
    reservas = (
        Reserva.objects.filter(organizacao=request.organizacao)
        .select_related('sala', 'recorrencia', 'criado_por')
    )
    return render(request, 'reservas/reserva_lista.html', {
        'reservas': reservas,
        'is_admin': _admin_do_perfil(request),
    })


@perfil_required
def reserva_nova(request):
    if request.method == 'POST':
        form = ReservaForm(request.POST, organizacao=request.organizacao)
        if form.is_valid():
            reserva = form.save(commit=False)
            reserva.organizacao = request.organizacao
            reserva.criado_por = request.user
            try:
                criar_reserva(reserva)
            except ConflitosDeAgenda as exc:
                _mensagens_de_conflito(request, exc.conflitos)
            else:
                messages.success(request, 'Reserva criada com sucesso.')
                return redirect('reservas:reserva_lista')
    else:
        form = ReservaForm(
            organizacao=request.organizacao,
            initial={'responsavel': _responsavel_padrao(request.user)},
        )
    return render(request, 'reservas/reserva_form.html', {'form': form})


@perfil_required
def reserva_excluir(request, pk):
    reserva = get_object_or_404(
        Reserva.objects.select_related('sala', 'recorrencia'),
        pk=pk,
        organizacao=request.organizacao,
    )
    if not _reserva_pode_ser_alterada(request, reserva):
        raise PermissionDenied('Você só pode excluir reservas criadas por sua conta.')
    if request.method == 'POST':
        reserva.delete()
        messages.success(request, 'Reserva excluída.')
        return redirect('reservas:reserva_lista')
    return render(request, 'reservas/confirmar_exclusao.html', {
        'objeto': reserva,
        'tipo': 'reserva',
        'voltar': 'reservas:reserva_lista',
    })


# --------------------------------------------------------------------------- #
# Reservas recorrentes                                                        #
# --------------------------------------------------------------------------- #
@perfil_required
def recorrencia_nova(request):
    if request.method == 'POST':
        form = RecorrenciaForm(request.POST, organizacao=request.organizacao)
        if form.is_valid():
            d = form.cleaned_data
            try:
                recorrencia, criadas = criar_serie(
                    sala=d['sala'],
                    titulo=d['titulo'],
                    responsavel=d['responsavel'],
                    hora_inicio=d['hora_inicio'],
                    hora_fim=d['hora_fim'],
                    frequencia=d['frequencia'],
                    intervalo=d['intervalo'],
                    data_inicio=d['data_inicio'],
                    data_fim=d['data_fim'],
                    observacoes=d['observacoes'],
                    criado_por=request.user,
                )
            except ConflitosDeAgenda as exc:
                _mensagens_de_conflito(request, exc.conflitos)
            else:
                if recorrencia is None:
                    messages.error(
                        request,
                        'A regra informada não gerou nenhuma data. Confira o período.',
                    )
                else:
                    messages.success(
                        request,
                        f'Série criada: {len(criadas)} reserva(s) sem conflito de agenda.',
                    )
                    return redirect('reservas:reserva_lista')
    else:
        form = RecorrenciaForm(
            organizacao=request.organizacao,
            initial={'responsavel': _responsavel_padrao(request.user)},
        )
    return render(request, 'reservas/recorrencia_form.html', {'form': form})


@perfil_required
def recorrencia_excluir(request, pk):
    recorrencia = get_object_or_404(
        Recorrencia, pk=pk, organizacao=request.organizacao
    )
    if not (_admin_do_perfil(request) or recorrencia.criado_por_id == request.user.pk):
        raise PermissionDenied('Você só pode excluir séries criadas por sua conta.')
    if request.method == 'POST':
        qtd = recorrencia.reservas.count()
        recorrencia.delete()
        messages.success(request, f'Série excluída ({qtd} reserva(s) removidas).')
        return redirect('reservas:reserva_lista')
    return render(request, 'reservas/confirmar_exclusao.html', {
        'objeto': recorrencia,
        'tipo': 'série de reservas',
        'voltar': 'reservas:reserva_lista',
        'extra': f'Isso remove as {recorrencia.reservas.count()} reserva(s) da série.',
    })


# --------------------------------------------------------------------------- #
# Dashboard e relatório CSV                                                   #
# --------------------------------------------------------------------------- #
@perfil_required
def dashboard(request):
    form = PeriodoForm(request.GET)
    base = Reserva.objects.filter(organizacao=request.organizacao)
    filtradas = filtrar_periodo(base, form)
    metricas = calcular_metricas(filtradas)
    is_admin = _admin_do_perfil(request)
    if not is_admin:
        metricas['reservas_por_mes'] = []
        metricas['reservas_por_dia'] = []

    return render(request, 'reservas/dashboard.html', {
        **metricas,
        'form': form,
        'is_admin': is_admin,
    })


def _proteger_celula_csv(valor):
    texto = '' if valor is None else str(valor)
    if texto.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + texto
    return texto


@admin_required
def exportar_csv(request):
    form = PeriodoForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest('Informe um período válido para exportar.')

    reservas = filtrar_periodo(
        Reserva.objects.filter(organizacao=request.organizacao)
        .select_related('sala', 'recorrencia'),
        form,
    )
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="reservas.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['Data', 'Início', 'Fim', 'Sala', 'Título', 'Responsável', 'Tipo'])
    for reserva in reservas:
        writer.writerow([
            reserva.data.isoformat(),
            reserva.hora_inicio.strftime('%H:%M'),
            reserva.hora_fim.strftime('%H:%M'),
            _proteger_celula_csv(reserva.sala.nome),
            _proteger_celula_csv(reserva.titulo),
            _proteger_celula_csv(reserva.responsavel),
            'Recorrente' if reserva.recorrente else 'Avulsa',
        ])
    return response
