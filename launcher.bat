@echo off
REM =============================================================
REM Dark of Hemi v2.0 - Launcher for Windows
REM =============================================================
REM   launcher.bat              - menu
REM   launcher.bat single       - single player
REM   launcher.bat mobile       - mobile mode
REM   launcher.bat server       - LAN server
REM   launcher.bat client <IP>  - LAN client
REM =============================================================
setlocal enabledelayedexpansion

set "HERE=%~dp0"
set "GAME=%HERE%dark_of_hemi_v2.0.py"
set "CRYPTO=%HERE%crypto80.py"

REM --- find python ---
set "PYTHON="
for %%P in (python py python3) do (
  if not defined PYTHON (
    %%P -c "import sys; sys.exit(0 if sys.version_info[0]==3 else 1)" >nul 2>&1
    if !errorlevel! == 0 set "PYTHON=%%P"
  )
)
if not defined PYTHON (
  echo [ERROR] Python 3 not found. Install from https://www.python.org/
  pause
  exit /b 1
)

if not exist "%GAME%" (
  echo [ERROR] Not found: %GAME%
  pause
  exit /b 1
)

set "MODE=%~1"
if "%MODE%"=="" goto menu
if /i "%MODE%"=="single" ( "%PYTHON%" "%GAME%" --single & goto end )
if /i "%MODE%"=="mobile" ( "%PYTHON%" "%GAME%" --mobile & goto end )
if /i "%MODE%"=="server" ( "%PYTHON%" "%GAME%" --server & goto end )
if /i "%MODE%"=="client" ( "%PYTHON%" "%GAME%" --client %~2 & goto end )
if /i "%MODE%"=="encrypt" ( "%PYTHON%" "%CRYPTO%" encrypt -i "%~2" -o "%~2.enc" & goto end )
if /i "%MODE%"=="decrypt" ( "%PYTHON%" "%CRYPTO%" decrypt -i "%~2" & goto end )
echo [ERROR] Unknown mode: %MODE%
goto end

:menu
echo =============================================
echo  DARK OF HEMI v2.0 - Launcher (Windows)
for /f "delims=" %%V in ('"%PYTHON%" --version 2^>^&1') do echo  Python: %%V
echo =============================================
echo  1) Single player
echo  2) Mobile mode
echo  3) LAN server
echo  4) LAN client
echo  0) Exit
set /p choice="> "
if "%choice%"=="1" "%PYTHON%" "%GAME%" --single
if "%choice%"=="2" "%PYTHON%" "%GAME%" --mobile
if "%choice%"=="3" "%PYTHON%" "%GAME%" --server
if "%choice%"=="4" (
  set /p ip="Server IP [127.0.0.1]: "
  if "!ip!"=="" set "ip=127.0.0.1"
  "%PYTHON%" "%GAME%" --client !ip!
)
if "%choice%"=="0" goto end

:end
endlocal
