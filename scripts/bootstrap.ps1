param(
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $VenvPath)) {
    python -m venv $VenvPath
}

$Python = Join-Path $VenvPath "Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -e .
& $Python -m stock_agent_orchestrator.cli doctor
& $Python -m stock_agent_orchestrator.cli demo

Write-Host "bootstrap complete"
