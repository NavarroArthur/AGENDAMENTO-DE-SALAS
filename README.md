# Reserva de Salas

Aplicação web de agendamento de salas em Django puro, com templates server-side.
Esta versão evolui o MVP da P1 para uma aplicação multi-organização, com login,
papéis, API REST e dashboard.

## Funcionalidades

- Salas e recursos separados por organização.
- Busca de salas por nome, recurso e capacidade mínima.
- Reservas avulsas e recorrentes, com bloqueio de conflitos de horário.
- Login por sessão do Django e papéis de administrador e operador.
- Isolamento de dados em todas as telas e endpoints por organização.
- API REST autenticada para salas, recursos e reservas.
- Dashboard com indicadores, período, gráficos e exportação CSV para administradores.
- Django Admin com escopo por organização; superusuários gerenciam as organizações.

## Como rodar localmente

Pré-requisitos: Python 3.11+.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite `.env` e defina uma `SECRET_KEY` própria. Para desenvolvimento local,
`DEBUG=1` e os hosts do exemplo permitem abrir o servidor em `127.0.0.1`.

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py configurar_organizacao --nome "Minha organização" --usuario admin
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/`. O comando `configurar_organizacao` reaproveita a
organização padrão criada pela migração, para que os registros da P1 fiquem
visíveis ao primeiro administrador. Em um banco novo, ele renomeia essa
organização para o nome informado.

Para adicionar usuários, entre em `/admin/`, crie a conta e depois um `Perfil`
associando usuário, organização e papel. Só superusuários podem criar
organizações e perfis pelo Admin. Membros usam as telas da aplicação em `/`.

Sem `DB_NAME`, o projeto usa SQLite. Para PostgreSQL, preencha `DB_NAME`,
`DB_USER`, `DB_PASSWORD`, `DB_HOST` e `DB_PORT` no ambiente. Antes de migrar um
banco usado, faça um backup. A migração P2 atribui os dados legados à organização
padrão e deixa `criado_por` vazio para as reservas antigas.

## Papéis

| Ação | Administrador | Operador |
|---|---:|---:|
| Ver salas, recursos e agenda da organização | Sim | Sim |
| Criar/editar/excluir salas e recursos | Sim | Não |
| Criar reservas avulsas e recorrentes | Sim | Sim |
| Excluir reservas/séries | Todas da organização | Apenas as que criou |
| Ver cartões e ranking do dashboard | Sim | Sim |
| Ver gráficos e exportar CSV | Sim | Não |
| Escrever salas e recursos pela API | Sim | Não |
| Criar reservas pela API | Sim | Sim |

O campo `responsavel` continua sendo o nome informado para a reserva. `criado_por`
registra a conta autenticada que a criou, sem perder o significado do campo atual.

## API REST

A API usa autenticação por sessão do Django e exige um perfil associado a uma
organização. As rotas ficam sob `/api/` e não aceitam a organização no payload;
ela é sempre obtida do perfil autenticado.

| Método e rota | Acesso |
|---|---|
| `GET /api/recursos/` | Lista os recursos da organização |
| `POST /api/recursos/` | Administrador cria recurso |
| `GET /api/salas/` | Lista salas e recursos da organização |
| `POST /api/salas/` | Administrador cria sala |
| `GET /api/reservas/` | Lista reservas da organização |
| `POST /api/reservas/` | Membro cria reserva, validando conflito |
| `GET /api/reservas/{id}/` | Detalha reserva da organização |
| `PATCH /api/reservas/{id}/` | Administrador ou autor atualiza |
| `DELETE /api/reservas/{id}/` | Administrador ou autor exclui |
| `GET /api/series/` | Lista séries da organização |
| `GET /api/dashboard/?inicio=AAAA-MM-DD&fim=AAAA-MM-DD` | Métricas da organização |

As séries recorrentes são criadas pela tela web, que aplica a regra “tudo ou
nada”. O endpoint de séries é somente leitura nesta versão.

## Dashboard e relatórios

O dashboard parte de uma única consulta filtrada por organização e período. Ele
mostra total de reservas, avulsas e ocorrências recorrentes, ranking de salas,
reservas por mês e por dia da semana. Administradores podem exportar o mesmo
período em CSV. Valores textuais iniciados como fórmulas são neutralizados para
evitar que planilhas executem conteúdo da reserva.

Os gráficos usam Chart.js pela CDN jsDelivr; se o navegador estiver sem acesso à
internet, os cartões e tabelas continuam disponíveis, mas os gráficos não serão
desenhados.

## Segurança e implantação

- Todas as telas de negócio exigem login e perfil organizacional.
- Consultas, IDs de URL, selects de formulários, API e métricas são escopados pela
  organização autenticada.
- CSRF continua ativo para formulários web; a autenticação de sessão do DRF também
  exige CSRF em operações de escrita.
- Em produção, use `DEBUG=0`, `SECRET_KEY` forte fora do repositório,
  `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` explícitos, HTTPS e um banco de dados
  com backup. Configure `SECURE_SSL_REDIRECT=1` e `SECURE_HSTS_SECONDS` apenas
  quando o domínio já estiver servindo HTTPS.
- `.env` e `db.sqlite3` são ignorados pelo Git. Não publique banco com dados reais.

## Testes

Os testes existentes cobrem geração de recorrências, conflitos, fluxo “tudo ou
nada”, filtros de salas e validação de horários. Execute localmente com:

```powershell
python manage.py test
```

## Melhorias mapeadas da P1

O arquivo [`MELHORIAS_P1.md`](MELHORIAS_P1.md) registra as fragilidades que esta
evolução tratou e os pontos de verificação restantes para a entrega.
