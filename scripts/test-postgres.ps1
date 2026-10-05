# Only for the disposable local Docker database created during development.
$ErrorActionPreference = 'Stop'
$leviaRoot = Split-Path $PSScriptRoot -Parent
$leviaCredentials = Get-Content -LiteralPath (Join-Path $leviaRoot '.cache/levia-test-db.json') -Raw | ConvertFrom-Json
$env:LEVIA_TEST_ADMIN_URL = 'postgresql+psycopg://postgres:' + $leviaCredentials.password + '@127.0.0.1:55439/levia_test'
$env:LEVIA_TEST_ALLOW_RESET = '1'
try {
    & (Join-Path $leviaRoot '.venv/Scripts/python.exe') -m pytest (Join-Path $leviaRoot 'backend/tests') -q
    $leviaTestExit = $LASTEXITCODE
} finally {
    Remove-Item Env:LEVIA_TEST_ADMIN_URL -ErrorAction SilentlyContinue
    Remove-Item Env:LEVIA_TEST_ALLOW_RESET -ErrorAction SilentlyContinue
}
exit $leviaTestExit
