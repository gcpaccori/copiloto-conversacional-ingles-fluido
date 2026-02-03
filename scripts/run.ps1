\
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $MyInvocation.MyCommand.Path) | Out-Null
Set-Location ..

.\.venv\Scripts\python.exe -m app.main
