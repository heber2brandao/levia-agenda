# Etapa 4 — operação conectada

O painel aprovado está conectado à API e ao PostgreSQL, com navegação em computador
e celular. Abra http://localhost:5173/conta com os servidores do README em execução.

- **Visão geral:** atendimentos do dia, previsão de valor, serviços concluídos no mês,
  clientes e retornos autorizados. A lista de próximos agendamentos cobre hoje e
  os próximos 30 dias, mostra a data de cada atendimento e destaca amanhã.
  Atualiza ao voltar à janela e pelo botão de atualização.
- **Agenda:** dia/semana, reserva manual de múltiplos serviços, bloqueio de horários,
  confirmação, conclusão, cancelamento e reagendamento.
- **Clientes:** cadastro automático, busca, histórico e registro separado de autorização
  para convites, inclusive revogação.
- **Faturamento:** valores dos atendimentos concluídos e previsão dos agendamentos.
  Não representa pagamentos recebidos, lucro ou conciliação bancária.
- **Meu espaço:** nome, expediente, cores e upload permanente de logo.
- **Página pública:** serviços ativos, duração/valor somados, horários disponíveis,
  nome/telefone/e-mail opcional e reserva persistente sem login.

A reserva usa calendário mensal em português, com atalhos Hoje/Amanhã. Selecionar
o dia carrega os horários automaticamente; basta tocar no horário desejado.
Datas fora da janela de 90 dias ficam desabilitadas. Na agenda manual, salvar leva
ao dia reservado. Os indicadores de atendimentos/valor do dia continuam restritos
a hoje; a lista de próximos agendamentos inclui os futuros.

O link público usa o identificador da profissional. Um link localhost só funciona na
máquina onde os servidores estão rodando; compartilhar externamente depende do deploy.
O botão WhatsApp abre uma mensagem para envio manual. Nenhuma mensagem automática é
enviada nesta etapa. Serviços de exemplo da demonstração não alimentam a conta real.

## Persistência e segurança

Migrações `0005_bookings` e `0006_extension_schema` aplicadas ao Supabase. Reservas
guardam os nomes, durações e valores dos serviços no momento da criação. Alterações
posteriores no catálogo não reescrevem esse histórico. Chaves de idempotência evitam
duplicação por repetição de uma requisição; locks transacionais e uma constraint de
exclusão GiST impedem sobreposição, incluindo bloqueios.

As sete tabelas de negócio têm RLS habilitado e forçado; o papel de execução não é
proprietário nem tem BYPASSRLS. A API autenticada deriva a conta do JWT. Na API pública,
uma política SELECT limitada ao UUID solicitado permite resolver a profissional;
somente o servidor estabelece o contexto de tenant para a transação. A resposta pública
contém apenas identidade visual, serviços e recibo restrito, sem histórico ou contatos
privados. Nenhuma credencial PostgreSQL é entregue ao navegador. Há validação de campos,
limite de corpo e rate limiting persistente, inclusive limite adicional para reservas.

O advisor não aponta mais extensão no schema público. O aviso informativo sobre RLS
sem política em `alembic_version` é intencional: acesso da aplicação revogado.
Permanece pendente avaliar a [proteção contra senhas vazadas do Supabase](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection),
sem habilitar cobranças.

## Testes no Windows

Na raiz, com Docker e a venv preparados conforme os guias anteriores:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-test-postgres.ps1
powershell -ExecutionPolicy Bypass -File scripts/test-postgres.ps1
.\.venv\Scripts\python.exe -m ruff check backend
cd frontend
npm.cmd run build
$env:PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/browsers"
npx.cmd playwright install chromium
npm.cmd run test:e2e
npm.cmd run test:business
docker stop levia-stage2-test
```

Não execute os testes Python e os testes de negócio no navegador simultaneamente:
ambos usam o PostgreSQL descartável. O servidor `scripts/business_e2e_server.py`
aceita apenas o banco local `levia_test` em 127.0.0.1:55439, usa identidade controlada
e nunca lê as credenciais do backend/.env. Não deve ser usado como servidor da aplicação.

Resultado: 47 testes Pytest, 8 regressões de demonstração e 2 fluxos integrados
desktop/mobile. Os fluxos integrados verificam reserva pública → agenda → atualização
da página → confirmação → histórico → faturamento com PostgreSQL real local.
Isso não equivale a teste automatizado de Supabase Auth ou envio de e-mail.

## Próximas etapas

Etapa 5: avisos persistentes, worker confiável, Resend, lembretes 24h, retornos com
consentimento e franquia mensal configurável. Etapa 6: assinatura, domínio, deploy,
backup/restore, revisão operacional/LGPD, testes de produção e instalação PWA.
