param([string]$Python = "python")
Push-Location $PSScriptRoot\..
try {
  & $Python -m venv .venv
  . .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  pip install -e .[dev]
}
finally {
  Pop-Location
}
