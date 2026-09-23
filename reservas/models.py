from django.db import models


class Recurso(models.Model):
    """Equipamento/recurso que uma sala pode ter (projetor, TV, ar-condicionado...)."""

    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Sala(models.Model):
    """Uma sala reservável. Os recursos são equipamentos fixos da sala."""

    nome = models.CharField(max_length=100, unique=True)
    capacidade = models.IntegerField(default=0)
    localizacao = models.CharField(max_length=200, blank=True)
    recursos = models.ManyToManyField(Recurso, blank=True, related_name='salas')

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Recorrencia(models.Model):
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

    def __str__(self):
        return f'{self.get_frequencia_display()} a cada {self.intervalo} ({self.data_inicio} a {self.data_fim})'


class Reserva(models.Model):
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

    class Meta:
        ordering = ['data', 'hora_inicio']

    @property
    def recorrente(self):
        return self.recorrencia_id is not None

    def __str__(self):
        return f'{self.titulo} — {self.sala} em {self.data:%d/%m/%Y} {self.hora_inicio:%H:%M}'
