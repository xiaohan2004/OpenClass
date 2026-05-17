param(
  [switch]$Dev
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$frontendDir = Join-Path $repoRoot "frontend"
$tauriDir = Join-Path $repoRoot "tauri"
$backendReq = Join-Path $repoRoot "backend\requirements.txt"
$backendScript = Join-Path $PSScriptRoot "start-backend.ps1"
$frontendScript = Join-Path $PSScriptRoot "start-frontend.ps1"

function Write-Step($Message) {
  Write-Host "[OpenClass] $Message"
}

function Assert-Command($Name, $Hint) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Missing command $Name. $Hint"
  }
}

function Confirm-Install($Message) {
  $answer = Read-Host "$Message Install now? (y/n)"
  if ($answer -ne "y" -and $answer -ne "Y") {
    throw "Required dependencies are missing."
  }
}

function Test-BackendReady {
  try {
    Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
    return $true
  } catch {
    return $false
  }
}

function Wait-BackendReady {
  for ($i = 0; $i -lt 20; $i++) {
    if (Test-BackendReady) {
      return $true
    }
    Start-Sleep -Seconds 1
  }
  return $false
}

Write-Step "Checking required commands"
Assert-Command "node" "Install Node.js."
Assert-Command "npm" "Install Node.js/npm."
Assert-Command "cargo" "Install the Rust toolchain."
Assert-Command "rustc" "Install the Rust toolchain."
Assert-Command "python" "Install Python 3.10+ and make sure python is in PATH."

$rustVersionText = & rustc --version
$rustVersion = [regex]::Match($rustVersionText, "\d+\.\d+\.\d+").Value
if ([version]$rustVersion -lt [version]"1.87.0") {
  throw "Rust version is too old: $rustVersion. Rust 1.87.0+ is required."
}

$pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$pythonVersion -lt [version]"3.10") {
  throw "Python version is too old: $pythonVersion. Python 3.10+ is required."
}

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
  Confirm-Install "frontend\node_modules is missing."
  Push-Location $frontendDir
  try {
    npm install
  } finally {
    Pop-Location
  }
}

if (-not (Test-Path (Join-Path $tauriDir "node_modules"))) {
  Confirm-Install "tauri\node_modules is missing."
  Push-Location $tauriDir
  try {
    npm install
  } finally {
    Pop-Location
  }
}

try {
  python -c "import fastapi, uvicorn, sqlmodel" | Out-Null
} catch {
  Confirm-Install "Backend Python dependencies are missing."
  python -m pip install -r $backendReq
}

if (Test-BackendReady) {
  Write-Step "Backend is already running at http://127.0.0.1:8000"
} else {
  Write-Step "Starting backend in a separate window"
  Start-Process -FilePath "powershell" -ArgumentList @(
    "-ExecutionPolicy", "Bypass",
    "-NoExit",
    "-File", $backendScript
  ) -WorkingDirectory $repoRoot

  if (Wait-BackendReady) {
    Write-Step "Backend is ready"
  } else {
    Write-Host "[OpenClass] Backend did not become ready within 20 seconds. The frontend window will still open; check the backend window for errors."
  }
}

Write-Step "Starting frontend"
$frontendArgs = @()
if ($Dev) {
  $frontendArgs += "-Dev"
}
& $frontendScript @frontendArgs
