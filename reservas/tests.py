from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from .models import Recorrencia, Reserva, Recurso, Sala
from .services import (
    checar_conflitos_serie,
    criar_serie,
    gerar_datas,
    reservas_em_conflito,
)


class GerarDatasTest(TestCase):
    def test_diaria_simples(self):
        datas = gerar_datas('diaria', 1, date(2026, 1, 1), date(2026, 1, 5))
        self.assertEqual(len(datas), 5)
        self.assertEqual(datas[0], date(2026, 1, 1))
        self.assertEqual(datas[-1], date(2026, 1, 5))

    def test_diaria_com_intervalo(self):
        datas = gerar_datas('diaria', 2, date(2026, 1, 1), date(2026, 1, 7))
        self.assertEqual(datas, [date(2026, 1, 1), date(2026, 1, 3),
                                 date(2026, 1, 5), date(2026, 1, 7)])

    def test_semanal(self):
        datas = gerar_datas('semanal', 1, date(2026, 1, 5), date(2026, 1, 26))
        self.assertEqual(datas, [date(2026, 1, 5), date(2026, 1, 12),
                                 date(2026, 1, 19), date(2026, 1, 26)])

    def test_semanal_quinzenal(self):
        datas = gerar_datas('semanal', 2, date(2026, 1, 5), date(2026, 2, 2))
        self.assertEqual(datas, [date(2026, 1, 5), date(2026, 1, 19), date(2026, 2, 2)])

    def test_mensal(self):
        datas = gerar_datas('mensal', 1, date(2026, 1, 10), date(2026, 4, 10))
        self.assertEqual(datas, [date(2026, 1, 10), date(2026, 2, 10),
                                 date(2026, 3, 10), date(2026, 4, 10)])

    def test_mensal_ancora_dia_31(self):
        # dia 31 deve cair no último dia dos meses curtos, sem "escorregar"
        datas = gerar_datas('mensal', 1, date(2026, 1, 31), date(2026, 4, 30))
        self.assertEqual(datas, [date(2026, 1, 31), date(2026, 2, 28),
                                 date(2026, 3, 31), date(2026, 4, 30)])

    def test_periodo_invertido_retorna_vazio(self):
        self.assertEqual(gerar_datas('diaria', 1, date(2026, 1, 5), date(2026, 1, 1)), [])

    def test_trava_maximo(self):
        datas = gerar_datas('diaria', 1, date(2026, 1, 1), date(2030, 1, 1))
        self.assertLessEqual(len(datas), 366)


class ConflitoTest(TestCase):
    def setUp(self):
        self.sala = Sala.objects.create(nome='Auditório')
        self.outra = Sala.objects.create(nome='Sala 2')
        Reserva.objects.create(
            sala=self.sala, titulo='Existente', responsavel='Ana',
            data=date(2026, 3, 10), hora_inicio=time(10, 0), hora_fim=time(11, 0))

    def test_sobreposicao_detectada(self):
        conf = reservas_em_conflito(self.sala, date(2026, 3, 10), time(10, 30), time(11, 30))
        self.assertEqual(conf.count(), 1)

    def test_encostado_nao_conflita(self):
        # 11:00-12:00 encosta em 10:00-11:00 mas não sobrepõe
        conf = reservas_em_conflito(self.sala, date(2026, 3, 10), time(11, 0), time(12, 0))
        self.assertEqual(conf.count(), 0)

    def test_outra_sala_nao_conflita(self):
        conf = reservas_em_conflito(self.outra, date(2026, 3, 10), time(10, 0), time(11, 0))
        self.assertEqual(conf.count(), 0)

    def test_outro_dia_nao_conflita(self):
        conf = reservas_em_conflito(self.sala, date(2026, 3, 11), time(10, 0), time(11, 0))
        self.assertEqual(conf.count(), 0)


class SerieTest(TestCase):
    def setUp(self):
        self.sala = Sala.objects.create(nome='Lab 1')

    def test_serie_sem_conflito_cria_tudo(self):
        datas = gerar_datas('semanal', 1, date(2026, 5, 4), date(2026, 5, 25))
        conflitos = checar_conflitos_serie(self.sala, datas, time(14, 0), time(15, 0))
        self.assertEqual(conflitos, [])
        recorrencia, criadas = criar_serie(
            sala=self.sala, titulo='Aula', responsavel='Prof',
            hora_inicio=time(14, 0), hora_fim=time(15, 0),
            frequencia='semanal', intervalo=1,
            data_inicio=date(2026, 5, 4), data_fim=date(2026, 5, 25))
        self.assertEqual(len(criadas), 4)
        self.assertEqual(recorrencia.reservas.count(), 4)

    def test_serie_com_um_conflito_e_detectada(self):
        # Uma reserva única bloqueia uma das datas da série
        Reserva.objects.create(
            sala=self.sala, titulo='Bloqueio', responsavel='X',
            data=date(2026, 5, 11), hora_inicio=time(14, 30), hora_fim=time(15, 30))
        datas = gerar_datas('semanal', 1, date(2026, 5, 4), date(2026, 5, 25))
        conflitos = checar_conflitos_serie(self.sala, datas, time(14, 0), time(15, 0))
        self.assertEqual(len(conflitos), 1)
        self.assertEqual(conflitos[0][0], date(2026, 5, 11))


class ViewReservaTest(TestCase):
    def setUp(self):
        self.sala = Sala.objects.create(nome='Sala A')

    def test_criar_reserva_unica(self):
        resp = self.client.post(reverse('reservas:reserva_nova'), {
            'sala': self.sala.id, 'titulo': 'Reunião', 'responsavel': 'Ana',
            'data': '2026-06-01', 'hora_inicio': '09:00', 'hora_fim': '10:00',
            'observacoes': '',
        })
        self.assertEqual(Reserva.objects.count(), 1)
        self.assertRedirects(resp, reverse('reservas:reserva_lista'))

    def test_reserva_conflitante_e_rejeitada(self):
        Reserva.objects.create(
            sala=self.sala, titulo='Ocupada', responsavel='Y',
            data=date(2026, 6, 1), hora_inicio=time(9, 0), hora_fim=time(10, 0))
        resp = self.client.post(reverse('reservas:reserva_nova'), {
            'sala': self.sala.id, 'titulo': 'Choque', 'responsavel': 'Ana',
            'data': '2026-06-01', 'hora_inicio': '09:30', 'hora_fim': '10:30',
            'observacoes': '',
        })
        self.assertEqual(resp.status_code, 200)  # re-renderiza com erro
        self.assertEqual(Reserva.objects.count(), 1)  # nada novo salvo
        self.assertContains(resp, 'Conflito de agenda')


class ViewRecorrenciaTest(TestCase):
    def setUp(self):
        self.sala = Sala.objects.create(nome='Sala B')

    def _payload(self, **overrides):
        dados = {
            'sala': self.sala.id, 'titulo': 'Treino', 'responsavel': 'Bruno',
            'hora_inicio': '08:00', 'hora_fim': '09:00',
            'frequencia': 'semanal', 'intervalo': '1',
            'data_inicio': '2026-07-06', 'data_fim': '2026-07-27',
            'observacoes': '',
        }
        dados.update(overrides)
        return dados

    def test_serie_valida_cria_todas(self):
        resp = self.client.post(reverse('reservas:recorrencia_nova'), self._payload())
        self.assertRedirects(resp, reverse('reservas:reserva_lista'))
        self.assertEqual(Reserva.objects.count(), 4)
        self.assertEqual(Recorrencia.objects.count(), 1)

    def test_serie_com_conflito_nao_salva_nada(self):
        # Bloqueia a 2ª ocorrência (13/07)
        Reserva.objects.create(
            sala=self.sala, titulo='Bloqueio', responsavel='Z',
            data=date(2026, 7, 13), hora_inicio=time(8, 30), hora_fim=time(9, 30))
        antes = Reserva.objects.count()
        resp = self.client.post(reverse('reservas:recorrencia_nova'), self._payload())
        self.assertEqual(resp.status_code, 200)
        # tudo ou nada: continua só a reserva de bloqueio, nenhuma da série
        self.assertEqual(Reserva.objects.count(), antes)
        self.assertEqual(Recorrencia.objects.count(), 0)

    def test_excluir_serie_remove_reservas(self):
        self.client.post(reverse('reservas:recorrencia_nova'), self._payload())
        serie = Recorrencia.objects.first()
        self.client.post(reverse('reservas:recorrencia_excluir', args=[serie.id]))
        self.assertEqual(Recorrencia.objects.count(), 0)
        self.assertEqual(Reserva.objects.count(), 0)
