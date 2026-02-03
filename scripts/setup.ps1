\
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $MyInvocation.MyCommand.Path) | Out-Null
Set-Location ..

if (!(Test-Path ".\.venv")) {
  python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt

Write-Host ""
Write-Host "Listo. Para ejecutar:"
Write-Host "  .\scripts\run.ps1"
