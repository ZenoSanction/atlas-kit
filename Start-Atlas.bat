@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Start Atlas
rem Atlas Kit - one-click start, in the right order: Strata (the brain) first, then Sapphire (the voice, with Hermes's
rem tools inside), then the browser. Strata has to start before Sapphire, or it gets less of the graphics card.
rem To shut down: close the Sapphire window FIRST, then the Strata window.

rem ============================ SETTINGS (most people change nothing) ============================
rem Strata's folder, and its start file for your model size (Strata made it: run-<size>.bat). Empty = the first found.
if not defined STRATA_DIR set "STRATA_DIR=C:\Strata"
if not defined STRATA_BAT set "STRATA_BAT="
rem Sapphire's folder (the one with main.py) and the python.exe of Sapphire's environment. Empty = searched for.
if not defined SAPPHIRE_DIR set "SAPPHIRE_DIR="
if not defined SAPPHIRE_PY set "SAPPHIRE_PY="
rem Free memory Strata wants before it starts, in GB. 64 GB PC: about 40 for IQ3_XXS, 30 for IQ2_XS.
if not defined MIN_FREE_GB set "MIN_FREE_GB=40"
if not defined ATLAS_URL set "ATLAS_URL=https://localhost:8073"
if not defined OPEN_BROWSER set "OPEN_BROWSER=1"
rem Browser to open Atlas in: empty = your default browser, or msedge, chrome or firefox.
if not defined BROWSER set "BROWSER="
if not defined STRATA_WAIT_MIN set "STRATA_WAIT_MIN=5"
if not defined SAPPHIRE_WAIT_MIN set "SAPPHIRE_WAIT_MIN=3"
rem ==============================================================================================

echo.
echo   ATLAS  -  Strata (brain) + Sapphire (voice) + Hermes tools (hands)
echo   ------------------------------------------------------------------
echo.

rem ---- find Strata's start file ----
if not defined STRATA_BAT for %%F in ("%STRATA_DIR%\run-*.bat") do if not defined STRATA_BAT set "STRATA_BAT=%%~fF"
if not defined STRATA_BAT (
  echo   Can't find Strata's start file in %STRATA_DIR%. Run Strata's START-HERE.bat once,
  echo   or set STRATA_DIR / STRATA_BAT at the top of this file.
  pause & exit /b 1
)

rem ---- find Sapphire: the folder with main.py, and its python ----
if not defined SAPPHIRE_DIR for %%D in ("%USERPROFILE%\sapphire" "%USERPROFILE%\Documents\sapphire" "C:\sapphire") do (
  if not defined SAPPHIRE_DIR if exist "%%~D\main.py" set "SAPPHIRE_DIR=%%~D"
)
if not defined SAPPHIRE_PY for %%P in ("%USERPROFILE%\miniconda3\envs\sapphire\python.exe" "%LOCALAPPDATA%\miniconda3\envs\sapphire\python.exe" "%ProgramData%\miniconda3\envs\sapphire\python.exe" "%USERPROFILE%\anaconda3\envs\sapphire\python.exe" "%USERPROFILE%\Documents\sapphire_env\Scripts\python.exe" "%SAPPHIRE_DIR%\.venv\Scripts\python.exe") do (
  if not defined SAPPHIRE_PY if exist "%%~P" set "SAPPHIRE_PY=%%~P"
)
if not defined SAPPHIRE_DIR goto sapphire_missing
if not defined SAPPHIRE_PY goto sapphire_missing
echo   Strata:   %STRATA_BAT%
echo   Sapphire: %SAPPHIRE_DIR%  ^(python: %SAPPHIRE_PY%^)
echo.

call :strata_up
if not errorlevel 1 (
  echo   [1/3] Strata is already running.
  goto sapphire
)

:need_sapphire_closed
call :sapphire_up
if not errorlevel 1 (
  echo   Sapphire is open, but Strata is not running. Strata has to start FIRST or it gets less of the graphics card.
  echo   Close the Sapphire window, then press any key.
  pause >nul
  goto need_sapphire_closed
)

:checkmem
set "FREE_GB=0"
for /f %%M in ('powershell -NoProfile -Command "[math]::Floor((Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory).AvailableMBytes/1024)"') do set "FREE_GB=%%M"
if !FREE_GB! LSS %MIN_FREE_GB% (
  echo   Free memory: !FREE_GB! GB. Strata wants about %MIN_FREE_GB% GB free before it starts.
  echo   Close your browser, Discord, games and other big programs.
  choice /c RS /n /m "  Press R to re-check, or S to start anyway: "
  if errorlevel 2 goto start_strata
  echo.
  goto checkmem
)

:start_strata
echo   [1/3] Starting Strata (the brain). The first start of the day can take 1-3 minutes.
start "Strata" "%STRATA_BAT%"
<nul set /p "=        waiting"
powershell -NoProfile -Command "$end=(Get-Date).AddMinutes(%STRATA_WAIT_MIN%); while((Get-Date) -lt $end){ try { if((Invoke-RestMethod 'http://127.0.0.1:8080/health' -TimeoutSec 2).loaded){ exit 0 } } catch {}; Write-Host -NoNewline '.'; Start-Sleep 3 }; exit 1"
if errorlevel 1 (
  echo.
  echo   Strata did not report ready within %STRATA_WAIT_MIN% minutes. Check the Strata window for an error.
  pause & exit /b 1
)
echo  ready.

:sapphire
call :sapphire_up
if not errorlevel 1 (
  echo   [2/3] Sapphire is already running.
  goto open_ui
)
echo   [2/3] Starting Sapphire (the voice, with Hermes's tools inside).
start "Sapphire" /d "%SAPPHIRE_DIR%" "%SAPPHIRE_PY%" main.py
<nul set /p "=        waiting"
powershell -NoProfile -Command "$end=(Get-Date).AddMinutes(%SAPPHIRE_WAIT_MIN%); while((Get-Date) -lt $end){ if(Get-NetTCPConnection -LocalPort 8073 -State Listen -ErrorAction SilentlyContinue){ exit 0 }; Write-Host -NoNewline '.'; Start-Sleep 2 }; exit 1"
if errorlevel 1 (
  echo.
  echo   Sapphire did not start within %SAPPHIRE_WAIT_MIN% minutes. Check the Sapphire window for an error.
  pause & exit /b 1
)
echo  ready.

:open_ui
if "%OPEN_BROWSER%"=="1" (
  echo   [3/3] Opening Atlas in your browser.
  if defined BROWSER (start "" "%BROWSER%" "%ATLAS_URL%") else (start "" "%ATLAS_URL%")
) else (
  echo   [3/3] Atlas is at %ATLAS_URL%
)
echo.
echo   Atlas is up. To shut down: close the Sapphire window FIRST, then the Strata window.
echo.
timeout /t 15
exit /b 0

:sapphire_missing
echo   Can't find Sapphire. Open the top of this file and set:
echo     SAPPHIRE_DIR = the folder that has Sapphire's main.py
echo     SAPPHIRE_PY  = the python.exe of Sapphire's environment
echo   Found so far: folder "%SAPPHIRE_DIR%", python "%SAPPHIRE_PY%"
pause & exit /b 1

rem ---- helpers: exit code 0 = running ----
:strata_up
powershell -NoProfile -Command "try { if ((Invoke-RestMethod 'http://127.0.0.1:8080/health' -TimeoutSec 2).loaded) { exit 0 } } catch {}; exit 1" >nul 2>&1
exit /b %errorlevel%

:sapphire_up
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8073 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>&1
exit /b %errorlevel%
