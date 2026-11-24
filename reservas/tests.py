from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Organizacao, Perfil
from .models import Recorrencia, Reserva, Recurso, Sala
from .services import (
    checar_conflitos_serie,
    criar_serie,
    gerar_datas,
    reservas_em_conflito,
)


def _preparar_organizacao_e_login(testcase, nome='Organização de teste'):
    organizacao = Organizacao.objects.create(nome=nome)
    usuario = get_user_model().objects.create_user(
        username='admin_teste',
        password='senha-de-teste',
    )
    Perfil.objects.create(
        usuario=usuario,
        organizacao=organizacao,
        papel=Perfil.ADMIN,
    )
    testcase.client.force_login(usuario)
    return organizacao, usuario


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
        self.organizacao, _ = _preparar_organizacao_e_login(self)
        self.sala = Sala.objects.create(nome='Auditório', organizacao=self.organizacao)
        self.outra = Sala.objects.create(nome='Sala 2', organizacao=self.organizacao)
        Reserva.objects.create(
            organizacao=self.organizacao,
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
        self.organizacao, _ = _preparar_organizacao_e_login(self)
        self.sala = Sala.objects.create(nome='Lab 1', organizacao=self.organizacao)

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
            organizacao=self.organizacao,
            sala=self.sala, titulo='Bloqueio', responsavel='X',
            data=date(2026, 5, 11), hora_inicio=time(14, 30), hora_fim=time(15, 30))
        datas = gerar_datas('semanal', 1, date(2026, 5, 4), date(2026, 5, 25))
        conflitos = checar_conflitos_serie(self.sala, datas, time(14, 0), time(15, 0))
        self.assertEqual(len(conflitos), 1)
        self.assertEqual(conflitos[0][0], date(2026, 5, 11))


class ViewReservaTest(TestCase):
    def setUp(self):
        self.organizacao, self.usuario = _preparar_organizacao_e_login(self)
        self.sala = Sala.objects.create(nome='Sala A', organizacao=self.organizacao)

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
            organizacao=self.organizacao,
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
        self.organizacao, self.usuario = _preparar_organizacao_e_login(self)
        self.sala = Sala.objects.create(nome='Sala B', organizacao=self.organizacao)

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
            organizacao=self.organizacao,
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


# --------------------------------------------------------------------------- #
# Feature 1 do P1: busca e filtro na listagem de salas                        #
# --------------------------------------------------------------------------- #
class BuscaFiltroSalasTest(TestCase):
    def setUp(self):
        self.organizacao, _ = _preparar_organizacao_e_login(self)
        self.projetor = Recurso.objects.create(nome='Projetor', organizacao=self.organizacao)
        self.tv = Recurso.objects.create(nome='TV', organizacao=self.organizacao)
        self.auditorio = Sala.objects.create(
            nome='Auditório Central', capacidade=100, organizacao=self.organizacao
        )
        self.auditorio.recursos.add(self.projetor)
        self.pequena = Sala.objects.create(
            nome='Sala Pequena', capacidade=10, organizacao=self.organizacao
        )
        self.pequena.recursos.add(self.tv)

    def test_busca_por_nome_icontains(self):
        # 'audit' (minúsculo) deve achar 'Auditório Central' (não é case-sensitive)
        r = self.client.get(reverse('reservas:sala_lista'), {'q': 'audit'})
        self.assertContains(r, 'Auditório Central')
        self.assertNotContains(r, 'Sala Pequena')

    def test_filtro_por_recurso(self):
        r = self.client.get(reverse('reservas:sala_lista'), {'recurso': self.tv.id})
        self.assertContains(r, 'Sala Pequena')
        self.assertNotContains(r, 'Auditório Central')

    def test_filtro_por_capacidade_minima(self):
        r = self.client.get(reverse('reservas:sala_lista'), {'capacidade': '50'})
        self.assertContains(r, 'Auditório Central')
        self.assertNotContains(r, 'Sala Pequena')

    def test_busca_e_filtro_combinados(self):
        # nome contém 'sala' E tem o recurso TV -> só a Sala Pequena
        r = self.client.get(reverse('reservas:sala_lista'),
                            {'q': 'sala', 'recurso': self.tv.id})
        self.assertContains(r, 'Sala Pequena')
        self.assertNotContains(r, 'Auditório Central')

    def test_sem_resultado_mostra_mensagem(self):
        r = self.client.get(reverse('reservas:sala_lista'), {'q': 'inexistente'})
        self.assertContains(r, 'Nenhuma sala encontrada')

    def test_busca_permanece_no_campo(self):
        r = self.client.get(reverse('reservas:sala_lista'), {'q': 'audit'})
        self.assertContains(r, 'value="audit"')


# --------------------------------------------------------------------------- #
# Feature 2 do P1: validação customizada no ModelForm                         #
# --------------------------------------------------------------------------- #
class ValidacaoHorarioReservaTest(TestCase):
    def setUp(self):
        self.organizacao, _ = _preparar_organizacao_e_login(self)
        self.sala = Sala.objects.create(nome='Sala X', organizacao=self.organizacao)

    def _dados(self, inicio, fim):
        return {'sala': self.sala.id, 'titulo': 'Reunião', 'responsavel': 'Ana',
                'data': '2026-10-01', 'hora_inicio': inicio, 'hora_fim': fim,
                'observacoes': ''}

    def test_fim_antes_do_inicio_e_rejeitado(self):
        from .forms import ReservaForm
        form = ReservaForm(data=self._dados('11:00', '10:00'), organizacao=self.organizacao)
        self.assertFalse(form.is_valid())
        self.assertIn('hora_fim', form.errors)

    def test_horario_valido_passa(self):
        from .forms import ReservaForm
        form = ReservaForm(data=self._dados('10:00', '11:00'), organizacao=self.organizacao)
        self.assertTrue(form.is_valid())
