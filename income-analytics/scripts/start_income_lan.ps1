param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$localPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $localPython) {
    $localPython
} else {
    (Get-Command python -ErrorAction Stop).Source
}

$projectSource = Join-Path $projectRoot "src"
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$projectSource;$env:PYTHONPATH" } else { $projectSource }
Set-Location -LiteralPath $projectRoot
Write-Host "Income disponível neste PC em http://127.0.0.1:$Port"
Write-Host "Income disponível na rede local em http://192.168.1.82:$Port"
& $python -B -m uvicorn income_analytics.main:app --host 0.0.0.0 --port $Port
