param(
  [int]$Port = 8501,
  [string]$HostAddr = "127.0.0.1",
  [string]$Python = "python",
  [switch]$NoInstall
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

$venvRoot = Join-Path $repoRoot ".venv-ui"
$venvPy = Join-Path $repoRoot ".venv-ui\\Scripts\\python.exe"

# Recreate env if executable is missing or venv metadata is corrupted.
$venvCfg = Join-Path $venvRoot "pyvenv.cfg"
if ((Test-Path $venvPy) -and !(Test-Path $venvCfg)) {
  Remove-Item -Recurse -Force $venvRoot
}

if (!(Test-Path $venvPy)) {
  & $Python -m venv $venvRoot
}

if (-not $NoInstall) {
  & $venvPy -m pip install --upgrade pip | Out-Null
  & $venvPy -m pip install -r .\\ui\\streamlit\\requirements.txt
}

& $venvPy -m streamlit run .\\ui\\streamlit\\app.py `
  --server.address $HostAddr `
  --server.port $Port `
  --logger.level debug


