# Serves this folder on 127.0.0.1:<PORT> and exposes it publicly via Tailscale Funnel.
# Usage: powershell -ExecutionPolicy Bypass -File serve.ps1 [-NoFunnel]
param([switch]$NoFunnel)

$siteDir = $PSScriptRoot
$port = 8787
$envFile = Join-Path $siteDir ".env"
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^\s*PORT\s*=\s*(\d+)\s*$') { $port = [int]$Matches[1] }
    }
}

# Start the static server unless something is already listening on the port.
$listening = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $listening) {
    $py = (Get-Command python -ErrorAction Stop).Source
    Start-Process -FilePath $py -ArgumentList @("-m", "http.server", "$port", "--bind", "127.0.0.1", "--directory", "`"$siteDir`"") -WindowStyle Hidden
    Write-Output "Static server started on http://127.0.0.1:$port"
} else {
    Write-Output "Something is already listening on port $port - leaving it running."
}

if (-not $NoFunnel) {
    $ts = "C:\Program Files\Tailscale\tailscale.exe"
    if (-not (Test-Path $ts)) { $ts = (Get-Command tailscale -ErrorAction Stop).Source }
    & $ts funnel --bg $port
}
