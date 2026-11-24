# Manual de estudo — Reserva de Salas (P1 + P2)

Este manual resume como as partes do projeto se encaixam e onde estudar cada
conceito das Aulas 1–5, 13, 14 e 17.

## 1. Arquitetura e fluxo

O projeto usa Django MVT e páginas MPA: `reservas/urls.py` encaminha a URL para
uma função em `reservas/views.py`; a view consulta models pelo ORM e devolve um
template em `reservas/templates/reservas/`. Os formulários validam dados em
`reservas/forms.py`; regras reutilizáveis de conflito e recorrência ficam em
`reservas/services.py`.

## 2. Models e organização

- `core/models.py`: `Organizacao`, `Perfil` e o model abstrato `DaOrganizacao`.
- `reservas/models.py`: `Recurso`, `Sala`, `Reserva` e `Recorrencia` herdam o
  campo de organização.
- Cada perfil liga uma conta Django a uma organização e a um papel (`admin` ou
  `operador`).
- O `responsavel` textual foi preservado. `criado_por` registra qual conta
  autenticada criou a reserva ou série.

A migração `reservas/migrations/0002_organizacao_e_autoria.py` preserva dados da
P1: cria uma organização padrão, atribui a ela as linhas antigas e só então torna
a FK obrigatória. Faça backup do banco antes de migrar dados em uso. O comando
`python manage.py configurar_organizacao` renomeia a organização padrão e liga o
primeiro superusuário a ela.

## 3. Login e autorização

As views de negócio usam `perfil_required`; mudanças de salas e recursos exigem
`admin_required`. Operadores podem criar reservas, mas só podem apagar as que
criaram. Administradores veem e administram os registros da própria organização.
Superusuários sem perfil ficam no Django Admin até serem associados a uma
organização.

O isolamento precisa aparecer em todas as leituras e gravações:

- filtrar querysets pelo `request.organizacao`;
- buscar IDs dentro desse queryset, para registros de outra organização
  responderem 404;
- limitar salas e recursos que aparecem em formulários;
- definir a organização no servidor, nunca a partir do payload do cliente.

## 4. API

`reservas/api_urls.py` define a fronteira `/api/`; `api_views.py` filtra os
querysets pela organização do perfil; `serializers.py` escolhe os campos
expostos e valida referências dentro do tenant. A autenticação usa sessão Django
e as permissões globais exigem usuário autenticado. Salas e recursos só aceitam
escrita de administradores; reservas podem ser alteradas pelo autor ou pelo
administrador. Séries são somente leitura pela API nesta versão.

## 5. Dashboard e relatórios

`reservas/dashboard.py` centraliza a consulta base e as agregações. Todas as
métricas recebem o queryset já filtrado por organização e período. O dashboard
mostra totais, salas mais reservadas, série mensal e distribuição por dia da
semana; operadores veem cartões e ranking, enquanto gráficos e CSV ficam para
administradores. `json_script` passa os dados ao Chart.js com escape seguro. A
exportação usa o mesmo filtro e neutraliza campos textuais que poderiam ser
interpretados como fórmulas por planilhas.

## 6. Variáveis de ambiente

`reservasalas/settings.py` lê `.env`, mantém `DEBUG` desligado por padrão e exige
uma chave definida fora do modo local. `.env.example` serve de modelo; o arquivo
`.env` e o banco local não devem ser versionados. Em produção, configure hosts,
origens CSRF, chave forte, HTTPS, banco e backup.

## 7. Caminho para estudar o código

1. Leia `reservas/models.py` para entender as entidades e relações.
2. Siga `reservas/urls.py` → `reservas/views.py` → um template para entender MVT.
3. Leia `reservas/forms.py` e `reservas/services.py` para as validações.
4. Compare `reservas/api_urls.py`, `api_views.py` e `serializers.py` com as telas.
5. Leia `reservas/dashboard.py` e `templates/reservas/dashboard.html` para ver as
   agregações e gráficos.

Para executar os testes existentes, use `python manage.py test` depois de criar
o ambiente e aplicar as migrações.
