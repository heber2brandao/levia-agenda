# Etapa 3 — catálogo e disponibilidade

Atualização: banco remoto criado e conectado após esta entrega. Consulte
[configuração Supabase](supabase-setup.md) para verificações e pendências de Auth.

Implementação local. Nenhum projeto Supabase foi criado, nenhuma cobrança ativada
e nenhuma reserva pública real foi liberada. A conexão de Auth permanece pendente
conforme o [guia da Etapa 2](stage-2.md).

## Funcionalidades

- Área `/conta`, seção **Serviços e horários**: criação, edição, ativação e
  desativação persistentes; nome, preço em centavos, duração e retorno opcional.
- Sugestões opcionais conforme as especialidades salvas no perfil. O preço deve
  ser informado pela profissional; escolher uma sugestão não salva automaticamente.
- Prévia privada com nome do espaço e cores do perfil, cartões dos serviços ativos,
  seleção de múltiplos serviços e soma de preço/duração.
- Consulta real à API para calcular horários a partir do expediente e das ocupações
  do banco. A consulta não cria nem garante reserva.
- Migração `0002_catalog`: serviços e ocupações com RLS obrigatório, índices e
  permissões restritas. A aplicação só pode ler ocupações nesta etapa.

## Regras do motor

Horários de início a cada 15 minutos, contados a partir da abertura do período;
duração exata da combinação selecionada. Períodos adjacentes são unidos. Pausas
não podem ser atravessadas. Inícios passados ou iguais ao momento atual não são
oferecidos. Uma ocupação pode terminar exatamente quando o próximo serviço começa.
Ocupações canceladas são ignoradas; ocupações de outras contas não interferem.

O expediente é interpretado no fuso IANA da profissional e os instantes são
retornados com UTC. `tzdata` assegura os fusos também no Windows. Janelas que
atravessam mudança de offset ou possuem extremidades ambíguas/inexistentes são
omitidas por segurança. Essa política conservadora pode retirar horários em dias
de mudança de horário de verão em outros países.

Consulta entre hoje e 90 dias à frente, até 10 serviços e 480 minutos por combinação.
Catálogo limitado a 500 serviços para proteção de recursos; isso não representa
limite de agendamentos da assinatura. Valores de R$ 0,00 a R$ 99.999,99 por serviço,
durações de 5 a 480 minutos, retorno de 1 a 365 dias ou vazio.

## Executar no Windows

No terminal PowerShell do VS Code, a partir da raiz:

```powershell
.\.venv\Scripts\python.exe -m pip install -e "./backend[dev]"
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-proxy-headers
```

O comando Alembic exige `LEVIA_MIGRATION_DATABASE_URL` configurada no arquivo local
`backend/.env`, conforme a Etapa 2. Não use a credencial de migração como credencial
da API. Sem projeto/banco configurado, não execute a migração contra uma URL inventada.

Em outro terminal, a partir da raiz:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Abra `http://localhost:5173/conta`. Após configurar Supabase e API, entre, salve
seu perfil e expediente e abra **Serviços e horários**. Sem configuração, permanece
o aviso explícito; a demonstração em `/` continua separada, com dados fictícios.

## Validação executada

35 testes Pytest aprovados com PostgreSQL 17 local: inclui ciclo de migrações,
RLS, catálogo, combinação de serviços, horários ocupados, cancelamentos, limites
e bordas temporais. Os testes de API injetam identidades locais; os de JWT verificam
assinaturas separadamente. Não constituem teste de login com Supabase.

8 testes Playwright aprovados em Chromium desktop/mobile para a demonstração e a
conta sem configuração. Build TypeScript/Vite aprovado. O catálogo conectado no
navegador ainda precisa ser validado com um projeto Supabase real.

Comandos reproduzíveis a partir da raiz (Docker Desktop iniciado):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/start-test-postgres.ps1
docker exec levia-stage2-test pg_isready -U postgres -d levia_test
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/test-postgres.ps1
docker stop levia-stage2-test
.\.venv\Scripts\python.exe -m ruff check backend
```

O script de testes reinicia o esquema **somente no banco local descartável
`levia_test`**. Sem esse banco, `python -m pytest backend/tests` pula os testes
PostgreSQL, preservando os testes unitários.

## Pendências da Etapa 4

Página pública com catálogo persistente e consulta sem login; criação manual e
pública de reservas; bloqueios editáveis; proteção transacional de sobreposição;
cancelamento, reagendamento e clientes. A tabela de ocupações é apenas a base de
leitura nesta etapa, sem endpoint de gravação ou restrição de exclusão ainda.
Também seguem pendentes o upload permanente de logo e a validação de Auth na nuvem.

Referências técnicas: [ZoneInfo do Python](https://docs.python.org/3/library/zoneinfo.html)
e [intervalos PostgreSQL](https://www.postgresql.org/docs/current/rangetypes.html).
