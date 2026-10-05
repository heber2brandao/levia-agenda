# Etapa 5 — avisos, e-mails e lembretes

Implementação disponível; **envio real desativado**. Nenhuma conta Resend, domínio,
chave ou cobrança foi criada. Migração `0007_notifications` aplicada ao Supabase,
com dez tabelas protegidas por RLS. O cadastro e os serviços existentes foram preservados.

## O que funciona

- Avisos persistentes no dashboard para novos agendamentos e mudanças de status/data,
  com contagem de não lidos e marcação de leitura por conta.
- Fila transacional: o agendamento e suas notificações são gravados juntos.
- E-mail de recebimento do pedido, confirmação profissional, cancelamento e reagendamento,
  somente quando a reserva tem endereço informado.
- Lembrete programado para 24 horas antes. Reservas feitas com menos de 24 horas
  recebem o aviso de recebimento; não geram um lembrete retroativo adicional.
- Retorno após conclusão, na data sugerida às 9h no fuso da profissional, somente
  com autorização. Novo atendimento concluído ou reserva futura suprimem convite antigo.
- Revogação pelo painel ou link assinado no e-mail, com confirmação explícita na
  página de preferências. Abrir o link não revoga automaticamente (evita robôs de e-mail).
- Franquia padrão de 100 por mês e profissional, configurável administrativamente
  em `professionals.monthly_email_limit`. O cliente da API não pode aumentar seu limite.
- WhatsApp continua exclusivamente manual.

Eventos anteriores à migração não são recriados. Os avisos surgem nas próximas operações.
Não copiamos endereços antigos de clientes para uma reserva pública que não informou e-mail.

## Confiabilidade e limites

O worker usa o mesmo papel restrito `levia_app`, RLS e contexto transacional por
proprietário. `LEVIA_WORKER_OWNER_IDS` enumera explicitamente as contas autorizadas.
Não há papel com leitura irrestrita, BYPASSRLS ou acesso de `anon` à fila.
Novas assinaturas precisam ser incluídas na configuração de execução; automatizar esse
provisionamento controlado faz parte da preparação de produção.

Jobs usam `FOR UPDATE SKIP LOCKED`, lease de 5 minutos e token de posse. Se houver
interrupção, outro ciclo recupera o job. A reserva da franquia ocorre por UPSERT
atômico antes do envio, apenas uma vez por job, no mês local da primeira tentativa.
O payload e a chave de idempotência permanecem iguais entre tentativas, mesmo após reinício.

O Resend guarda [chaves de idempotência por 24 horas](https://resend.com/docs/dashboard/emails/idempotency-keys).
O worker interrompe tentativas após 23 horas ou oito tentativas e exige revisão,
evitando reenvio automático após a expiração dessa proteção. Backoff entre tentativas;
erros definitivos não são repetidos. Timeout e falha de rede não são tratados como
sucesso. Respostas e endereços não são escritos nos logs.

Cancelamento, versão do agendamento, expiração e consentimento são conferidos antes
de enviar. Uma mensagem já em trânsito/aceita pelo provedor não pode ser desfeita por
cancelamento ou revogação posteriores. `accepted` significa aceitação pelo provedor,
não entrega na caixa de entrada; webhooks de entrega/bounce não foram implementados.

Tentativas de resultado incerto e falhas conservam sua reserva da franquia. Mensagens
barradas por quota não são enviadas no mês seguinte automaticamente. Jobs expirados
são descartados. Essa política conservadora evita ultrapassar a franquia e enviar
avisos antigos. O painel distingue pendentes, aceitos, quota e revisão.

## Configuração segura para ativar depois

1. Verificar um domínio e remetente no Resend, com os registros DNS solicitados.
2. Publicar o frontend em HTTPS: links localhost não servem às clientes.
3. Configurar somente no servidor as variáveis comentadas em `backend/.env.example`:
   `LEVIA_RESEND_API_KEY`, `LEVIA_EMAIL_FROM`, `LEVIA_PUBLIC_WEB_URL` e
   `LEVIA_EMAIL_UNSUBSCRIBE_SECRET` (32+ caracteres aleatórios). Não colar segredos no chat.
4. API e worker devem usar o mesmo segredo de revogação. `LEVIA_WORKER_OWNER_IDS`
   recebe uma lista JSON de UUIDs `auth.users.id`, não o ID público do espaço.
5. Somente depois de validar domínio, URLs e execução, definir `LEVIA_EMAIL_ENABLED=true`
   em API e worker e reiniciar a API. A chave deve ter apenas permissão de envio.
6. Executar uma verificação real com destinatário autorizado e observar o resultado.
   Isso ainda não foi feito; os testes usam um adaptador controlado, sem e-mails externos.

Não é necessário adicionar chaves ou alterar políticas no frontend. Consulte a
[API de envio do Resend](https://resend.com/docs/api-reference/emails/send-email).

## Windows / VS Code

Na raiz do projeto, usando a venv do README:

```powershell
# Um ciclo; enquanto desativado, sai sem processar ou enviar nada:
powershell -ExecutionPolicy Bypass -File scripts/run-worker.ps1 --once

# Processo contínuo (Ctrl+C encerra; os jobs permanecem no banco):
powershell -ExecutionPolicy Bypass -File scripts/run-worker.ps1
```

Para operação durável, usar supervisor de processos na hospedagem. Alternativa Windows:
no Agendador de Tarefas, executar `powershell.exe` com argumentos
`-NoProfile -ExecutionPolicy Bypass -File "CAMINHO_ABSOLUTO\scripts\run-worker.ps1" --once`,
repetindo a cada minuto, sem iniciar nova instância se já estiver em execução.
Não foi registrada tarefa automática nesta etapa. O banco persiste horários e tentativas;
o processo precisa estar ativo para enviar. Lembretes atrasados só são enviados enquanto
o atendimento ainda não começou.

## Verificação executada

- Migrações upgrade/downgrade/upgrade em PostgreSQL 17 descartável.
- Testes de isolamento, deduplicação, quota concorrente, lease/reinício, timeout,
  expiração, cancelamento/reagendamento, consentimento e link adulterado.
- Adaptador HTTP Resend testado com transporte local: nenhum envio real.
- Fluxo navegador → API → PostgreSQL local em desktop/celular, incluindo leitura de avisos.
- Compilação TypeScript/Vite e Ruff.
- `python -m app.worker --once` confirmou envio desativado na configuração local real.

Para repetir, iniciar o banco com `scripts/start-test-postgres.ps1`, executar
`scripts/test-postgres.ps1` e, depois, `npm.cmd run test:business` em `frontend`.
Não executar esses dois conjuntos simultaneamente; usam o mesmo banco descartável.

## Pendências antes de produção

Resend/domínio, HTTPS público, processo supervisionado, monitoramento de fila/revisão,
política de retenção dos payloads com dados pessoais, validação de entrega e operação
do ciclo de assinaturas. O advisor permanece com o aviso preexistente de
[proteção contra senhas vazadas desativada](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).
O aviso informativo de [RLS sem política em alembic_version](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy)
é intencional: metadados de migração sem acesso da aplicação.
