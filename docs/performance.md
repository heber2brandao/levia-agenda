# Diagnostico de latencia

A API responde com `Server-Timing`, contendo apenas duracoes em milissegundos.
Nao registra SQL, parametros, tokens, IDs, nomes, telefones ou enderecos.

| Metrica | O que mede |
|---|---|
| app | Tempo dentro da API ate iniciar a resposta; nao inclui rede do navegador nem download |
| ip_limit | Limite de IP, incluindo espera por thread e operacao no banco |
| auth | Verificacao JWT e eventual busca das chaves publicas |
| user_limit | Operacao do limite por usuario |
| db_connect | Obtencao da conexao da sessao autenticada, incluindo pool/pre-ping |
| tenant_context | Configuracao transacional da identidade para RLS |
| sql | Soma das execucoes SQL via driver, incluindo rede API-banco e espera no banco |

As medidas se sobrepoem: `sql` tambem inclui comandos dos limites e do contexto
RLS, e `app` inclui todas as fases. **Nao somar as colunas.** `sql` nao inclui
commit/rollback, pre-ping do pool ou processamento posterior dos resultados.
Nao e tempo puro de CPU do PostgreSQL. Comparar com `pg_stat_statements` ajuda
a diferenciar execucao no servidor do banco e transporte.

No navegador: Rede > Fetch/XHR > uma resposta nova > Timing > Server Timing.
Para leitura publica sem dados pessoais no PowerShell:

```powershell
$r = Invoke-WebRequest https://levia-api.onrender.com/api/v1/ready -UseBasicParsing
$r.Headers['Server-Timing']
```

Publicar no servico **levia-api** (auto-deploy desativado): Manual Deploy > Deploy
latest commit. O deploy do site estatico nao atualiza a API.
Depois confirmar o cabecalho na API publica e coletar os tempos das chamadas
autenticadas; nao copiar Authorization, cookies ou o corpo com dados de clientes.

Referencia: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Server-Timing
