from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RecorrenciaForm, ReservaForm, RecursoForm, SalaForm
from .models import Recorrencia, Reserva, Recurso, Sala
from .services import checar_conflitos_serie, criar_serie, gerar_datas


# --------------------------------------------------------------------------- #
# Recursos (CRUD)                                                             #
# --------------------------------------------------------------------------- #
def recurso_lista(request):
    return render(request, 'reservas/recurso_lista.html',
                  {'recursos': Recurso.objects.all()})


def recurso_form(request, pk=None):
    instancia = get_object_or_404(Recurso, pk=pk) if pk else None
    if request.method == 'POST':
        form = RecursoForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Recurso salvo com sucesso.')
            return redirect('reservas:recurso_lista')
    else:
        form = RecursoForm(instance=instancia)
    return render(request, 'reservas/recurso_form.html',
                  {'form': form, 'editando': instancia is not None})


def recurso_excluir(request, pk):
    recurso = get_object_or_404(Recurso, pk=pk)
    if request.method == 'POST':
        recurso.delete()
        messages.success(request, 'Recurso excluído.')
        return redirect('reservas:recurso_lista')
    return render(request, 'reservas/confirmar_exclusao.html',
                  {'objeto': recurso, 'tipo': 'recurso',
                   'voltar': 'reservas:recurso_lista'})


# --------------------------------------------------------------------------- #
# Salas (CRUD)                                                                #
# --------------------------------------------------------------------------- #
def sala_lista(request):
    salas = Sala.objects.prefetch_related('recursos')
    recurso_id = request.GET.get('recurso')
    if recurso_id:
        salas = salas.filter(recursos__id=recurso_id)
    contexto = {
        'salas': salas,
        'recursos': Recurso.objects.all(),
        'recurso_id': recurso_id,
    }
    return render(request, 'reservas/sala_lista.html', contexto)


def sala_form(request, pk=None):
    instancia = get_object_or_404(Sala, pk=pk) if pk else None
    if request.method == 'POST':
        form = SalaForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sala salva com sucesso.')
            return redirect('reservas:sala_lista')
    else:
        form = SalaForm(instance=instancia)
    return render(request, 'reservas/sala_form.html',
                  {'form': form, 'editando': instancia is not None})


def sala_excluir(request, pk):
    sala = get_object_or_404(Sala, pk=pk)
    if request.method == 'POST':
        sala.delete()
        messages.success(request, 'Sala excluída.')
        return redirect('reservas:sala_lista')
    return render(request, 'reservas/confirmar_exclusao.html',
                  {'objeto': sala, 'tipo': 'sala', 'voltar': 'reservas:sala_lista'})


# --------------------------------------------------------------------------- #
# Reservas                                                                    #
# --------------------------------------------------------------------------- #
def reserva_lista(request):
    reservas = Reserva.objects.select_related('sala', 'recorrencia')
    return render(request, 'reservas/reserva_lista.html', {'reservas': reservas})


def reserva_nova(request):
    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Reserva criada com sucesso.')
            return redirect('reservas:reserva_lista')
    else:
        form = ReservaForm()
    return render(request, 'reservas/reserva_form.html', {'form': form})


def reserva_excluir(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    if request.method == 'POST':
        reserva.delete()
        messages.success(request, 'Reserva excluída.')
        return redirect('reservas:reserva_lista')
    return render(request, 'reservas/confirmar_exclusao.html',
                  {'objeto': reserva, 'tipo': 'reserva',
                   'voltar': 'reservas:reserva_lista'})


# --------------------------------------------------------------------------- #
# Reservas recorrentes (o núcleo: tudo ou nada)                              #
# --------------------------------------------------------------------------- #
def recorrencia_nova(request):
    if request.method == 'POST':
        form = RecorrenciaForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            datas = gerar_datas(d['frequencia'], d['intervalo'],
                                d['data_inicio'], d['data_fim'])

            if not datas:
                messages.error(request, 'A regra informada não gerou nenhuma data. '
                                        'Confira o período e o intervalo.')
            else:
                conflitos = checar_conflitos_serie(
                    d['sala'], datas, d['hora_inicio'], d['hora_fim'])

                if conflitos:
                    # Tudo ou nada: não grava NADA e mostra cada data em conflito.
                    messages.error(
                        request,
                        f'A série NÃO foi criada: {len(conflitos)} de {len(datas)} '
                        f'ocorrência(s) conflitam com reservas existentes.')
                    for data_conf, existente in conflitos:
                        messages.warning(
                            request,
                            f'{data_conf:%d/%m/%Y}: {d["hora_inicio"]:%H:%M}–{d["hora_fim"]:%H:%M} '
                            f'choca com "{existente.titulo}" '
                            f'({existente.hora_inicio:%H:%M}–{existente.hora_fim:%H:%M}).')
                else:
                    _, criadas = criar_serie(
                        sala=d['sala'], titulo=d['titulo'],
                        responsavel=d['responsavel'],
                        hora_inicio=d['hora_inicio'], hora_fim=d['hora_fim'],
                        frequencia=d['frequencia'], intervalo=d['intervalo'],
                        data_inicio=d['data_inicio'], data_fim=d['data_fim'],
                        observacoes=d['observacoes'])
                    messages.success(
                        request,
                        f'Série criada: {len(criadas)} reserva(s) sem conflito de agenda.')
                    return redirect('reservas:reserva_lista')
    else:
        form = RecorrenciaForm()
    return render(request, 'reservas/recorrencia_form.html', {'form': form})


def recorrencia_excluir(request, pk):
    recorrencia = get_object_or_404(Recorrencia, pk=pk)
    if request.method == 'POST':
        qtd = recorrencia.reservas.count()
        recorrencia.delete()  # cascata apaga as reservas da série
        messages.success(request, f'Série excluída ({qtd} reserva(s) removidas).')
        return redirect('reservas:reserva_lista')
    return render(request, 'reservas/confirmar_exclusao.html',
                  {'objeto': recorrencia, 'tipo': 'série de reservas',
                   'voltar': 'reservas:reserva_lista',
                   'extra': f'Isso remove as {recorrencia.reservas.count()} reserva(s) da série.'})
