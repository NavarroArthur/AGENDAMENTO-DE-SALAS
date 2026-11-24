from django import forms

from .models import Recorrencia, Reserva, Recurso, Sala
from .services import reservas_em_conflito


class RecursoForm(forms.ModelForm):
    class Meta:
        model = Recurso
        fields = ['nome', 'descricao']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, organizacao=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organizacao = organizacao

    def clean_nome(self):
        nome = self.cleaned_data['nome']
        if self.organizacao is not None:
            duplicado = Recurso.objects.filter(
                organizacao=self.organizacao,
                nome__iexact=nome,
            )
            if self.instance.pk:
                duplicado = duplicado.exclude(pk=self.instance.pk)
            if duplicado.exists():
                raise forms.ValidationError('Já existe um recurso com esse nome na organização.')
        return nome


class SalaForm(forms.ModelForm):
    class Meta:
        model = Sala
        fields = ['nome', 'capacidade', 'localizacao', 'recursos']
        widgets = {
            'recursos': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, organizacao=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organizacao = organizacao
        if organizacao is None:
            self.fields['recursos'].queryset = Recurso.objects.none()
        else:
            self.fields['recursos'].queryset = Recurso.objects.filter(
                organizacao=organizacao
            )

    def clean_nome(self):
        nome = self.cleaned_data['nome']
        if self.organizacao is not None:
            duplicada = Sala.objects.filter(
                organizacao=self.organizacao,
                nome__iexact=nome,
            )
            if self.instance.pk:
                duplicada = duplicada.exclude(pk=self.instance.pk)
            if duplicada.exists():
                raise forms.ValidationError('Já existe uma sala com esse nome na organização.')
        return nome


class ReservaForm(forms.ModelForm):
    """Reserva única. A checagem de conflito acontece aqui, no is_valid()."""

    class Meta:
        model = Reserva
        fields = ['sala', 'titulo', 'responsavel', 'data',
                  'hora_inicio', 'hora_fim', 'observacoes']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time'}),
            'hora_fim': forms.TimeInput(attrs={'type': 'time'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, organizacao=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organizacao = organizacao
        if organizacao is None:
            self.fields['sala'].queryset = Sala.objects.none()
        else:
            self.fields['sala'].queryset = Sala.objects.filter(organizacao=organizacao)

    def clean(self):
        cleaned = super().clean()
        sala = cleaned.get('sala')
        data = cleaned.get('data')
        inicio = cleaned.get('hora_inicio')
        fim = cleaned.get('hora_fim')

        if inicio and fim and inicio >= fim:
            self.add_error('hora_fim', 'A hora de fim deve ser depois da hora de início.')
        elif sala and data and inicio and fim:
            if self.organizacao and sala.organizacao_id != self.organizacao.pk:
                self.add_error('sala', 'Escolha uma sala da sua organização.')
                return cleaned
            conflitos = reservas_em_conflito(
                sala,
                data,
                inicio,
                fim,
                excluir_ids=[self.instance.pk] if self.instance.pk else None,
            )
            conflito = conflitos.first()
            if conflito:
                raise forms.ValidationError(
                    f'Conflito de agenda: a sala "{sala}" já tem "{conflito.titulo}" '
                    f'em {data:%d/%m/%Y} das {conflito.hora_inicio:%H:%M} às {conflito.hora_fim:%H:%M}.'
                )
        return cleaned


class RecorrenciaForm(forms.Form):
    """Série recorrente: dados da reserva + regra de repetição.

    A validação de conflito (tudo ou nada) é feita na view, pois envolve
    várias datas de uma vez.
    """

    sala = forms.ModelChoiceField(queryset=Sala.objects.none(), label='Sala')
    titulo = forms.CharField(max_length=200, label='Título')
    responsavel = forms.CharField(max_length=120, label='Responsável')
    hora_inicio = forms.TimeField(
        label='Hora de início', widget=forms.TimeInput(attrs={'type': 'time'}))
    hora_fim = forms.TimeField(
        label='Hora de fim', widget=forms.TimeInput(attrs={'type': 'time'}))
    frequencia = forms.ChoiceField(
        choices=Recorrencia.FREQUENCIAS, label='Frequência')
    intervalo = forms.IntegerField(
        min_value=1, initial=1, label='A cada (nº de dias/semanas/meses)')
    data_inicio = forms.DateField(
        label='Início', widget=forms.DateInput(attrs={'type': 'date'}))
    data_fim = forms.DateField(
        label='Fim', widget=forms.DateInput(attrs={'type': 'date'}))
    observacoes = forms.CharField(
        required=False, widget=forms.Textarea(attrs={'rows': 3}), label='Observações')

    def __init__(self, *args, organizacao=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organizacao = organizacao
        self.fields['sala'].queryset = (
            Sala.objects.filter(organizacao=organizacao)
            if organizacao is not None else Sala.objects.none()
        )

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get('hora_inicio')
        fim = cleaned.get('hora_fim')
        if inicio and fim and inicio >= fim:
            self.add_error('hora_fim', 'A hora de fim deve ser depois da hora de início.')

        di = cleaned.get('data_inicio')
        df = cleaned.get('data_fim')
        if di and df and df < di:
            self.add_error('data_fim', 'A data de fim não pode ser antes da data de início.')
        return cleaned


class PeriodoForm(forms.Form):
    inicio = forms.DateField(required=False, label='Início')
    fim = forms.DateField(required=False, label='Fim')

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get('inicio')
        fim = cleaned.get('fim')
        if inicio and fim and fim < inicio:
            self.add_error('fim', 'A data final não pode ser anterior à data inicial.')
        return cleaned
