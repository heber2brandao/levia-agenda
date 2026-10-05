# Publicacao gratuita de validacao no Render

Status em 05/10/2026: conta Render acessivel; conexao GitHub aguardando verificacao
do usuario. Nenhum servico criado ou publicado por este procedimento ainda.

`render.yaml` prepara uma API Docker Free e um site estatico, com deploys
automaticos desligados. Nao cria PostgreSQL Render, disco, cron ou worker.
O banco continua no Supabase. E-mails seguem desativados.

## Conectar e publicar

1. Concluir a verificacao do GitHub no Chrome. Usar repositorio **privado** para
   o Levia e autorizar o aplicativo Render somente nesse repositorio. Nao conceder
   acesso a todos os repositorios. Nunca enviar `.env`, `.cache`, backups ou senhas.
2. No Render, criar Blueprint a partir do repositorio e conferir o resumo:
   API `free`, site estatico, nenhum recurso pago. Os nomes podem receber sufixos;
   usar as URLs realmente atribuidas pelo painel, nunca supor disponibilidade.
3. Preencher variaveis solicitadas. Na API, `LEVIA_DATABASE_URL` deve usar o papel
   restrito `levia_app`, `sslmode=verify-full` e
   `sslrootcert=/etc/secrets/postgres-ca.crt`. Adicionar o CA oficial como Secret
   File `postgres-ca.crt` no servico da API antes de considerar o deploy concluido.
   Verificar conectividade do endpoint Supabase; se for necessario pooler IPv4,
   usar dados oficiais do projeto e testar o isolamento transacional.
4. `LEVIA_PUBLIC_WEB_URL`: origem HTTPS do site. `LEVIA_CORS_ORIGINS`: lista JSON
   contendo essa origem. `LEVIA_ALLOWED_HOSTS`: lista JSON com hostname real da
   API e `127.0.0.1`. Sem curingas. `LEVIA_SUPABASE_URL`: origem do projeto.
5. No site, `VITE_API_URL`: URL HTTPS da API terminada em `/api/v1`.
   `VITE_SUPABASE_URL`: origem Supabase; `VITE_SUPABASE_PUBLISHABLE_KEY`: somente
   chave publicavel. Nunca usar senha do banco ou chave administrativa no frontend.
6. Ajustar Site URL e redirects do Supabase Auth para a URL real do site seguida
   de `/conta`. Reimplantar o frontend apos alterar variaveis Vite.
7. Validar readiness, login, persistencia apos atualizar, logo, disponibilidade,
   reserva, dashboard e cancelamento com dados de teste autorizados. Conferir
   tambem links diretos da SPA e negacao de acesso entre contas.

## Limites deste ambiente

- API gratuita dorme apos 15 minutos sem requisicoes e pode demorar ao retornar.
  Render nao recomenda seu Free para producao; nao prometer disponibilidade a
  clientes pagantes. Nao adicionar pings para contornar a suspensao.
- O comando desativa headers de proxy: ate validar a cadeia de proxies do Render,
  os limites podem ser compartilhados por visitantes atras do mesmo proxy.
  Nao habilitar confianca irrestrita em X-Forwarded-For para contornar limites.
- TLS do banco, CSP com origens reais e verificacao de IP do visitante devem ser
  revisados no ambiente hospedado antes de liberar uso comercial.
- Nenhum lembrete automatico funciona sem worker/agendador e provedor de e-mail.
- Nao colar segredos no chat. Configura-los somente no painel do servico correto.

Documentacao: [Blueprint](https://render.com/docs/blueprint-spec),
[arquivos secretos](https://render.com/docs/configure-environment-variables),
[limites gratuitos](https://render.com/docs/free).
