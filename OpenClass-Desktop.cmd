@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\desktop\start-openclass.ps1" %*
if errorlevel 1 (
  echo.
  echo OpenClass failed to start. See the error above.
  pause
)
