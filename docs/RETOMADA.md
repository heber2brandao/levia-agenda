# Retomada do deploy Levia — 09/10/2026

## Atualizacao: publicacao e recuperacao de senha

- Segunda otimizacao: perfil/logo reutilizados em memoria por 30s, chaveados pelo token da sessao; edicao de perfil e logo invalidam cache. Testes cobrem expiracao, troca de sessao, copia defensiva, abort e invalidacao. Medicao externa com API ativa: ready 1179ms; /me sem login 863/806ms (401), nao representa tempo do dashboard autenticado. Nao prometer que toda lentidao foi resolvida.

- Otimizacao de navegacao: Clientes nao busca mais indicadores, catalogo e agendamentos. Agenda nao recalcula indicadores; catalogo so e carregado na Agenda. Dados continuam consultados sem cache compartilhado entre contas. Build validado; teste de regressao verifica ausencia dessas chamadas em Clientes.

- API publicada: https://levia-api.onrender.com — `/api/v1/ready` retornou 200.
- Frontend publicado: https://levia-agenda-heber.onrender.com — deploy confirmado pelo painel.
- Rewrite `/*` para `/index.html` salvo. Site URL e redirect `/conta` no Supabase salvos pelo usuario.
- Correcao de recuperacao: compartilhar somente verificadores PKCE temporarios entre abas; capturar PASSWORD_RECOVERY antes do componente React e preservar a tela ao atualizar.
- Dois testes Playwright com Supabase simulado passaram (nova aba/reload e link sem verifier). Nao alteram senha real nem enviam e-mail.
- Proximo passo: publicar a correcao frontend e solicitar NOVO link pelo mesmo navegador. Validar senha e login reais com o usuario.
- Atualizacao posterior: correcao de nova aba confirmada no bundle publico. Usuario abriu Nova senha. Logs Auth de 09/10 22:10 UTC confirmaram `same_password` (422 em `/user`): senha proposta igual a atual. Mensagem especifica implementada e teste de regressao adicionado. Usuario deve escolher senha diferente; login real ainda pendente.
- Plano API Free em Ohio, auto-deploy API Off. E-mails de lembretes e worker continuam desativados; e-mails Auth sao separados.

O restante abaixo e historico anterior a publicacao e nao representa o estado atual.

Objetivo anterior: concluir deploy gratuito de validacao no Render, com respostas
curtas e sem repetir verificacoes concluidas. Nao contratar planos ou dominio.

## Estado confirmado

- Repositorio privado: https://github.com/heber2brandao/levia-agenda
- Commit inicial enviado: `7d02690`; branch `main`.
- GitHub conectado ao Render, workspace `heber's workspace`.
- Ultimo formulario preparado (nao submetido): API `levia-api`, Docker,
  `backend/Dockerfile`, contexto `.`, Virginia, Free US$0, auto-deploy Off,
  healthcheck `/api/v1/ready`.
- Comando: `python -m uvicorn app.main:app --host 0.0.0.0 --port 10000 --no-proxy-headers --no-access-log`.
- Usuario AUTORIZOU explicitamente enviar a credencial restrita do Supabase e
  o segredo de rate limiting como variaveis protegidas do backend Render.
- Usuario informou que habilitou acesso a URLs de arquivo na extensao Chrome.
- Arquivos locais ignorados pelo Git existem: `deploy/secrets/render-api.env`
  e `deploy/secrets/postgres-ca.crt`. NUNCA imprimir, comitar ou expor o .env.
- Conexao ao pooler oficial `aws-0-sa-east-1.pooler.supabase.com:5432` testada
  com `sslmode=verify-full`, CA oficial e usuario `levia_app.fiyzzjkiysxauuyvrxnm`.
- Supabase ref: `fiyzzjkiysxauuyvrxnm`; migracoes ate `0007_notifications`.
- Nenhum deploy online foi confirmado. E-mails e worker permanecem desativados.

## Proxima acao

1. Recuperar controle do navegador e verificar estado real do Render antes de
   criar servicos, evitando duplicatas.
2. Retomar Add from .env / Choose a file com o arquivo local autorizado.
   Adicionar CA como Secret File `postgres-ca.crt` (caminho `/etc/secrets/`).
3. Confirmar plano Free antes de submeter. Publicar API e frontend estatico.
4. URLs no arquivo preparado sao PROVISORIAS: `https://levia-api.onrender.com`
   e `https://levia-agenda-heber.onrender.com`. Conferir URLs atribuidas pelo
   Render e corrigir hosts, CORS, public_web_url e VITE_API_URL antes de testar.
5. Configurar frontend com URL/chave PUBLICAVEL Supabase e demo false.
   Configurar rewrite SPA; atualizar Supabase Auth Site URL/redirect `/conta`.
6. Verificar readiness, pagina publica/disponibilidade, login e persistencia.
   Nao criar reservas reais de teste sem escopo apropriado.

## Bloqueio desta retomada

Em 09/10 o controle de navegador falhou ao iniciar, inclusive apos reset:
`windows sandbox failed: helper_unknown_error: setup refresh had errors`.
Nenhuma acao remota foi realizada nesta retomada. Nao e erro do codigo Levia.
Terminal isolado falhou igualmente; execucao elevada permitiu leitura local.
Solicitar reinicio do aplicativo/sessao Codex; nao pedir nova autorizacao para
credenciais ja autorizadas. Nao insistir em loops de reconexao.

## Preservar

`frontend/tsconfig.json` tem alteracao local nao revisada nesta retomada.
Nao sobrescrever ou enviar automaticamente. Quatro screenshots docs/*.png
estao nao rastreados. Historico: 63 testes backend e fluxo desktop/mobile
passaram anteriormente; nao foram reexecutados nesta retomada.

Limitacoes do piloto: API gratuita dorme; proxy/IP ainda precisa validacao;
sem e-mails automaticos, cobranca, monitoramento e backup operacional concluidos.
