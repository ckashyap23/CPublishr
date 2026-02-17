param(
  [int]$Port = 3000,
  [string]$HostAddr = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$npm = $null
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if ($npmCmd) {
  $npm = $npmCmd.Source
}
if (-not $npm) {
  $fallback = "C:\\Program Files\\nodejs\\npm.cmd"
  if (Test-Path $fallback) {
    $npm = $fallback
  }
}
if (-not $npm) {
  throw "npm was not found on PATH. Ensure Node.js is installed and restart your terminal, or install to `C:\\Program Files\\nodejs`."
}

# Ensure node.exe is discoverable for npm scripts (some npm.cmd setups call `node` via PATH).
$nodeDir = Split-Path -Parent $npm
if ($env:Path -notlike "*$nodeDir*") {
  $env:Path = "$nodeDir;$env:Path"
}

if (!(Test-Path "node_modules")) {
  & $npm install
}

& $npm run dev -- --host $HostAddr --port $Port
