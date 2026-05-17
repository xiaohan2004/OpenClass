param(
  [switch]$Install
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$frontendDir = Join-Path $repoRoot "frontend"
$tauriDir = Join-Path $repoRoot "tauri"

function Write-Step($Message) {
  Write-Host "[OpenClass Frontend] $Message"
}

function Assert-Command($Name, $Hint) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Missing command $Name. $Hint"
  }
}

Write-Step "Checking required commands"
Assert-Command "node" "Install Node.js."
Assert-Command "npm" "Install Node.js/npm."
Assert-Command "cargo" "Install the Rust toolchain."
Assert-Command "rustc" "Install the Rust toolchain."

$rustVersionText = & rustc --version
$rustVersion = [regex]::Match($rustVersionText, "\d+\.\d+\.\d+").Value
if ([version]$rustVersion -lt [version]"1.87.0") {
  throw "Rust version is too old: $rustVersion. Rust 1.87.0+ is required for the current Tauri dependency set."
}

if ($Install) {
  Write-Step "Installing frontend dependencies"
  Push-Location $frontendDir
  try {
    npm install
  } finally {
    Pop-Location
  }

  Write-Step "Installing Tauri dependencies"
  Push-Location $tauriDir
  try {
    npm install
  } finally {
    Pop-Location
  }
}

Write-Step "Checking frontend dependencies"
if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
  throw "frontend\node_modules is missing. Run OpenClass-Desktop.cmd and enter y when prompted to install."
}

Write-Step "Checking Tauri dependencies"
if (-not (Test-Path (Join-Path $tauriDir "node_modules"))) {
  throw "tauri\node_modules is missing. Run OpenClass-Desktop.cmd and enter y when prompted to install."
}

Write-Step "Environment check passed"
