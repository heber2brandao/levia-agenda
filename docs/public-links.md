# Links públicos por negócio

O cadastro gera `public_slug` a partir do nome do espaço, sem acentos. Nomes
repetidos recebem um sufixo. O endereço não muda nas edições seguintes do perfil.
`/agendar/{uuid}` continua válido, inclusive para disponibilidade e reservas.
O perfil exibe o endereço completo e o botão Copiar link.

## Publicação de 11/10/2026

- Migração Alembic `0008_public_slugs` aplicada ao Supabase e versão registrada.
- Perfil existente recebeu `barber-heber`; RLS continua habilitada e forçada.
- 73 testes do backend passaram; build e fluxo desktop/celular passaram.
- Após enviar o commit, publicar a API: Render → levia-api → Manual Deploy →
  Deploy latest commit. O frontend publica automaticamente.
- Confirmar GET `/api/v1/public/barber-heber` e o endereço antigo retornando 200.
- A troca do endereço principal `levia-agenda-heber.onrender.com` ainda está
  pendente no Render. Não basta mudar o caminho `/agendar/...`.

## Ao trocar o endereço principal

Usar a URL realmente atribuída pelo Render, sem supor disponibilidade. Manter
o endereço antigo durante a transição. Atualizar `LEVIA_PUBLIC_WEB_URL`, adicionar
a nova origem em `LEVIA_CORS_ORIGINS` e adicionar `/conta` às URLs autorizadas no
Supabase Auth. Só então atualizar Site URL, testar login/recuperação/agendamento
e compartilhar os novos endereços. Não criar serviços pagos ou comprar domínio.

## Revisão de segurança

A política de busca por slug é limitada a SELECT do papel interno `levia_app`.
Nenhum acesso foi concedido a anon/authenticated. Os endpoints públicos retornam
somente o DTO público e limpam o contexto de busca dentro da transação.

O advisor manteve os avisos de configuração: a tabela administrativa
`alembic_version` tem RLS sem políticas (intencionalmente sem acesso público),
e a proteção Auth contra senhas vazadas está desativada. Referências:
https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy
https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection
