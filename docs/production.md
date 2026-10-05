# Preparação para publicação — Etapa 6A

O pacote de publicação está no workspace. **Ainda não há site publicado, domínio
configurado, servidor contratado ou cobrança de assinaturas.** A configuração
local existente continua usando desenvolvimento. Este guia não ativa e-mails.

## Arquitetura preparada

- Servidor Linux com Docker Compose: Caddy entrega o frontend React e encaminha
  `/api/*` para a API. Apenas portas 80/443 ficam expostas.
- Caddy prepara HTTPS automático após DNS/domínio reais, certificados persistidos
  nos volumes `caddy_data` e `caddy_config`. Não remover esses volumes na atualização.
- API Python 3.12 executada sem root, sistema de arquivos somente leitura e sem
  credenciais administrativas. PostgreSQL permanece no Supabase.
- Worker opcional, mesmo código/imagem da API, habilitado pelo profile `email`.
  Inicialmente fica desligado. Não há WhatsApp automático.
- Contexto Docker exclui `.env`, credenciais, certificados, caches e dados de testes.
  Somente URL e chave **publicável** do Supabase entram no build do frontend.
- API confia em headers de proxy apenas do IP reservado do Caddy (`172.30.0.2`).
  Não usar `--forwarded-allow-ips=*` nem expor a porta 8000 na internet.
  Se a sub-rede conflitar com a hospedagem, alterar Compose e o IP confiável juntos.

As regras do proxy seguem a [documentação do Caddy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
O [profile de Compose](https://docs.docker.com/compose/how-tos/profiles/) evita iniciar
o worker até que o envio seja configurado. Certificados públicos só são obtidos
quando DNS, domínio e acesso externo às portas estiverem disponíveis.

## Informações que faltam

### Verificação de hospedagem em 04/10/2026

A conta Vercel conectada foi consultada e está no plano **Hobby**. Esse plano
[permite somente uso pessoal não comercial](https://vercel.com/docs/plans/hobby),
portanto não foi criado deployment comercial do Levia nem ativado plano pago.
Não é necessário comprar domínio: provedores podem oferecer endereço próprio,
como o [subdomínio onrender.com do Render](https://render.com/docs/web-services).
Não há acesso Render conectado nesta sessão. O plano gratuito do Render
[suspende a API após 15 minutos sem tráfego](https://render.com/docs/free),
então não deve ser apresentado como hospedagem sempre disponível para clientes.

O pacote Docker local continua sendo a preparação validada. Ainda faltam escolher
e acessar a hospedagem, adaptar sua configuração, provisionar os segredos e o CA
do banco, atualizar os redirects do Supabase e validar o fluxo completo por HTTPS.
Nenhuma publicação, alteração de plano ou compra foi realizada nesta verificação.

Domínio/subdomínio escolhido e hospedagem Linux com Docker. Depois serão necessários:
registros DNS, certificado CA do PostgreSQL, acesso SSH ao servidor, configuração
de e-mail e definição do processo de backup. Não envie senhas no chat.
Não foi selecionado fornecedor nem plano pago. O pacote pode ser adaptado à hospedagem escolhida.

## Preparar no Windows / VS Code

Na raiz, preserve os arquivos locais atuais de `backend` e `frontend`:

```powershell
Copy-Item deploy/.env.example deploy/.env
Copy-Item deploy/backend.env.example deploy/.env.backend
New-Item -ItemType Directory -Force deploy/secrets
```

Preencha os modelos. Em `.env`, `DOMAIN` é só o domínio, sem `https://`. Em
`.env.backend`, `LEVIA_PUBLIC_WEB_URL` e CORS usam a origem HTTPS completa.
`LEVIA_ALLOWED_HOSTS` inclui esse domínio e `127.0.0.1` (healthcheck interno).

O banco usa **levia_app**, nunca `postgres` ou `service_role`. A URL deve conter
`sslmode=verify-full&sslrootcert=/run/secrets/postgres-ca.crt`. Salve o certificado
CA oficial do projeto em `deploy/secrets/postgres-ca.crt`; não é um certificado
inventado/autossinado nem a senha do banco. O certificado e a configuração ficam
fora das imagens e do versionamento. Não copiar chaves Resend para arquivos do frontend.

```powershell
.\.venv\Scripts\python.exe scripts/check-production.py
docker compose --env-file deploy/.env -f deploy/compose.yaml config --quiet
docker compose --env-file deploy/.env -f deploy/compose.yaml build
```

O preflight confere somente arquivos e consistência; não consulta DNS, não abre o
banco nem garante entrega de e-mail. Use `config --quiet`: a saída completa do
Compose pode revelar os valores dos segredos. A construção gera imagens locais;
não publica nada. O build de teste com `example.test` não pode ser enviado como release.

## Publicar depois que o servidor e o domínio forem definidos

1. Criar primeiro um ambiente de validação. Não usar dados pessoais de clientes
   para ensaios de restauração, testes de carga ou simulações de reservas.
2. Configurar DNS para o servidor e liberar 80/443; manter SSH restrito. Não colocar
   outro proxy/CDN à frente sem revisar IP confiável e limites de requisição.
3. Transferir código/imagens e configurações por canal seguro. Restringir a leitura
   dos `.env` ao administrador. Nunca comitar esses arquivos.
4. No Supabase Auth, configurar Site URL e redirect permitido exatamente como
   `https://SEU_DOMINIO/conta`; manter os localhost somente enquanto forem necessários
   ao desenvolvimento. Conferir o modelo de confirmação e recuperação de senha.
5. Confirmar migração `0007_notifications` e papel restrito. Migrações administrativas
   são tarefas separadas; não são executadas automaticamente na inicialização.
   O container da API recusa `LEVIA_MIGRATION_DATABASE_URL` em produção.
6. No servidor, executar o preflight e iniciar:

```powershell
docker compose --env-file deploy/.env -f deploy/compose.yaml up -d api web
docker compose --env-file deploy/.env -f deploy/compose.yaml ps
```

Os comandos Docker também funcionam no shell Linux. `restart: unless-stopped`
recupera processos encerrados; marcar container como unhealthy não o reinicia
automaticamente. Configure monitoramento externo e alerta humano.

## Conferências obrigatórias no ambiente publicado

- `https://SEU_DOMINIO/api/v1/health`: processo ligado. Não prova integração.
- `https://SEU_DOMINIO/api/v1/ready`: conexão com banco disponível (HTTP 200);
  responde 503 genérico se indisponível. A validação do papel/RLS ocorre no startup.
- `/docs`, `/redoc` e `/openapi.json` não expõem a API em produção.
- Novo cadastro, confirmação de e-mail, login/logout e recuperação de senha.
- Duas profissionais: isolamento de perfil, serviços, agenda, clientes e avisos.
- Reserva de amanhã pelo celular, confirmação no painel, reagendamento/cancelamento,
  bloqueio de conflito e dados preservados ao recarregar.
- Logo/cores, calendário, links públicos e ausência de erros de rede/CSP.
- HTTPS válido, sem conteúdo misto; chaves privadas ausentes dos assets públicos.

Após isso, configurar Resend conforme [Etapa 5](stage-5.md). O worker precisa de
lista explícita de proprietários autorizados. Com tudo configurado:

```powershell
.\.venv\Scripts\python.exe scripts/check-production.py --with-email
docker compose --env-file deploy/.env -f deploy/compose.yaml --profile email up -d worker
```

Não ativar antes de validar remetente e domínio. Testar uma mensagem para destinatário
autorizado e observar a fila; os testes automatizados não são prova de entrega real.

## Atualização, rollback, backup e suporte

Definir uma nova `RELEASE_TAG` por release. Preservar a imagem/tag anterior antes
de reconstruir. Atualizar com `up -d`; em caso de falha, voltar ao tag anterior
compatível com o schema. Nunca fazer downgrade destrutivo do banco automaticamente.
Os locks Python e npm registram dependências testadas; revisar atualizações e
reconstruir as imagens periodicamente, incluindo correções das imagens base.

Antes da primeira cliente pagante, definir frequência/retenção/criptografia de
backups e testar restauração em projeto separado. Validar dados do schema `levia`,
identidades do Supabase Auth, vínculo dos proprietários, políticas e configurações.
Copiar apenas `levia` não recupera sozinho as contas de autenticação. Registrar
quem pode restaurar, perda máxima aceitável de dados e tempo de recuperação.
Este pacote não criou backup nem testou restauração na nuvem.

Configurar alerta para `/ready`, falhas do worker e filas em revisão/quota. Logs
de acesso da API foram desativados para não registrar caminhos/tokens/dados; logs
operacionais têm rotação. Preparar retenção de dados, canal de suporte, termos de
uso e política de privacidade antes da venda. A PWA tem manifest e worker básicos;
instalação em dispositivos reais ainda precisa de validação após HTTPS.

## O que continua fora desta entrega

Hospedagem/DNS efetivos, emissão real de TLS público, envio real Resend, backup/restore
operacional, assinatura/cobrança recorrente, cancelamento de assinatura e controle de
acesso por situação de pagamento. A Etapa 6A prepara a publicação; não declara o
produto liberado para venda nem ativa integrações de pagamento.
