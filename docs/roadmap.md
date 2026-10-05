# Desenvolvimento por etapas

**Etapa 6A — pacote de publicação preparado:** Docker API/frontend/worker opcional,
proxy HTTPS, preflight e verificações de produção. Ainda sem hospedagem/domínio
configurados e sem assinatura/cobrança. Ver [Publicação](production.md).

**Estado atual — Etapa 5:** avisos e fila persistentes, worker por conta, lembretes,
convites com revogação e franquia implementados. Migração `0007_notifications` aplicada.
Envios reais dependem de Resend/domínio/worker e continuam desativados. Ver [guia](stage-5.md).
O restante deste arquivo registra o planejamento e estados anteriores.

**Atualização:** Etapas 1–4 implementadas; banco Supabase conectado e migrado até
`0006_extension_schema`. Confirmação de e-mail e login realizados pelo usuário.
Painel, agenda, reservas, clientes e faturamento documentados em [Etapa 4](stage-4.md).
Próximo trabalho: Etapa 5, notificações. O planejamento abaixo registra a sequência original.

1. **Base e experiência demonstrativa (implementada):** validar linguagem, identidade,
   navegação mobile, cartões de serviço e fluxo público com a pessoa responsável.
   Não avançar automaticamente para integrações.
2. **Banco, autenticação e segurança (implementação local atual):** modelagem tenant/profissional/expediente,
   migração Alembic inicial, Supabase Auth, isolamento com papel restrito e RLS,
   limites de requisição. Critério: testes de acesso cruzado e JWT inválido negados.
   Testes locais aprovados; pendente criar/configurar o projeto Supabase e validar
   autenticação e persistência reais pelo navegador. Ver `stage-2.md`.
3. **Serviços e disponibilidade (implementação local atual):** CRUD persistente, especialidades múltiplas,
   sugestões opcionais por especialidade, expediente com intervalos/fusos, serviços
   ativos na prévia privada conectada. Testes de bordas temporais e catálogo por tenant
   aprovados; página pública persistente fica com a Etapa 4. Ver `stage-3.md`.
4. **Reservas e clientes:** operação pública/manual, bloqueios, cancelamento,
   reagendamento, confirmação/conclusão, histórico, opt-in e revogação reais.
   Critério: reservas concorrentes nunca sobrepõem ocupação; idempotência comprovada.
5. **Notificações e testes:** worker durável, Resend, lembrete 24h, retornos com
   autorização, limite mensal atômico, botão WhatsApp manual, painel de avisos.
   Critério: reinício do worker, retry, cancelamento e quota sem duplicar envios.
6. **Produção e assinatura:** contrato de billing, integração futura de pagamento,
   staging, CI/CD, revisão de dependências, backup/restore, observabilidade, PWA
   instalável validada, acessibilidade e privacidade. Nenhum deploy nesta Etapa 1.

## Aceite visual proposto

- Explorar painel e agenda em celular e desktop.
- Adicionar/editar um serviço e verificar seu cartão na página pública.
- Desativar um serviço e conferir que ele deixa de ser oferecido na mesma sessão.
- Concluir a simulação sem e-mail; convite futuro começa desmarcado.
- Conferir que todos os resultados dizem claramente que não há reserva real.
- Validar se a paleta, os rótulos e a quantidade de passos atendem ao público.
