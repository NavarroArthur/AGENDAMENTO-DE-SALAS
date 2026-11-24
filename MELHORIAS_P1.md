# Revisão da P1 antes da evolução

Itens que estavam frágeis no MVP e como esta etapa os trata:

1. **Views sem autenticação:** as telas de negócio agora exigem login e perfil;
   operações de catálogo são exclusivas do administrador e reservas são limitadas
   ao autor ou ao administrador da organização.
2. **Dados sem organização:** modelos de negócio recebem uma FK obrigatória;
   uma migração de dados atribui registros existentes à organização padrão.
3. **Conflitos sujeitos a gravações simultâneas:** criação avulsa e de séries
   revalidam o conflito dentro de transação e bloqueiam a sala no banco que
   oferece `SELECT FOR UPDATE`.
4. **Configuração insegura para produção:** `DEBUG` fica desligado por padrão;
   a chave é obrigatória fora do modo local e os cookies de sessão/CSRF usam
   `Secure` quando `DEBUG=0`.
5. **Cobertura P2 pendente:** acrescentar e executar cenários de isolamento entre
   duas organizações, papéis, API e métricas antes da demonstração final.

Antes de migrar um banco existente, faça backup. Após criar o superusuário,
execute `python manage.py configurar_organizacao --nome "Minha organização"
--usuario <username>` para associar a primeira conta aos dados legados.
