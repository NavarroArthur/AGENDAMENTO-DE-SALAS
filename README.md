# Reserva de Salas

Sistema de reserva de salas em **Django puro** (MPA + templates), feito para a
entrega **P1 (MVP funcional)** da disciplina *Laboratório de Programação Full Stack*.

O núcleo do sistema são as **reservas recorrentes sem conflito de agenda**: você
cria uma série (diária, semanal ou mensal) e o sistema só grava se **nenhuma**
ocorrência colidir com uma reserva existente na mesma sala (regra *tudo ou nada*).

---

## Entidades

| Entidade      | Papel |
|---------------|-------|
| **Recurso**   | Equipamento de sala (projetor, TV, ar-condicionado...). |
| **Sala**      | Sala reservável; tem vários recursos (M2M). Dá para filtrar salas por recurso. |
| **Reserva**   | Uma ocorrência: sala, título, responsável (texto), data, horário. Pode ser única ou pertencer a uma série. |
| **Recorrência** | A regra da série (frequência, intervalo "a cada N", início e fim). Gera as Reservas. |

Cada ocorrência de uma série é uma `Reserva` ligada à `Recorrencia` por FK. Isso
deixa a detecção de conflito **uniforme**: única ou recorrente, tudo vira `Reserva`
e a checagem de choque é a mesma.

---

## Como rodar

Pré-requisito: Python 3.11+ instalado.

```bash
# 1. ambiente virtual
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. dependências
pip install -r requirements.txt

# 3. variáveis de ambiente (sem isso ele já roda em SQLite)
cp .env.example .env            # Windows: copy .env.example .env

# 4. banco de dados
python manage.py migrate

# 5. usuário admin (para o /admin)
python manage.py createsuperuser

# 6. subir o servidor
python manage.py runserver
```

Acesse:

- **Aplicação:** http://127.0.0.1:8000/
- **Admin do Django:** http://127.0.0.1:8000/admin/

Sem `DB_NAME` no `.env`, o projeto usa **SQLite** automaticamente. Para PostgreSQL,
preencha as variáveis `DB_*` no `.env` (precisa do `psycopg2-binary`, já no
requirements) e rode `migrate` de novo.

---

## Como funciona o núcleo

**Detecção de conflito** (`reservas/services.py` → `reservas_em_conflito`): duas
reservas colidem quando são na **mesma sala**, no **mesmo dia**, e os horários se
sobrepõem — `inicio_existente < fim_novo E inicio_novo < fim_existente`. Horários
encostados (10–11 e 11–12) **não** conflitam.

**Recorrência** (`gerar_datas`): expande a regra em datas.

- *Diária* — a cada N dias.
- *Semanal* — a cada N semanas.
- *Mensal* — a cada N meses, ancorando no dia original (dia 31 vira o último dia
  dos meses curtos, sem "escorregar" o dia).
- Trava de segurança de 366 ocorrências.

**Tudo ou nada** (`recorrencia_nova` + `criar_serie`): gera todas as datas, checa
conflito em cada uma; se **qualquer** uma colidir, **nada** é gravado e a tela
lista exatamente as datas/horários em choque. Se estiver tudo livre, a série
inteira é criada dentro de uma transação atômica.

---

## Estrutura

```
reserva-salas/
├── manage.py
├── requirements.txt
├── .env.example
├── reservasalas/            # configurações do projeto
│   ├── settings.py          # dotenv + PostgreSQL/SQLite
│   └── urls.py              # inclui reservas.urls
└── reservas/                # app do domínio
    ├── models.py            # Recurso, Sala, Recorrencia, Reserva
    ├── services.py          # geração de datas + conflito (regra de negócio)
    ├── forms.py             # ModelForm + form da série
    ├── views.py             # views de função (CRUD + agenda)
    ├── urls.py              # rotas com name
    ├── admin.py             # 4 models registrados
    ├── tests.py             # 19 testes do núcleo
    ├── templates/reservas/  # base.html + páginas (herança de template)
    └── static/reservas/     # estilo.css
```

## Testes

```bash
python manage.py test
```

19 testes cobrindo geração de datas (diária/semanal/mensal, intervalo, âncora do
dia 31), detecção de conflito (sobreposição, encostado, outra sala, outro dia),
e o fluxo *tudo ou nada* (série válida cria tudo; série com um conflito não grava
nada).

---

## O que está pronto no P1

- CRUD completo de **Salas** e **Recursos** (front-end + Admin), com filtro de
  salas por recurso.
- **Reserva única** com bloqueio de conflito.
- **Reserva recorrente** (diária/semanal/mensal) com validação *tudo ou nada*.
- Agenda (página inicial) listando todas as reservas; exclusão de reserva avulsa
  e de série inteira.
- **Feature 1 — busca e filtro** na listagem de salas: busca por nome
  (`icontains`) + filtros por recurso e capacidade mínima, combináveis.
- **Feature 2 — validação customizada** no `ReservaForm`: término depois do
  início (além do bloqueio de conflito de agenda).
- Todos os models no Django Admin.

> Versão enxuta: sem painel/dashboard, página de detalhe, filtros extras na
> agenda nem campos/configs além do necessário — só o que o P1 pede.

## Relatório P1 — Features obrigatórias

**Feature 1 (busca e filtro)** foi aplicada à listagem de **Salas**. A busca é por
**nome** (`nome__icontains`, ignora maiúsculas/minúsculas) e há filtros por
**recurso** e por **capacidade mínima**, todos opcionais e combináveis (lidos de
`request.GET` e encadeados com `.filter()`). Escolhi esses campos porque é assim
que se procura uma sala na prática ("uma sala com projetor para 40 pessoas"); sem
a feature, o usuário precisaria varrer a lista inteira.

**Feature 2 (validação customizada)** está no `ReservaForm` (`ModelForm`), no
método `clean()`: **o horário de término precisa ser depois do início**. Escolhi
essa regra porque um horário invertido é logicamente impossível e passaria pela
validação padrão do Django, quebrando a lógica de conflito. O mesmo `clean()`
ainda bloqueia conflito de agenda.

Sugestão de commits (um por feature): `feat: busca e filtro na listagem de salas`
e `feat: validação de horário no ReservaForm`.

## Roadmap sugerido para o P2

- Autenticação e permissões (reserva vinculada ao usuário; atendente/gerente).
- Editar reserva/série; página de detalhe; filtros na agenda; "pular ocorrências em conflito".
- Camada DRF (`/api/`) expondo os mesmos models.
- Testes de borda, segurança (CSRF já ativo), deploy.
