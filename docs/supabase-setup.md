# Supabase — configuração em 03/10/2026

Atualização da Etapa 5: migração `0007_notifications` aplicada e verificada, com dez
tabelas sob RLS forçado. Perfil e quatro serviços preservados. Fila com o mesmo
isolamento por profissional da API; nenhum papel global novo. Envios desativados.
Detalhes: [Etapa 5](stage-5.md).

## Atualização — operação conectada

Migrações até `0006_extension_schema` aplicadas. Preservados o perfil e os quatro
serviços cadastrados. Autenticação e confirmação de e-mail realizadas pelo usuário.
As reservas públicas e manuais agora usam a API com persistência, isolamento e
proteção transacional de conflitos. Ver [Etapa 4](stage-4.md), inclusive limitações
dos testes automatizados e pendência do advisor sobre proteção de senhas vazadas.
As seções abaixo mantêm o histórico de configuração.

Projeto **Levia Agenda** criado na organização `heber2brandao's Org`, região
São Paulo (`sa-east-1`). Referência: `fiyzzjkiysxauuyvrxnm`.
Custo de criação consultado pelo conector: **0/mês**. Nenhum upgrade pago solicitado.

[Abrir projeto](https://supabase.com/dashboard/project/fiyzzjkiysxauuyvrxnm).

## Configurado e verificado

- Migrações Alembic até `0003_migration_metadata` aplicadas ao banco remoto.
  O SQL foi gerado pelo Alembic em modo offline e aplicado pelo conector; a tabela
  `public.alembic_version` registra a revisão correta para futuras migrações.
- Cinco tabelas no schema privado `levia`, todas com ENABLE/FORCE RLS.
- Acesso ao schema negado a `anon`, `authenticated` e `service_role`.
- Papel `levia_app` com login e permissões restritas, sem superusuário, BYPASSRLS,
  propriedade de tabelas ou herança de outros papéis. Senha gerada criptograficamente
  e guardada somente no arquivo local `backend/.env`; o servidor recebeu verificador
  SCRAM. Não há senha administrativa de banco armazenada no aplicativo.
- `backend/.env`: URL do Supabase, conexão PostgreSQL e segredo de rate limit.
- `frontend/.env`: URL e chave pública publishable; `VITE_DEMO_MODE=false`.
  A raiz e rotas antigas redirecionam para `/conta`. A demonstração só é habilitada
  explicitamente com `VITE_DEMO_MODE=true`. Segredos não fazem parte do bundle do navegador.
- Conexão real PostgreSQL direta confirmada com `levia_app` usando TLS.
- Verificação RLS real com duas identidades temporárias: escrita/leitura própria,
  negação de leitura cruzada, rollback integral e limpeza do contexto da conexão.
  Nenhum cadastro Auth foi criado por esse teste.
- Endpoints públicos de Auth responderam HTTP 200: e-mail/senha habilitado,
  confirmação de e-mail ativa, login anônimo desativado e JWKS com ES256.
- 35 testes locais passaram após a migração adicional; Ruff aprovado.
- Build com a configuração pública do projeto aprovado; 8 testes Playwright
  passaram com as variáveis Supabase desabilitadas somente no servidor de testes.
  Isso verifica a demonstração, não o login real.

O advisor de segurança retornou somente o aviso informativo
[RLS sem política](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy)
para `public.alembic_version`. Isso é intencional: a tabela de controle não possui
política de acesso público e seus grants foram revogados. Migrações usam o proprietário.

## Pendências de autenticação

Atualização: captura do painel enviada pelo responsável confirma Site URL
`http://localhost:5173/conta` salvo e os dois redirects localhost/127.0.0.1
listados. A tela local de login carregou com os campos e ações esperados.
O cadastro/confirmacão de e-mail e login com conta real ainda aguardam teste.

Atualização posterior: o responsável confirmou e-mail e informou ter configurado
o perfil. Consulta agregada verificou 1 perfil e 4 serviços persistidos. Corrigida
a configuração local que ainda permitia retornar à demonstração. Verificação sem
sessão no navegador: `/` redireciona para `/conta` e permanece após reload, sem
erros reportados. A sessão autenticada do responsável não foi inspecionada.

O conector não expõe edição das configurações de Auth. O painel exige login do
responsável para concluir:

1. [URL Configuration](https://supabase.com/dashboard/project/fiyzzjkiysxauuyvrxnm/auth/url-configuration):
   definir Site URL `http://localhost:5173/conta` e permitir os redirects exatos
   `http://localhost:5173/conta` e `http://127.0.0.1:5173/conta`.
2. Conferir senha mínima de 12 caracteres no provedor de e-mail e expiração dos JWT.
3. Validar cadastro, confirmação de e-mail, entrada, perfil/catálogo e recuperação
   de senha no navegador, com contas próprias de teste.

Não houve teste E2E com conta Supabase real. Não habilitar envio de e-mails reais
para clientes antes de configurar/validar SMTP e as etapas de notificações.

## Executar no Windows

Reinicie os servidores após a criação dos arquivos `.env`. Na raiz, em dois terminais:

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-proxy-headers
```

```powershell
cd frontend
npm.cmd run dev
```

Abra `http://localhost:5173/conta`. O banco remoto já está migrado; não execute
scripts de reset/testes destrutivos contra esse projeto. Os scripts PostgreSQL de
teste continuam restritos ao banco local descartável `levia_test`.

A conexão local usa `sslmode=require`, adequada ao estágio de desenvolvimento
previsto no projeto. Antes de produção, configurar validação do certificado com
`sslmode=verify-full` e CA confiável. Guardar backup seguro da senha da aplicação;
não copiar arquivos `.env` para repositórios nem enviá-los pelo chat.

Para migrações futuras, obter a credencial administrativa diretamente no painel e
configurar o ambiente dedicado de migrações; nunca substituir `levia_app` por
`postgres` na API.
