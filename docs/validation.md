# Validação da Etapa 1

## Estado atual — preparação de publicação (Etapa 6A)

63 testes Pytest aprovados com PostgreSQL local, incluindo recusa de configurações
inseguras, hosts não permitidos, documentação oculta e readiness. Ruff aprovado.
Imagens Linux Python 3.12 e frontend Node/Caddy construídas; `pip check` na imagem
aprovado, API sem root e sem `.env` na imagem. Compose e Caddy validados.
Em contêineres locais: rotas SPA, proxy `/api`, headers de segurança, cache de assets
e resposta 503 de readiness sem banco verificados. Não houve conexão produtiva
nesses contêineres nem emissão de certificado público. Domínios `example.test` e
chave publicável de teste foram usados somente no build de validação.
O preflight identificou os arquivos de configuração e certificado ainda ausentes;
isso é uma pendência de publicação, não uma integração concluída.
Nenhum deploy, contratação ou backup/restore remoto foi executado.
Detalhes e passos pendentes: [Publicação](production.md).

## Estado atual — Etapa 5 (04/10/2026)

54 testes Pytest aprovados, Ruff aprovado, 2 fluxos integrados de navegador aprovados
em desktop/celular com avisos e marcação de leitura; build TypeScript/Vite aprovado.
Testes de envio usam transporte local controlado, sem comunicação com Resend.
Supabase migrado até `0007_notifications`, dez tabelas com RLS forçado; cadastro
preservado. Worker real executado com `--once`: nenhum e-mail processado, pois está
desativado. Restam configuração Resend/domínio, hospedagem e validação de envio real.
Avisos de depreciação Starlette/httpx e cache Pytest Windows não impediram os testes.
Detalhes, limitações e comandos: [Etapa 5](stage-5.md). Abaixo, histórico anterior.

## Estado atual — Etapa 4

Correção de datas (04/10/2026): seleção pública/manual com datas por extenso em
português e valores ISO, limitada a hoje e aos próximos 90 dias. O teste integrado
confere a data enviada à API. Build aprovado novamente; consulta pública real de
05/10/2026 com Corte Degradê + Luzes retornou 26 horários para 90 minutos, sem criar
reserva na conta da profissional. A apresentação foi conferida em navegador com
idioma inglês, eliminando a dependência do formato regional do campo de data.

47 testes Pytest aprovados com PostgreSQL local, Ruff aprovado, 8 testes de
regressão da demonstração e 2 testes integrados de negócio em desktop/celular.
Build TypeScript/Vite aprovado. Supabase migrado até `0006_extension_schema`;
perfil e quatro serviços existentes preservados. Os testes integrados usam
identidade controlada local, não o login real do Supabase. Detalhes e comandos
em [Etapa 4](stage-4.md). As seções abaixo são registros históricos.

## Configuração Supabase — atualização posterior

Banco remoto migrado até `0003_migration_metadata`; conexão `levia_app` e RLS
verificados na nuvem com rollback dos dados temporários. Auth público/JWKS
responderam HTTP 200 com ES256. 35 testes locais passaram novamente após a
migração adicional. Login e recuperação de senha reais ainda aguardam configuração
de URLs no painel e teste com conta própria. Ver [registro](supabase-setup.md).

## Estado mais recente — Etapa 3

Em 03/10/2026: 35 testes Pytest aprovados, incluindo PostgreSQL 17 local e
migrações upgrade/downgrade/upgrade; 8 testes Playwright aprovados (desktop/mobile),
build TypeScript/Vite aprovado. Catálogo e disponibilidade testados pela API e
pelo motor puro; interface conectada ainda sem validação E2E Supabase.
As ocorrências de cache Windows e depreciação Starlette/httpx continuam sendo
avisos, não falhas. Detalhes e comandos: [Etapa 3](stage-3.md).

## Histórico — Etapa 2

Em 03/10/2026, **25 testes Pytest passaram**, com PostgreSQL 17 real em container
local descartável; **8 testes Playwright passaram** em Chromium desktop/mobile.
Build TypeScript/Vite aprovado, Ruff sem problemas e `pip check` sem dependências
incompatíveis. O módulo de conta é carregado separadamente para não aumentar o
carregamento inicial da demonstração.

Cobertura do back-end: assinatura/claims JWT com chaves criptográficas de teste,
tokens inválidos/expirados, metadata editável ignorada, payload limitado, validação
de perfil/expediente, migração upgrade/downgrade/upgrade, persistência, RLS entre
contas, revogação de grants de anon/authenticated/service_role, proprietário imutável,
reutilização de conexões sem contexto vazado, cadastro concorrente e rate limit
atômico/HTTP resistente a X-Forwarded-For forjado.

Os testes de persistência injetam identidades de teste na dependência da API; a
verificação JWT é testada separadamente com assinatura real gerada para testes.
Não foram usados tokens nem credenciais de um projeto Supabase. Os testes de UI
verificam a conta **sem configuração**, além de todos os fluxos demonstrativos.
Login/cadastro/recuperação de senha e perfil conectado no navegador precisam ser
validados contra o projeto real após configuração. Não há teste E2E Supabase concluído.

O PostgreSQL descartável `levia-stage2-test` foi parado após os testes; o script de
inicialização permite retomá-lo. Nenhum recurso de nuvem nem cobrança foi criado.
Detalhes operacionais e limitações: [Etapa 2](stage-2.md).

Ocorrências: corrigido identificador SQL reservado no contador de requisições;
uma execução inicial de navegador excedeu o limite durante a primeira carga, e a
rodada final passou em 18,9s. O timeout do cenário agora é 60s. Pytest ainda relata
o aviso upstream Starlette/httpx e um aviso de escrita no cache do Windows, sem
falha nos testes. O histórico abaixo descreve etapas anteriores, não substitui
este registro mais recente.

Ambiente: Windows, PowerShell, Node 24.12.0, npm 11.6.2, Python 3.14.2.

## Executado e aprovado

| Verificação | Resultado |
|---|---|
| Pytest (`python -m pytest backend/tests -q`) | 3 testes passaram |
| Ruff (`python -m ruff check backend`) | Sem problemas encontrados |
| TypeScript e Vite (`npm.cmd run build`) | Build de produção gerado |
| Playwright (`npm.cmd run test:e2e`) | 6 testes passaram: 3 cenários × desktop/mobile |
| Inspeção agent-browser | Painel renderiza; navegação identificada; nenhum erro de execução reportado |
| Inspeção visual | Capturas desktop e mobile em `docs/desktop.png` e `docs/mobile.png` |

API: contrato de saúde sem integrações, endpoint de negócio inexistente e origem CORS
não autorizada. Interface: adicionar serviço, desativar outro, refletir cartões públicos,
escolher serviço/data/horário, concluir simulação com e-mail ausente e opt-in desmarcado,
verificar mensagem de ausência de reserva real e ausência de overflow no resultado.
Também foram verificadas agenda semanal, busca sem resultado, formulário de perfil
e rota inexistente. Teste de fluxo captura exceções JavaScript e exige lista vazia.

## Ocorrências resolvidas e avisos

- Rede do sandbox bloqueou instalações inicialmente; instalação autorizada fora dessa
  restrição permitiu baixar dependências. Nenhuma credencial ou serviço pago foi usado.
- Cache npm do CLI shadcn teve erro de bloqueio; uma nova execução com cache separado
  instalou os três componentes oficiais. Build confirmou compatibilidade.
- Vite precisou executar fora da restrição que bloqueava sua pasta temporária.
- Testes de navegador ganharam a porta exclusiva 5174 após conflito com o dev server.
- As capturas finais foram feitas no build de preview em 4187, pois outro projeto
  passou a responder em 5173 após o encerramento do servidor desta demonstração.
- Pytest passou com um aviso upstream de depreciação Starlette/httpx no TestClient.
  Migrar o adaptador de testes quando estabilizada a combinação na Etapa 2.
- Os testes também exibiram aviso de configuração de cores do terminal, sem falhas.

## Não verificado / não implementado

Nenhum teste de banco, RLS, Supabase Auth, concorrência de reservas, limites de abuso,
Resend, worker, quota mensal, pagamento ou deploy: esses recursos ainda não existem.
Não foi atestada conformidade LGPD, segurança de produção, acessibilidade completa,
compatibilidade com Safari/Firefox ou instalação PWA em dispositivos reais.
Emulação mobile usou Chromium, não Safari nativo. Offline não é suportado.

Os testes de infraestrutura e demonstração desta etapa não substituem os testes
de negócio, segurança e concorrência previstos para as próximas etapas.

## Incremento: aparência personalizada

Build TypeScript/Vite aprovado e suíte de 6 testes aprovada após a personalização.
O novo cenário verifica logo PNG, rejeição de SVG, cores aplicadas na página pública,
texto legível em fundo escuro e destaque claro, painel sem alteração de paleta,
remoção da logo, restauração e perda das alterações ao recarregar. Os testes de API
não foram repetidos neste incremento, pois o back-end não mudou.

A rodada inicial com 4 workers teve timeouts no carregamento; com 2 workers todos
os testes passaram em 17,8 segundos. Configuração agora limita a concorrência a 2.
Inspeção visual do preview em `/perfil` concluída, sem erros de execução reportados;
captura em `docs/appearance.png`. Limites de upload foram implementados no navegador;
não houve upload remoto ou validação de segurança no servidor.

## Correção: nome do espaço

Nome agora compartilhado entre cabeçalho, prévia e página pública, com botão
dedicado de salvamento na sessão. Build aprovado e 6 testes Playwright passaram
em 13,5 segundos. O cenário de aparência também verifica remoção de espaços nas
extremidades, manutenção do nome ao navegar, rejeição de nome contendo apenas
espaços e restauração ao recarregar. Nenhuma persistência remota foi adicionada.

## Incremento: vários serviços no mesmo atendimento

Build aprovado e 6 testes Playwright passaram em 13,9 segundos. O fluxo público
agora testa dois serviços, soma de preços/durações, remoção de itens, seleção vazia,
limpeza do horário após alteração e resumo final com todos os serviços. Cenários
executados em desktop e mobile. O motor real de disponibilidade não foi implementado;
o total de minutos é demonstrativo e não altera os horários fictícios apresentados.

## Correção: salvar os dados da profissional

O antigo botão Simular cadastro foi substituído por Salvar perfil nesta sessão.
Nome, telefone, e-mail, especialidade, fuso e expediente agora são mantidos no estado
compartilhado ao navegar. Sem nome de empresa personalizado, o título público acompanha
o nome da profissional. Empresas com nome próprio mantêm esse nome.
Build aprovado e 6 testes passaram em 16,6 segundos; regressão reproduz o caso
Fernanda KieleK, valida saudação, título público, permanência do nome/telefone na
navegação e preservação de um nome de empresa personalizado. Sem persistência remota.
