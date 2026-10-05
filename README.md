# Levia Agenda

**Render gratuito (validação):** configuração em `render.yaml` e instruções em
[Publicação no Render](docs/render.md). Conexão GitHub e deploy ainda pendentes.

**Preparação de publicação (Etapa 6A):** imagens Docker, proxy HTTPS, verificações de
produção e instruções de deploy estão em [Publicação](docs/production.md).
O sistema ainda não foi publicado; domínio/hospedagem, e-mails reais e assinatura
continuam pendentes. Os comandos locais abaixo continuam válidos.

Micro-SaaS para profissionais autônomos da beleza. **Etapa 5 implementada: avisos, fila de e-mails, lembretes e franquia; envios reais ainda desativados.**

Consulte o [guia da Etapa 5](docs/stage-5.md) para configurar Resend, executar o worker
no Windows e entender os testes e as pendências. Supabase atualizado até
`0007_notifications`. Nenhuma cobrança ou envio externo foi ativado.

A conta conectada abre em `/conta`, com agenda diária/semanal, serviços, clientes,
histórico, faturamento e identidade visual com logo. A página `/agendar/{id}` permite
reservas de múltiplos serviços sem login da cliente. Perfil, serviços, logo e reservas
persistem no PostgreSQL. A demonstração original só é habilitada explicitamente com
`VITE_DEMO_MODE=true`; a configuração local atual usa `false`.

O Supabase está migrado até `0007_notifications`, preservando o cadastro existente.
Autenticação e confirmação de e-mail foram verificadas pelo usuário; os testes
automatizados de negócio usam identidade controlada e banco local, sem testar o login
na nuvem. A ativação dos e-mails reais, assinatura e deploy permanecem pendentes.
Consulte o [guia da Etapa 4](docs/stage-4.md) para operação, segurança e testes.

Consulte o [guia da Etapa 2](docs/stage-2.md) para configurar Auth, migrações, papel
restrito de banco, variáveis e testes de isolamento no Windows.
O [guia da Etapa 3](docs/stage-3.md) documenta a migração do catálogo, a seleção de
múltiplos serviços, as regras de disponibilidade e o que falta para reservas públicas.
O [painel conectado e upload de logo](docs/dashboard-logo.md) já permitem navegar
entre as áreas reais e salvar a identidade visual da profissional.

## Executar no Windows / VS Code

Instale Node.js 22.12+ (ou 24 LTS), Python 3.12+ e VS Code. Abra esta pasta via
**Arquivo → Abrir Pasta**. Use dois terminais PowerShell (**Terminal → Novo Terminal**).
Os comandos abaixo partem da raiz do projeto. `npm.cmd` evita o bloqueio do npm.ps1
pelo PowerShell; não é necessário alterar a política de execução.

### Terminal 1 — interface

```powershell
cd frontend
npm.cmd install
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm.cmd run dev
```

Abra **http://localhost:5173**. Após a primeira instalação, use `npm.cmd ci` quando
houver `package-lock.json` para reproduzir exatamente as dependências.

Se outro projeto estiver usando 5173, execute `npm.cmd run dev -- --port 5180`
e abra `http://localhost:5180`. Ao integrar a API, acrescente essa origem ao CORS.

### Terminal 2 — API

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "./backend[dev]"
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Se `python` não estiver no PATH, use `py -3.12` para criar o ambiente (desde que
essa versão esteja instalada). Não é preciso ativar a venv. No VS Code, selecione
**Python: Select Interpreter → .venv\Scripts\python.exe**.

API: **http://localhost:8000/api/v1/health**. Documentação: **http://localhost:8000/docs**.
O health é apenas liveness do processo; não atesta banco ou integrações.
Encerre os servidores com `Ctrl+C`. Ao reiniciar, basta executar os comandos dos servidores.

As versões Python verificadas estão em `backend/requirements-dev.lock.txt`
(snapshot Windows/Python 3.14). Para reproduzi-las, instale com
`python -m pip install -r backend/requirements-dev.lock.txt` usando o executável da venv,
antes de instalar o projeto editável. Validar compatibilidade ao mudar de plataforma.

### Verificações

```powershell
# Na raiz
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m ruff check backend

cd frontend
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd run test:e2e
npm.cmd run preview
```

Preview do build: **http://localhost:4173**. O Playwright inicia seu próprio servidor
na porta 5174, separada do servidor de desenvolvimento.

## O que explorar

| Página | Caminho | Interação nesta etapa |
|---|---|---|
| Conta conectada | `/conta` | Auth e perfil persistente quando configurados |
| Painel | `/` | Indicadores e atalhos fictícios |
| Agenda | `/agenda` | Alternância diária/semanal ilustrativa |
| Serviços | `/servicos` | Adicionar, editar, ativar/desativar em memória |
| Clientes | `/clientes` | Busca e histórico ilustrativo |
| Meu espaço | `/perfil` | Prévia do formulário de cadastro |
| Página pública | `/agendar/ana` | Serviço → data → horário fictício → dados → simulação |

Desative um serviço e abra a página pública pelo painel: o cartão desaparece.
Recarregar a página restaura a demonstração. Não informe dados pessoais reais.

Na página pública, selecione um ou mais cartões de serviço. O resumo soma valor e
duração para um único atendimento; toque novamente para remover um item. Alterar
os serviços limpa o horário selecionado. A disponibilidade real considerando a
duração conjunta será implementada no motor de agenda.

### Personalização da página pública

Em **Meu espaço**, edite **Nome do espaço** e clique em **Salvar nome do espaço**.
O nome aparece no cabeçalho, na prévia e na página pública durante a sessão.
O botão **Salvar perfil nesta sessão** aplica também seu nome, telefone, e-mail e
demais campos do perfil. Enquanto nenhum nome próprio de empresa for definido,
o espaço acompanha o nome da profissional (ex.: Ateliê Fernanda KieleK). Um nome
de empresa personalizado é preservado ao alterar o nome da profissional.

Em **Meu espaço → Aparência**, escolha a cor principal, a cor de fundo e uma logo.
A prévia muda imediatamente; **Ver página personalizada** abre o agendamento com
a mesma identidade. O painel mantém a identidade Levia. Texto preto/branco é escolhido
automaticamente conforme o fundo para preservar contraste.

Logos aceitas: PNG, JPG e WebP, até 2 MB e 4096 × 4096 pixels. A imagem é decodificada
e reduzida para até 512 pixels no navegador. É possível remover a logo ou restaurar
todo o padrão. Nada é enviado nem gravado em banco/localStorage; atualizar a página
descarta as alterações. Armazenamento por profissional e validação de upload no
servidor ficam para a integração futura.

## Estrutura

```text
backend/
  app/main.py          # FastAPI, configuração segura e rotas
  app/auth.py          # Validação de assinatura e claims Supabase
  app/models.py        # Modelos SQLAlchemy 2 de identidade e expediente
  app/profiles.py      # GET/PUT /api/v1/me
  app/security.py      # Limites compartilhados e tamanho de payload
  app/core/config.py   # Configuração por ambiente
  app/worker.py        # Ponto de entrada explicitamente não implementado
  migrations/          # Migração inicial, grants e RLS
  tests/               # Testes básicos de infraestrutura
  pyproject.toml       # Dependências Python
frontend/
  src/components/ui/   # Componentes shadcn/ui
  src/App.tsx          # Rotas e telas demonstrativas
  src/AccountApp.tsx   # Autenticação e perfil conectado
  src/demo.ts          # Dados fictícios, tipos e formatação
  public/              # Manifesto, ícone e service worker mínimo
  tests/               # Verificações de navegação e fluxo
docs/
  architecture.md      # Decisões, fronteiras e segurança futura
  roadmap.md           # Etapas e critérios de validação
  validation.md        # Resultado real das verificações
  stage-2.md           # Configuração Supabase e segurança
```

## Configuração e PWA

Os `.env.example` não contêm credenciais. `.env` fica fora do versionamento.
Tudo que começa com `VITE_` é público. Nunca colocar chaves privadas ali.
A franquia de 100 e-mails é uma regra planejada, ainda sem contador ou envio.

O build tem manifesto e registra um service worker sem cache. É uma **base de PWA**:
não oferece uso offline nem confirmação de reservas offline. Instalação em todos os
dispositivos, ícones PNG/maskable e atualização controlada precisam de validação antes
de produção. Em produção, PWA exige HTTPS; localhost serve para desenvolvimento.
O host futuro precisa encaminhar rotas da SPA para `index.html`.

## Documentação consultada

- [Vite: instalação e execução](https://vite.dev/guide/)
- [shadcn/ui com Vite](https://ui.shadcn.com/docs/installation/vite)
- [FastAPI: aplicação inicial](https://fastapi.tiangolo.com/tutorial/first-steps/)

Consulte [arquitetura](docs/architecture.md), [próximas etapas](docs/roadmap.md)
e [validação realizada](docs/validation.md). Nenhum recurso pago foi criado.
