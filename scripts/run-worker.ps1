$ErrorActionPreference = 'Stop'
$leviaRoot = Split-Path $PSScriptRoot -Parent
Push-Location (Join-Path $leviaRoot 'backend')
try {
    & (Join-Path $leviaRoot '.venv/Scripts/python.exe') -m app.worker @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
