param(
  [switch]$Install
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$backendReq = Join-Path $repoRoot "backend\requirements.txt"

function Write-Step($Message) {
  Write-Host "[OpenClass Backend] $Message"
}

function Assert-Command($Name, $Hint) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Missing command $Name. $Hint"
  }
}

function Confirm-Install($Message) {
  $answer = Read-Host "$Message Install now? (y/n)"
  if ($answer -ne "y" -and $answer -ne "Y") {
    throw "Required backend dependencies are missing."
  }
}

Write-Step "Checking Python"
Assert-Command "python" "Install Python 3.10+ and make sure python is in PATH."

$pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$pythonVersion -lt [version]"3.10") {
  throw "Python version is too old: $pythonVersion. Python 3.10+ is required."
}

if ($Install) {
  Write-Step "Installing backend Python dependencies"
  python -m pip install -r $backendReq
}

Write-Step "Checking backend Python dependencies"
try {
  python -c "import fastapi, uvicorn, sqlmodel" | Out-Null
} catch {
  Confirm-Install "Backend Python dependencies are missing."
  python -m pip install -r $backendReq
}

$env:PYTHONPATH = Join-Path $repoRoot "backend"
Push-Location $repoRoot
try {
  Write-Step "Starting FastAPI at http://127.0.0.1:8000"
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} finally {
  Pop-Location
}
