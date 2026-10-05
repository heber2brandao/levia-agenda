# Starts only the named disposable PostgreSQL container; never targets Supabase.
$ErrorActionPreference = 'Stop'
$leviaRoot = Split-Path $PSScriptRoot -Parent
$leviaCache = Join-Path $leviaRoot '.cache'
New-Item -ItemType Directory -Force $leviaCache | Out-Null
$leviaSecrets = Join-Path $leviaCache 'levia-test-db.json'
$leviaExisting = docker ps -a --filter 'name=^/levia-stage2-test$' --format '{{.Names}}'
if ($LASTEXITCODE -ne 0) { throw 'Abra o Docker Desktop e tente novamente.' }
if ($leviaExisting -eq 'levia-stage2-test') {
    if (-not (Test-Path -LiteralPath $leviaSecrets)) { throw 'Arquivo local de credenciais de teste não encontrado.' }
    docker start levia-stage2-test
} else {
    $leviaPassword = [guid]::NewGuid().ToString('N')
    @{ password = $leviaPassword } | ConvertTo-Json | Set-Content -LiteralPath $leviaSecrets -Encoding utf8
    $env:POSTGRES_PASSWORD = $leviaPassword
    try {
        docker run --name levia-stage2-test -e POSTGRES_PASSWORD -e POSTGRES_DB=levia_test -p 127.0.0.1:55439:5432 -d postgres:17
        if ($LASTEXITCODE -ne 0) { throw 'Não foi possível iniciar o banco de teste.' }
    } finally { Remove-Item Env:POSTGRES_PASSWORD -ErrorAction SilentlyContinue }
}
Write-Output 'Banco descartável levia-stage2-test iniciado. Aguarde ficar pronto antes dos testes.'
