param(
  [switch]$Install,
  [switch]$Dev
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

$checkArgs = @{}
if ($Install) {
  $checkArgs.Install = $true
}
& (Join-Path $PSScriptRoot "frontend-check.ps1") @checkArgs

$env:OPENCLASS_REPO_ROOT = $repoRoot
Push-Location (Join-Path $repoRoot "tauri")
try {
  if ($Dev) {
    npm run tauri:dev
    exit
  }

  $frontendExe = Join-Path $repoRoot "tauri\src-tauri\target\release\openclass-desktop.exe"
  if (-not (Test-Path $frontendExe)) {
    Write-Host "[OpenClass Frontend] Release exe not found. Building it now."
    npm run tauri:build
  }

  Start-Process -FilePath $frontendExe
} finally {
  Pop-Location
}
