from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import DaOrganizacao


class Recurso(DaOrganizacao):
    """Equipamento/recurso que uma sala pode ter (projetor, TV, ar-condicionado...)."""

    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)

    class Meta:
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['organizacao', 'nome'],
                name='uniq_recurso_org_nome',
            ),
        ]

    def __str__(self):
        return self.nome


class Sala(DaOrganizacao):
    """Uma sala reservável. Os recursos são equipamentos fixos da sala."""

    nome = models.CharField(max_length=100)
    capacidade = models.IntegerField(default=0)
    localizacao = models.CharField(max_length=200, blank=True)
    recursos = models.ManyToManyField(Recurso, blank=True, related_name='salas')

    class Meta:
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['organizacao', 'nome'],
                name='uniq_sala_org_nome',
            ),
        ]

    def __str__(self):
        return self.nome


class Recorrencia(DaOrganizacao):
    """Regra de uma série de reservas. As ocorrências ficam em Reserva."""

    DIARIA = 'diaria'
    SEMANAL = 'semanal'
    MENSAL = 'mensal'
    FREQUENCIAS = [
        (DIARIA, 'Diária'),
        (SEMANAL, 'Semanal'),
        (MENSAL, 'Mensal'),
    ]

    frequencia = models.CharField(max_length=10, choices=FREQUENCIAS)
    intervalo = models.IntegerField(default=1)  # a cada N (dias/semanas/meses)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='series_reservas_criadas',
    )

    def clean(self):
        super().clean()
        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({'data_fim': 'A data final não pode ser anterior à inicial.'})
        if self.intervalo is not None and self.intervalo < 1:
            raise ValidationError({'intervalo': 'O intervalo precisa ser maior que zero.'})

    def __str__(self):
        return f'{self.get_frequencia_display()} a cada {self.intervalo} ({self.data_inicio} a {self.data_fim})'


class Reserva(DaOrganizacao):
    """Uma ocorrência de reserva (única ou parte de uma série recorrente)."""

    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='reservas')
    titulo = models.CharField(max_length=200)
    responsavel = models.CharField(max_length=120)
    data = models.DateField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    observacoes = models.TextField(blank=True)
    recorrencia = models.ForeignKey(
        Recorrencia,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reservas',
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas_criadas',
    )

    class Meta:
        ordering = ['data', 'hora_inicio']

    def clean(self):
        super().clean()
        if self.hora_inicio and self.hora_fim and self.hora_inicio >= self.hora_fim:
            raise ValidationError({'hora_fim': 'Precisa ser posterior ao horário de início.'})
        if self.sala_id and self.organizacao_id:
            if self.sala.organizacao_id != self.organizacao_id:
                raise ValidationError({'sala': 'A sala precisa pertencer à organização da reserva.'})
        if self.recorrencia_id and self.organizacao_id:
            if self.recorrencia.organizacao_id != self.organizacao_id:
                raise ValidationError({'recorrencia': 'A série precisa pertencer à organização da reserva.'})

    @property
    def recorrente(self):
        return self.recorrencia_id is not None

    def __str__(self):
        return f'{self.titulo} — {self.sala} em {self.data:%d/%m/%Y} {self.hora_inicio:%H:%M}'
