# Manual de Estudo — Sistema de Reserva de Salas (Django puro)

Este manual explica **o projeto inteiro, arquivo por arquivo**, ligando cada
pedaço aos conceitos das Aulas 1–5. Serve como material de estudo: leia junto
com o código aberto no editor.

## Índice

1. Visão geral
2. A arquitetura MVT e o ciclo de uma requisição
3. Mapa de pastas e arquivos
4. Como o projeto foi montado, do zero (passo a passo)
5. Explicação de cada arquivo de código
6. O núcleo a fundo: conflito e recorrência
7. Comandos do `manage.py` (referência)
8. Glossário
9. Exercícios para fixar
10. Mapa do projeto para as Aulas 1–5
11. As duas features obrigatórias do P1

---

## 1. Visão geral

**O que o sistema faz:** cadastra salas e seus recursos (equipamentos), e permite
reservar salas — de forma **única** ou **recorrente** (repetida no tempo) —
sempre **impedindo choque de horário** na mesma sala.

**Requisitos do P1 atendidos:**

- Entidades: **Sala**, **Recurso**, **Reserva**, **Recorrência**.
- Recurso é **equipamento da sala** (relação muitos-para-muitos).
- Reservas recorrentes **diária / semanal / mensal**.
- **Sem conflito de agenda**, em modo **tudo ou nada**: se qualquer ocorrência da
  série colide, nada é gravado.
- **Sem login** (o responsável é um campo de texto).

**A stack:** Django puro (o próprio Django monta o HTML com *templates* — sem
React), banco **PostgreSQL** em produção com **SQLite** como padrão no
desenvolvimento. É a mesma linha das Aulas 3–5.

---

## 2. A arquitetura MVT e o ciclo de uma requisição

O Django organiza o código em **MVT** (Model · View · Template):

- **Model** — os dados (viram tabelas no banco). Arquivo `models.py`.
- **View** — a lógica: recebe a requisição, busca dados, decide o que mostrar.
  Arquivo `views.py`.
- **Template** — a tela: HTML que exibe os dados. Pasta `templates/`.

Toda página segue o mesmo ciclo (Aula 5):

```
Navegador
   │  1. usuário acessa uma URL  (ex.: /reservas/nova/)
   ▼
urls.py  ──2. descobre qual VIEW responde aquela URL──►  views.py
   ▼                                                        │
   │                          3. a view usa o MODEL (ORM)   │
   │                             para ler/gravar no banco   ▼
   │                                                     models.py ──► Banco
   │  4. a view escolhe um TEMPLATE e manda os dados
   ▼
templates/*.html  ──5. HTML pronto──►  volta ao navegador
```

Guarde esta frase: **a URL chama a View, a View usa o Model e devolve um
Template.** Todo o projeto é isso repetido para cada tela.

---

## 3. Mapa de pastas e arquivos

```
reserva-salas/
├── manage.py                 # "controle remoto" do projeto (roda comandos)
├── requirements.txt          # dependências (Django, python-dotenv, psycopg2)
├── .env.example              # modelo das variáveis de ambiente (copie p/ .env)
├── .gitignore                # o que NÃO vai pro Git (.env, db.sqlite3, venv...)
├── README.md                 # como rodar
├── MANUAL.md                 # este manual
│
├── reservasalas/             # o PROJETO (configuração geral)
│   ├── settings.py           # configurações: apps, banco, idioma, segredos
│   ├── urls.py               # roteador principal (inclui as urls do app)
│   ├── wsgi.py / asgi.py     # ponte com o servidor em produção
│   └── __init__.py
│
└── reservas/                 # o APP (o domínio: salas e reservas)
    ├── models.py             # Recurso, Sala, Recorrencia, Reserva
    ├── services.py           # regra de negócio: gerar datas + detectar conflito
    ├── forms.py              # formulários (validação de entrada)
    ├── views.py              # as funções que respondem cada URL
    ├── urls.py               # rotas do app (com name)
    ├── admin.py              # registra os models no Django Admin
    ├── tests.py              # 19 testes automatizados
    ├── migrations/           # histórico de mudanças do banco
    ├── templates/reservas/   # os HTMLs (com herança de template)
    └── static/reservas/      # o CSS
```

**Projeto × App** (Aula 4): o *projeto* (`reservasalas`) é o site inteiro e
guarda as configurações; o *app* (`reservas`) é um módulo que cuida de uma
funcionalidade. Um projeto pode ter vários apps.

---

## 4. Como o projeto foi montado, do zero (passo a passo)

Esta é a mesma sequência das Aulas 4 e 5. Se quiser recriar para estudar, rode na
ordem:

```bash
# 1) Ambiente virtual isolado (Aula 4)
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2) Instalar dependências
pip install django python-dotenv psycopg2-binary

# 3) Criar o PROJETO (o ponto final = "aqui nesta pasta")
django-admin startproject reservasalas .

# 4) Criar o APP
python manage.py startapp reservas

# 5) Registrar o app em reservasalas/settings.py -> INSTALLED_APPS

# 6) Escrever os models (reservas/models.py)

# 7) Levar os models ao banco (Aula 4)
python manage.py makemigrations      # gera o "plano" da mudança
python manage.py migrate             # aplica o plano no banco

# 8) Registrar no Admin (reservas/admin.py) e criar um usuário admin
python manage.py createsuperuser

# 9) Escrever views, urls e templates (Aula 5)

# 10) Rodar o servidor
python manage.py runserver           # http://127.0.0.1:8000/
```

Ordem mental: **ambiente → projeto → app → models → migração → admin →
views/urls/templates → forms.**

---

## 5. Explicação de cada arquivo de código

### 5.1 `reservasalas/settings.py` — as configurações

O "coração" da configuração (Aula 4). Pontos que valem estudar:

```python
from dotenv import load_dotenv
load_dotenv(BASE_DIR / '.env')          # lê variáveis do arquivo .env
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-inseguro-troque-em-producao')
DEBUG = os.getenv('DEBUG', '1') == '1'
```

- **`python-dotenv`**: mantém segredos (senha do banco, SECRET_KEY) **fora do
  código**, num arquivo `.env` que não vai pro Git. É a convenção do professor.
- `os.getenv('X', padrão)`: lê a variável `X`; se não existir, usa o padrão.

```python
INSTALLED_APPS = [ ... 'reservas' ]     # sem isto, o Django ignora seu app
```

O banco cai para SQLite quando você não define `DB_NAME` — ótimo para desenvolver
sem instalar PostgreSQL:

```python
if os.getenv('DB_NAME'):
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', ...}}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3',
                             'NAME': BASE_DIR / 'db.sqlite3'}}
```

Outros ajustes: `LANGUAGE_CODE = 'pt-br'`, `TIME_ZONE = 'America/Sao_Paulo'`.

### 5.2 `reservasalas/urls.py` — o roteador principal

```python
urlpatterns = [
    path('admin/', admin.site.urls),        # o painel /admin
    path('', include('reservas.urls')),     # delega tudo ao app "reservas"
]
```

`include()` (Aula 5) "pluga" as rotas do app no projeto. Assim o projeto não vira
um arquivo gigante: cada app tem seu próprio `urls.py`.

### 5.3 `reservas/models.py` — os dados

Cada classe vira uma tabela; cada atributo, uma coluna (Aula 4).

```python
class Recurso(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)

    class Meta:
        ordering = ['nome']              # listagens já saem em ordem alfabética

    def __str__(self):                   # como o objeto aparece no Admin/shell
        return self.nome
```

- `CharField` = texto curto (precisa de `max_length`); `TextField` = texto longo.
- `unique=True` = não deixa dois recursos com o mesmo nome.
- `blank=True` = o campo pode ficar vazio nos formulários.
- `__str__` = define o "nome de exibição" do objeto (Aula 4).

```python
class Sala(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    capacidade = models.IntegerField(default=0)
    localizacao = models.CharField(max_length=200, blank=True)
    recursos = models.ManyToManyField(Recurso, blank=True, related_name='salas')
```

- **`ManyToManyField`**: uma sala tem vários recursos e um recurso está em várias
  salas. É a decisão "recurso = equipamento da sala".
- `related_name='salas'`: permite ir do recurso para as salas (`recurso.salas`).

```python
class Recorrencia(models.Model):
    DIARIA = 'diaria'; SEMANAL = 'semanal'; MENSAL = 'mensal'
    FREQUENCIAS = [(DIARIA, 'Diária'), (SEMANAL, 'Semanal'), (MENSAL, 'Mensal')]

    frequencia = models.CharField(max_length=10, choices=FREQUENCIAS)
    intervalo = models.IntegerField(default=1)   # "a cada N"
    data_inicio = models.DateField()
    data_fim = models.DateField()
```

- `choices=` limita o campo a valores pré-definidos (aparece como `<select>`).
- Guardamos aqui só a **regra** da série. As ocorrências ficam em `Reserva`.

```python
class Reserva(models.Model):
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='reservas')
    titulo = models.CharField(max_length=200)
    responsavel = models.CharField(max_length=120)   # "sem login": texto simples
    data = models.DateField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    observacoes = models.TextField(blank=True)
    recorrencia = models.ForeignKey(Recorrencia, on_delete=models.CASCADE,
                                    null=True, blank=True, related_name='reservas')

    class Meta:
        ordering = ['data', 'hora_inicio']

    @property
    def recorrente(self):
        return self.recorrencia_id is not None
```

- **`ForeignKey`** = "pertence a" (uma reserva pertence a uma sala). É o lado
  "muitos" de um-para-muitos.
- `on_delete=models.CASCADE`: se a sala for apagada, suas reservas somem junto.
  O mesmo para a série: apagar a `Recorrencia` apaga as reservas dela.
- `recorrencia` é **`null=True`**: reserva única não tem série (fica vazio).
- **Decisão de design importante:** tanto a reserva única quanto cada ocorrência
  da série são a **mesma** tabela `Reserva`. Isso deixa a checagem de conflito
  **igual** para as duas — é só olhar a tabela `Reserva`.
- `@property recorrente`: um atalho de leitura; `reserva.recorrente` devolve
  `True/False`. Usado no template para mostrar a etiqueta "série".

### 5.4 `reservas/services.py` — a regra de negócio (o coração)

Colocamos a lógica pesada aqui, **fora das views e dos templates**, para poder
**testar isolado** e reaproveitar. É o arquivo mais importante para estudar.

**(a) Gerar as datas da série:**

```python
def gerar_datas(frequencia, intervalo, data_inicio, data_fim):
    intervalo = max(1, int(intervalo))
    datas = []
    if data_fim < data_inicio:
        return datas                       # período inválido → nada
    if frequencia == Recorrencia.DIARIA:
        atual = data_inicio
        while atual <= data_fim and len(datas) < MAX_OCORRENCIAS:
            datas.append(atual)
            atual = atual + timedelta(days=intervalo)
    elif frequencia == Recorrencia.SEMANAL:
        ...   timedelta(weeks=intervalo)
    elif frequencia == Recorrencia.MENSAL:
        ...   _somar_meses(data_inicio, passo * intervalo)
    return datas
```

- `timedelta` soma dias/semanas de forma segura (vira o mês/ano sozinho).
- `MAX_OCORRENCIAS = 366` é uma **trava de segurança** contra séries absurdas.

**(b) Somar meses ancorando no dia certo:**

```python
def _somar_meses(base, meses):
    total = (base.month - 1) + meses
    ano = base.year + total // 12
    mes = total % 12 + 1
    dia = min(base.day, _ultimo_dia_do_mes(ano, mes))   # dia 31 -> 28/30
    return date(ano, mes, dia)
```

Detalhe fino: se a série começa dia 31, meses curtos (fev, abr...) não têm dia
31; usamos o **último dia** desses meses, sem "escorregar" o dia nas próximas
repetições (sempre ancoramos no dia original). Isso é testado.

**(c) Detectar conflito (a parte mais importante):**

```python
def reservas_em_conflito(sala, data, hora_inicio, hora_fim, excluir_ids=None):
    qs = Reserva.objects.filter(sala=sala, data=data)
    return qs.filter(hora_inicio__lt=hora_fim, hora_fim__gt=hora_inicio)
```

Duas reservas conflitam quando são na **mesma sala**, **mesmo dia**, e os
horários **se sobrepõem**. A regra de sobreposição está detalhada na seção 6.
`__lt` = "menor que", `__gt` = "maior que" (filtros do ORM).

**(d) Checar a série inteira e criar tudo:**

```python
def checar_conflitos_serie(sala, datas, hora_inicio, hora_fim):
    conflitos = []
    for d in datas:
        for existente in reservas_em_conflito(sala, d, hora_inicio, hora_fim):
            conflitos.append((d, existente))
    return conflitos

@transaction.atomic
def criar_serie(...):
    recorrencia = Recorrencia.objects.create(...)
    Reserva.objects.bulk_create([Reserva(...) for d in datas])
    return recorrencia, datas
```

- `@transaction.atomic`: ou grava **tudo**, ou **nada** (se der erro no meio, o
  banco volta atrás). É o que garante o "tudo ou nada".
- `bulk_create`: insere todas as reservas de uma vez (mais rápido que uma a uma).

### 5.5 `reservas/forms.py` — os formulários

Formulários validam a entrada do usuário (Aula 5). Usamos dois tipos:

**`ModelForm`** — gera os campos automaticamente a partir de um model:

```python
class SalaForm(forms.ModelForm):
    class Meta:
        model = Sala
        fields = ['nome', 'capacidade', 'localizacao', 'recursos']
        widgets = {'recursos': forms.CheckboxSelectMultiple}
```

Você só diz o model e os campos; os tipos, rótulos e validação vêm prontos.
`widgets` troca a aparência de um campo (aqui, caixas de seleção).

**Validação de conflito na reserva única** — feita no `clean()`, então o
`is_valid()` já barra:

```python
class ReservaForm(forms.ModelForm):
    ...
    def clean(self):
        cleaned = super().clean()
        ...
        if inicio and fim and inicio >= fim:
            self.add_error('hora_fim', 'A hora de fim deve ser depois da de início.')
        elif sala and data and inicio and fim:
            conflito = reservas_em_conflito(sala, data, inicio, fim).first()
            if conflito:
                raise forms.ValidationError('Conflito de agenda: ...')
        return cleaned
```

- `clean()` roda quando você chama `form.is_valid()`; é onde entram regras que
  cruzam vários campos.
- `add_error(campo, msg)` prende o erro num campo; `ValidationError` é erro geral
  do formulário.

**`forms.Form` (não-Model)** para a série, porque ela mistura dados da reserva +
regra de repetição (campos de dois models diferentes):

```python
class RecorrenciaForm(forms.Form):
    sala = forms.ModelChoiceField(queryset=Sala.objects.all())
    titulo = forms.CharField(max_length=200)
    ...
    frequencia = forms.ChoiceField(choices=Recorrencia.FREQUENCIAS)
    intervalo = forms.IntegerField(min_value=1, initial=1)
    data_inicio = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    data_fim = forms.DateField(...)
```

A validação de conflito da **série** não fica aqui (envolve várias datas) — fica
na view, usando o `services.py`.

### 5.6 `reservas/views.py` — as funções que respondem as URLs

Usamos **views de função** (o estilo do professor). O padrão que se repete:

```python
def sala_form(request, pk=None):
    instancia = get_object_or_404(Sala, pk=pk) if pk else None
    if request.method == 'POST':                 # enviou o formulário
        form = SalaForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sala salva com sucesso.')
            return redirect('reservas:sala_lista')
    else:                                         # só abriu a página
        form = SalaForm(instance=instancia)
    return render(request, 'reservas/sala_form.html', {'form': form, ...})
```

Guarde este padrão **GET mostra / POST salva**:
- `GET` (abrir): cria um formulário vazio (ou preenchido, se estiver editando).
- `POST` (enviar): valida; se ok, salva e **redireciona**; se não, cai no
  `render` final e mostra os erros.
- `render(request, template, contexto)` monta o HTML (Aula 5).
- `redirect('reservas:sala_lista')` manda o navegador para outra rota (evita
  reenviar o formulário ao dar F5).
- `messages` mostra o aviso verde/vermelho no topo (configurado no `base.html`).
- O mesmo `sala_form` serve para **criar e editar** (se vier `pk`, edita).

**A view do núcleo — reserva recorrente (tudo ou nada):**

```python
def recorrencia_nova(request):
    if request.method == 'POST':
        form = RecorrenciaForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            datas = gerar_datas(d['frequencia'], d['intervalo'],
                                d['data_inicio'], d['data_fim'])
            conflitos = checar_conflitos_serie(d['sala'], datas,
                                               d['hora_inicio'], d['hora_fim'])
            if conflitos:
                # não grava NADA; lista cada data em conflito
                for data_conf, existente in conflitos:
                    messages.warning(request, f'{data_conf:%d/%m/%Y}: choca com ...')
            else:
                criar_serie(...)                 # grava tudo, atômico
                return redirect('reservas:reserva_lista')
    ...
```

Repare: a view **orquestra** (chama o `services.py`), mas a regra pesada mora no
service. Isso é "lógica na view, não no template", e "cada coisa no seu lugar".

### 5.7 `reservas/urls.py` — as rotas do app

```python
app_name = 'reservas'
urlpatterns = [
    path('', views.reserva_lista, name='reserva_lista'),   # a agenda é a home
    path('salas/', views.sala_lista, name='sala_lista'),
    path('salas/<int:pk>/editar/', views.sala_form, name='sala_editar'),
    ...
]
```

- `path('rota/', view, name='apelido')`: liga um endereço a uma view.
- **`name=`** deixa você referenciar a rota pelo apelido nos templates
  (`{% url 'reservas:sala_lista' %}`) e nas views (`redirect('reservas:...')`).
  Se a URL mudar, nada quebra.
- `<int:pk>` captura um número da URL e entrega para a view como `pk`.
- `app_name` cria o "namespace" (por isso escrevemos `reservas:sala_lista`).

### 5.8 `reservas/admin.py` — o painel administrativo grátis

```python
admin.site.register(Recurso)
admin.site.register(Sala)
admin.site.register(Recorrencia)
admin.site.register(Reserva)
```

Registrar um model faz o Django gerar, de graça, uma tela completa de CRUD em
`/admin` (Aula 4). Ótimo para popular dados enquanto as telas próprias evoluem.

### 5.9 Templates (`reservas/templates/reservas/`)

HTML com a **Django Template Language** (Aula 5): `{{ }}` mostra valor, `{% %}`
executa lógica.

**Herança (`base.html`)** — o layout comum fica num arquivo só:

```html
<!-- base.html -->
<header>... menu ...</header>
{% if messages %}{% for m in messages %}<div>{{ m }}</div>{% endfor %}{% endif %}
{% block conteudo %}{% endblock %}   <!-- "buraco" que cada página preenche -->
```

```html
<!-- reserva_lista.html -->
{% extends 'reservas/base.html' %}
{% block conteudo %}
  {% for r in reservas %}
      <tr><td>{{ r.data|date:"d/m/Y" }}</td><td>{{ r.titulo }}</td></tr>
  {% empty %}
      <tr><td>Nenhuma reserva cadastrada.</td></tr>
  {% endfor %}
{% endblock %}
```

- `{% extends %}` + `{% block %}`: cada página só escreve o "miolo"; cabeçalho e
  rodapé vêm do `base.html` (DRY — não repetir código).
- `{% for %} ... {% empty %}`: repete linhas; o `empty` cobre a lista vazia.
- `|date:"d/m/Y"` é um **filtro** que formata a data.

**Formulário (`reserva_form.html`)**:

```html
<form method="post">
    {% csrf_token %}          <!-- proteção obrigatória contra ataque CSRF -->
    {{ form.as_p }}           <!-- renderiza todos os campos, um por parágrafo -->
    <button>Salvar</button>
</form>
```

Sem `{% csrf_token %}` o Django **recusa** o envio (segurança nativa, Aula 3/5).

`{% load static %}` + `{% static 'reservas/estilo.css' %}` no `base.html` geram o
caminho certo do CSS na pasta `static/`.

### 5.10 `reservas/static/reservas/estilo.css`

CSS puro, com uma paleta simples (vinho/dourado). Nada de framework. Layout
responsivo básico com `flex`/`grid`.

### 5.11 `reservas/tests.py` — 19 testes automatizados

Rodam com `python manage.py test`. Cobrem exatamente o núcleo:

- **`GerarDatasTest`** — datas diárias/semanais/mensais, "a cada N", âncora do
  dia 31, período invertido, e a trava de 366.
- **`ConflitoTest`** — sobreposição detectada; horários encostados **não**
  conflitam; outra sala/outro dia não conflitam.
- **`SerieTest`** — série sem conflito cria tudo; série com 1 conflito é detectada.
- **`ViewReservaTest` / `ViewRecorrenciaTest`** — os fluxos completos pelas views,
  inclusive "série com conflito **não salva nada**" e "excluir série apaga as
  reservas".

Estudar os testes é a forma mais rápida de entender o comportamento esperado.

---

## 6. O núcleo a fundo: conflito e recorrência

### 6.1 Detecção de conflito (sobreposição de intervalos)

Dois intervalos de tempo **[inícioA, fimA)** e **[inícioB, fimB)** se sobrepõem
quando:

```
inícioA < fimB   E   inícioB < fimA
```

No código isso é o filtro `hora_inicio__lt=hora_fim, hora_fim__gt=hora_inicio`
(comparando o novo horário com cada reserva existente). Exemplos, para uma
reserva existente das **10:00–11:00**:

```
Novo 10:30–11:30  → 10:30<11:00 e 10:00<11:30 → CONFLITA
Novo 09:30–10:30  → 09:30<11:00 e 10:00<10:30 → CONFLITA
Novo 11:00–12:00  → 11:00<11:00 é FALSO       → NÃO conflita (encostado)
Novo 08:00–09:00  → 10:00<09:00 é FALSO       → NÃO conflita
```

Usamos `<` (estrito), então **11:00–12:00 logo após 10:00–11:00 é permitido** —
encostar não é sobrepor. E o filtro sempre restringe à **mesma sala e mesma
data**, então salas diferentes podem ter reservas no mesmo horário.

### 6.2 Geração de recorrência

`gerar_datas` transforma a regra em uma lista de datas concretas:

- **Diária:** soma `intervalo` dias a cada passo.
- **Semanal:** soma `intervalo` semanas.
- **Mensal:** soma `intervalo` meses ancorando no dia original (ver 5.4).

Cada data vira uma `Reserva` com o mesmo horário. Como as datas são diferentes,
as ocorrências da série **nunca conflitam entre si** — só precisamos comparar com
o que já existe no banco.

### 6.3 Tudo ou nada

Fluxo completo da série:

```
1. gerar_datas(...)            → todas as datas da regra
2. checar_conflitos_serie(...) → lista de (data, reserva_existente) em choque
3a. se a lista tem algo   → NÃO grava nada; mostra as datas em conflito
3b. se a lista está vazia → criar_serie(...) grava tudo em transação atômica
```

O `@transaction.atomic` no `criar_serie` é a rede de segurança: se algo falhasse
no meio da gravação, o banco desfaria tudo, nunca deixando uma série pela metade.

---

## 7. Comandos do `manage.py` (referência)

| Comando | O que faz |
|---|---|
| `runserver` | Sobe o servidor de desenvolvimento (127.0.0.1:8000) |
| `startapp <nome>` | Cria um novo app |
| `makemigrations` | Gera o plano de mudança a partir dos models |
| `migrate` | Aplica as migrações no banco |
| `createsuperuser` | Cria o usuário admin (para o `/admin`) |
| `shell` | Abre um Python já conectado ao projeto (testar o ORM) |
| `test` | Roda os testes automatizados |

**Regra de ouro (Aula 4):** mudou o model? Rode `makemigrations` e depois
`migrate`. Esquecer isso é o erro nº 1 de quem começa.

---

## 8. Glossário

- **MVT** — Model (dados), View (lógica), Template (tela).
- **ORM** — traduz classes Python em tabelas/consultas SQL, sem escrever SQL.
- **Model** — classe Python que representa uma tabela.
- **Migração** — plano versionado que leva mudanças dos models para o banco.
- **View** — função que recebe a requisição e devolve uma resposta.
- **Template / DTL** — HTML com `{{ valor }}` e `{% lógica %}`.
- **ModelForm** — formulário gerado a partir de um model.
- **CSRF** — ataque que o `{% csrf_token %}` bloqueia em formulários POST.
- **ForeignKey** — relação "pertence a" (um-para-muitos).
- **ManyToMany** — relação "vários-para-vários" (sala ↔ recursos).
- **QuerySet** — a "consulta" do ORM (`Reserva.objects.filter(...)`), preguiçosa
  (só bate no banco quando é usada).
- **Migração atômica / `transaction.atomic`** — bloco "tudo ou nada" no banco.

---

## 9. Exercícios para fixar

1. **Model:** adicione um campo `cor` (CharField) em `Sala` e faça o ciclo
   `makemigrations` → `migrate`. Confira a coluna nova no Admin.
2. **ORM (shell):** rode `python manage.py shell` e crie duas reservas na mesma
   sala/horário via `Reserva.objects.create(...)`. Depois teste
   `reservas_em_conflito(...)` e veja o conflito aparecer.
3. **View/URL/Template:** crie uma página `/salas/<pk>/` que mostre os detalhes de
   uma sala e a lista de reservas dela (`sala.reservas.all`). Você vai mexer em
   `views.py`, `urls.py` e criar um template — o ciclo completo da Aula 5.
4. **Regra de negócio:** implemente a frequência "quinzenal" (a cada 2 semanas)
   sem criar código novo — descubra por que `intervalo=2` + semanal já resolve.
5. **Teste:** escreva um teste que garanta que reservar 11:00–12:00 logo após
   10:00–11:00 na mesma sala **é permitido**.

---

## 10. Mapa do projeto para as Aulas 1–5

| Aula | Conceito | Onde aparece no projeto |
|---|---|---|
| 1 | Cliente-servidor, HTTP, verbos, ciclo da requisição | GET mostra / POST salva nas views |
| 2 | HTML, CSS, DOM, MPA, templates do Django | pasta `templates/` + `static/estilo.css` |
| 3 | Python, Django, MVT, ORM, PostgreSQL | `models.py`, `services.py`, `settings.py` |
| 4 | Projeto/app, models, migrações, Admin, venv, .env | `models.py`, `migrations/`, `admin.py`, `settings.py` |
| 5 | Views, URLs, templates, herança, forms, CSRF | `views.py`, `urls.py`, `forms.py`, templates |

---

## 11. As duas features obrigatórias do P1

Além do CRUD, a entrega P1 exige duas features **integradas** ao projeto (não como
telas soltas).

### 11.1 Feature 1 — Busca e filtro na listagem de salas

Aplicada à listagem de **Salas** (`sala_lista`). A view lê os parâmetros da URL e
encadeia filtros opcionais — todos combinam com "E":

```python
def sala_lista(request):
    salas = Sala.objects.prefetch_related('recursos')
    q = request.GET.get('q', '').strip()
    recurso_id = request.GET.get('recurso', '')
    capacidade = request.GET.get('capacidade', '')
    if q:
        salas = salas.filter(nome__icontains=q)              # busca textual
    if recurso_id:
        salas = salas.filter(recursos__id=recurso_id)        # filtro por recurso
    if capacidade.isdigit():
        salas = salas.filter(capacidade__gte=int(capacidade))  # filtro por capacidade
    return render(request, 'reservas/sala_lista.html',
                  {'salas': salas.distinct(), 'recursos': Recurso.objects.all()})
```

- `request.GET.get('q')` lê o parâmetro `?q=...` da URL.
- `nome__icontains` = "contém, ignorando maiúsculas/minúsculas".
- Cada `if` só aplica o filtro se o parâmetro veio preenchido → funcionam juntos
  ou separados.
- `.distinct()` evita salas repetidas quando o join do M2M (recursos) casa mais de
  uma vez.

No template, os campos são reabastecidos com `request.GET` (para não "esquecer" o
que foi digitado) e a lista vazia mostra mensagem clara:

```html
<input type="text" name="q" value="{{ request.GET.q }}">
...
{% for sala in salas %} ... {% empty %}
    <tr><td colspan="5">Nenhuma sala encontrada com esses filtros.</td></tr>
{% endfor %}
```

### 11.2 Feature 2 — Validação customizada no ModelForm

No `ReservaForm` (um `ModelForm`), o método `clean()` aplica uma regra de domínio
além do "campo obrigatório" que o Django já faz sozinho:

```python
def clean(self):
    cleaned = super().clean()
    inicio = cleaned.get('hora_inicio')
    fim = cleaned.get('hora_fim')
    if inicio and fim and inicio >= fim:
        self.add_error('hora_fim', 'A hora de fim deve ser depois da hora de início.')
    ...  # + checagem de conflito com raise forms.ValidationError(...)
    return cleaned
```

- `clean()` roda dentro do `form.is_valid()`.
- `cleaned.get('...')` lê os valores já validados, campo a campo.
- `add_error(campo, msg)` prende a mensagem no campo `hora_fim` — aparece sozinha
  no template (`{{ form.as_p }}`).

### 11.3 O que foi escolhido e por quê (relatório)

- **Feature 1** — buscar por **nome da sala** (o campo textual mais útil para
  achar uma sala) e filtrar por **recurso** e **capacidade mínima**, porque é
  assim que alguém procura uma sala de verdade: "quero uma com projetor para 40
  pessoas". Sem a feature, seria preciso ler a lista inteira na mão.
- **Feature 2** — "término depois do início" impede reservas logicamente
  impossíveis (fim antes do começo), que passariam pela validação padrão do
  Django e quebrariam a detecção de conflito.

Cada feature deve ir em um **commit próprio** no Git, por exemplo:
`feat: busca e filtro na listagem de salas` e
`feat: validação de horário no formulário de reserva`.

---

Bons estudos. Sugestão de leitura: comece pelo `models.py` (o que são os dados),
depois `services.py` (a regra), depois siga uma tela do começo ao fim
(`urls.py` → `views.py` → `templates/`).
