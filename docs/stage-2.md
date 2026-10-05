# Etapa 2 — banco, autenticação e isolamento

## Situação atual

Atualização em 03/10/2026: projeto remoto criado, migrações aplicadas e conexão
restrita da API verificada. Consulte [configuração Supabase](supabase-setup.md)
para o estado mais recente; o texto abaixo registra a entrega original da Etapa 2.

Código implementado e testado localmente com PostgreSQL 17. O projeto Supabase ainda
não existe; não houve cadastro real, confirmação/recuperação de e-mail, validação
contra JWKS hospedado ou persistência na nuvem. A demonstração anterior foi preservada.

Rotas da API:

| Rota | Comportamento |
|---|---|
| `GET /api/v1/health` | Liveness; flags indicam configuração, não disponibilidade |
| `GET /api/v1/me` | Perfil da profissional autenticada; 404 se cadastro incompleto |
| `PUT /api/v1/me` | Cria/atualiza o próprio perfil e expediente na mesma transação |

Sem endpoints por ID arbitrário, reservas ou acesso público a clientes nesta etapa.
Modelos: `Professional` (um `owner_id` por conta Auth), `WorkingPeriod` (vários
períodos por dia, segunda=0) e `RateLimit` (contador interno com identificação HMAC).
O ID da profissional é a fronteira de tenant para os módulos futuros.

## Configurar um projeto Supabase

1. Crie um projeto dedicado pelo painel Supabase, conferindo plano e custos antes
   de confirmar. Não reutilize banco de outro sistema. Este código não cria projetos.
2. Obtenha URL do projeto e **publishable key** (`sb_publishable_...`) em API Keys.
   A publishable key pode ir no front-end. Não usar secret key nem `service_role`.
3. Em Auth, habilite e-mail/senha, confirmação de e-mail e senha mínima de 12 caracteres.
   Desabilite login anônimo. Configure Site URL e Redirect URLs para a origem local
   usada e o caminho `/conta`. Não liberar redirecionamento curinga em produção.
4. Use chave de assinatura assimétrica ES256 ou RS256. A API não aceita HS256 legado.
   JWT issuer esperado: URL do projeto + `/auth/v1`; audience: `authenticated`.
5. Pelo botão Connect, obtenha a conexão PostgreSQL para migrações. Prefira conexão
   direta ou pool em modo session. A URL SQLAlchemy começa com `postgresql+psycopg://`.
   Não copie senhas para o chat, comandos versionados ou screenshots.
6. Configure `backend/.env` a partir de `.env.example`, inicialmente com
   `LEVIA_MIGRATION_DATABASE_URL` e `LEVIA_SUPABASE_URL`. Execute, dentro de backend:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current
..\.venv\Scripts\python.exe -m app.provision_role
```

O último comando pede uma senha exclusiva, sem mostrá-la, para habilitar login da
role **levia_app** criada pela migração. Não roda automaticamente. Guarde essa senha
num gerenciador de segredos. Se precisar embutir senha em URL, codifique os caracteres
reservados da senha com percent-encoding. O papel da API não deve herdar outros papéis.

7. Configure `LEVIA_DATABASE_URL` com a conexão do usuário **levia_app**, não postgres.
   Em conexão via Supavisor, siga o formato de usuário fornecido para o seu projeto,
   usando o papel customizado (ex.: papel + referência do projeto). `current_user`
   no PostgreSQL deve continuar sendo `levia_app`. Prepared statements estão
   desativados para compatibilidade com pool transacional. Use TLS para a nuvem;
   produção exige `sslmode=verify-full` e certificado CA confiável (`sslrootcert`).
8. Gere um segredo aleatório local de pelo menos 32 caracteres e configure
   `LEVIA_RATE_LIMIT_SECRET`. Ele precisa ser o mesmo em todas as réplicas da API.
   Não compartilhar com o navegador. Remova a credencial de migração do ambiente
   do processo de API em produção; ela pertence ao processo de migrações.
9. Não exponha o schema **levia** na Data API. A migração revoga acesso de PUBLIC,
   anon, authenticated e service_role a esse schema/tabelas, quando os papéis existem.
   O navegador acessa os dados do produto exclusivamente através de FastAPI.
10. Configure `frontend/.env`: `VITE_SUPABASE_URL`,
    `VITE_SUPABASE_PUBLISHABLE_KEY` e `VITE_API_URL`. Reinicie Vite/recompile após mudar
    variáveis. Use `VITE_DEMO_MODE=false` para disponibilizar somente a área conectada.
    Se true, `/` continua demonstração e `/conta` é a área conectada; não há migração
    automática de dados fictícios da demo para a conta real.

## Executar no Windows

Instalação e VS Code estão no README. Após configurar os arquivos locais, abra dois
terminais PowerShell na raiz:

```powershell
# Terminal API
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-proxy-headers
```

```powershell
# Terminal web
cd frontend
npm.cmd run dev
```

Abra `http://localhost:5173/conta`. Se usar outra porta, inclua a origem exata em
`LEVIA_CORS_ORIGINS` e nos redirecionamentos do Supabase. CORS não substitui autenticação.
O endpoint /health não comprova conexão ou envio de e-mails. Com banco configurado,
o startup recusa papel privilegiado/dono de tabela, memberships e ausência de RLS.

## Testes em PostgreSQL local descartável

Instale/abra Docker Desktop. Na raiz, os comandos abaixo criam somente o container
`levia-stage2-test`, banco `levia_test`, acessível por loopback na porta 55439.
As credenciais de teste são geradas localmente em `.cache`, fora do versionamento.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/start-test-postgres.ps1
docker exec levia-stage2-test pg_isready -U postgres -d levia_test
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/test-postgres.ps1
docker stop levia-stage2-test
```

`ExecutionPolicy Bypass` vale apenas para esse processo, sem mudar a política do
Windows. O script de testes autoriza explicitamente reset **somente** de schema no
banco local `levia_test`. Faz upgrade → downgrade → upgrade e testes com duas contas.
Nunca apontar esse teste para banco de produção. O papel runtime recebe senha temporária
a cada execução. Para testes sem banco: `python -m pytest backend/tests -q` usando a
venv; casos PostgreSQL são marcados como skipped, não como aprovados.

## Garantias implementadas e limites

- JWT: verificação criptográfica via PyJWT/JWKS, algoritmo limitado a ES256/RS256,
  issuer/audience/exp/iat/sub obrigatórios, UUID do usuário, role authenticated e
  rejeição de usuários anônimos. `user_metadata` não decide autorização. Cache de
  JWKS por até 5 minutos, sem cache permanente por chave. Falha do provedor fecha acesso.
- A assinatura de um token não comprova que a sessão foi revogada após sua emissão.
  Access tokens já emitidos podem permanecer válidos até expirar, inclusive após
  logout/exclusão do usuário. Defina expiração curta no Supabase; revogação imediata
  e sincronização do ciclo de exclusão exigem integração adicional antes de produção.
- Perfil e expediente: filtros explícitos por dono/tenant, RLS com USING/WITH CHECK,
  FORCE RLS e role sem BYPASSRLS. `levia.user_id` deriva do JWT e é definido com
  SET LOCAL dentro da transação; não sobrevive ao retorno da conexão ao pool.
- A API usa o banco como serviço confiável; nunca entregue a senha levia_app a
  clientes. O isolamento por contexto pressupõe consultas parametrizadas e controle
  exclusivo do SQL pela aplicação. Nenhuma função SECURITY DEFINER foi criada.
- Cadastro concorrente usa UNIQUE(owner_id) e upsert transacional; alterações de
  expediente são serializadas pelo registro da profissional. Horários sobrepostos,
  fusos inexistentes e campos extras (`tenant_id`/`owner_id`) são rejeitados.
- Quota padrão 60/min por IP e por usuário, compartilhada no PostgreSQL, contagem
  atômica e expurgo oportunista de contadores antigos. Janela fixa: pode haver pico
  na transição de minuto. Retorno 429/Retry-After. Supabase Auth tem seus próprios
  limites/CAPTCHA: configurar no provedor antes de publicar cadastro aberto.
- Payload de perfil limitado a 32 KiB antes do parsing. Erros não devolvem SQL,
  valores de entrada ou tokens. Parâmetros SQL ocultos no logging do engine.
  Não registrar Authorization, cookies, senha ou corpo em proxy/observabilidade.
- `--no-proxy-headers` evita confiar em X-Forwarded-For localmente. Em produção,
  configurar apenas proxies confiáveis e limite de corpo/conexões no ingress.
- Sessões Supabase usam sessionStorage da aba: não armazenamos senhas. JS na mesma
  origem pode acessar tokens; CSP e revisão de XSS continuam no checklist de produção.
  Nunca cachear API ou perfil no service worker. HTML do app requer cache/revalidação
  coerente no deploy; configuração do host ainda é Etapa 6.

## Aceite pendente na nuvem

Criar duas contas próprias de teste, confirmar e-mail, salvar perfis diferentes,
recarregar, sair/entrar, recuperar senha e conferir isolamento. Repetir verificação
dos grants e RLS no projeto Supabase com o papel real da API. Não há certificação
LGPD nem garantia de produção nesta entrega. Upload permanente de logo, exclusão/
exportação de conta, política de retenção, serviços/agenda e notificações são pendências.

Referências usadas: [JWT Supabase](https://supabase.com/docs/guides/auth/jwts),
[RLS](https://supabase.com/docs/guides/database/postgres/row-level-security),
[conexões PostgreSQL](https://supabase.com/docs/guides/database/connecting-to-postgres),
[login com senha](https://supabase.com/docs/reference/javascript/auth-signinwithpassword),
[PyJWT](https://pyjwt.readthedocs.io/en/stable/usage.html).
