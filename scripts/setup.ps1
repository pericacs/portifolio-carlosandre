$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
if (Test-Path -LiteralPath $envPath) {
    Write-Host '.env existente preservado.'
    exit 0
}
$randomBytes = New-Object byte[] 32
$generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try { $generator.GetBytes($randomBytes) } finally { $generator.Dispose() }
$databasePassword = [Convert]::ToBase64String($randomBytes)
$template = Get-Content -LiteralPath (Join-Path $projectRoot '.env.example') -Raw
[IO.File]::WriteAllText($envPath, $template.Replace('POSTGRES_PASSWORD=', "POSTGRES_PASSWORD=$databasePassword"))
Write-Host '.env criado com senha aleatória. Nenhum administrador foi criado.'
