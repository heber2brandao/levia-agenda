# Migrações (Etapa 2)

Revisão `0001_identity`: schema privado levia, profissionais, períodos de expediente,
contadores compartilhados de rate limit, grants e RLS forçado.

Com LEVIA_MIGRATION_DATABASE_URL configurada, em backend:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current
```

Não há conexão automática no import nem migração no startup. Nunca executar
create_all para substituir a migração. Downgrade apaga os dados da revisão:
é usado apenas no banco descartável de testes. A role levia_app permanece no downgrade.
Não expor schema levia na Data API do Supabase.
