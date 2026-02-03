\
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $MyInvocation.MyCommand.Path) | Out-Null
Set-Location ..

if (!(Test-Path ".\.venv")) {
  Write-Host "Primero corre .\scripts\setup.ps1"
  exit 1
}

.\.venv\Scripts\pip.exe install -r requirements-optional.txt
Write-Host "Opcionales instalados."
