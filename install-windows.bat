@echo off
:: ══ AVR Control Plane — Windows Installer ══
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   AVR Control Plane — Windows Installer  ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ── Check for package managers ──────────────────────────────
set "HAS_SCOOP=0"
set "HAS_CHOCO=0"

where scoop >nul 2>&1 && set "HAS_SCOOP=1"
where choco >nul 2>&1 && set "HAS_CHOCO=1"

if "%HAS_SCOOP%"=="1" (
    echo [INFO] Found Scoop — installing AVR tools...
    scoop install avr-gcc avrdude
    goto :verify
)

if "%HAS_CHOCO%"=="1" (
    echo [INFO] Found Chocolatey — installing AVR tools...
    choco install avr-gcc avrdude -y
    goto :verify
)

:: ── No package manager found ────────────────────────────────
echo [WARN] No package manager found.
echo.
echo  Option 1: Install Scoop (recommended)
echo    Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
echo    irm get.scoop.sh ^| iex
echo    scoop install avr-gcc avrdude
echo.
echo  Option 2: Install Chocolatey
echo    Run PowerShell as Admin, then:
echo    Set-ExecutionPolicy Bypass -Scope Process -Force
echo    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
echo    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
echo    choco install avr-gcc avrdude -y
echo.
echo  Option 3: Download WinAVR manually
echo    https://winavr.sourceforge.net/
echo.
goto :python

:verify
echo.
echo [OK] Verifying installation...

:python
echo.
echo [INFO] Checking Python...
where python >nul 2>&1 && (
    echo   Python found.
    echo   Installing PySide6 (optional)...
    pip install PySide6 2>nul || echo   [WARN] PySide6 install failed — will use browser
) || (
    echo   [ERROR] Python not found!
    echo   Download from: https://www.python.org/downloads/
    echo   Make sure to check "Add Python to PATH" during install.
)

echo.
echo ══════════════════════════════════════════
echo   After installing AVR tools, run:
echo   python terminal.py
echo ══════════════════════════════════════════
echo.
pause