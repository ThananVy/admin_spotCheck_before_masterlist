@echo off
REM ============================================================================
REM FIRST TIME SETUP - Run this ONCE to install UV and dependencies
REM ============================================================================

echo.
echo ========================================
echo  FIRST TIME SETUP
echo  Duplicate Detection System v2.0
echo ========================================
echo.
echo This will install UV and all required libraries.
echo You only need to run this ONCE!
echo.
pause

REM Check if running with admin rights
echo [1/4] Checking permissions...
net session >nul 2>&1
if %errorLevel% == 0 (
    echo   Admin rights detected: OK
) else (
    echo   Running as normal user: OK
)
echo.

REM Install UV
echo [2/4] Installing UV...
echo   This may take 1-2 minutes...
echo.
powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: UV installation failed!
    echo Please check your internet connection and try again.
    echo.
    pause
    exit /b 1
)

echo.
echo   UV installed successfully!
echo.

REM Add UV to PATH for current session
set PATH=%USERPROFILE%\.local\bin;%PATH%

REM Wait a moment for installation to complete
timeout /t 2 /nobreak >nul

echo [3/4] Installing Python dependencies...
echo   This may take 2-3 minutes...
echo.

REM Install dependencies using UV
cd /d "%~dp0"
uv pip install pandas numpy scipy openpyxl

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to install dependencies!
    echo.
    echo Trying alternative method...
    uv sync
)

echo.
echo [4/4] Verifying installation...
echo.

REM Check if dependencies are installed
uv pip list | findstr pandas >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   pandas: OK
) else (
    echo   pandas: MISSING
)

uv pip list | findstr numpy >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   numpy: OK
) else (
    echo   numpy: MISSING
)

uv pip list | findstr scipy >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   scipy: OK
) else (
    echo   scipy: MISSING
)

uv pip list | findstr openpyxl >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   openpyxl: OK
) else (
    echo   openpyxl: MISSING
)

echo.
echo ========================================
echo  SETUP COMPLETE!
echo ========================================
echo.
echo Next steps:
echo 1. Close this window
echo 2. Put your Excel files in the Source folder:
echo    - Master_Data.xlsx
echo    - New_Data.xlsx
echo 3. Double-click: run_daily.bat
echo.
echo You only needed to run this setup once!
echo From now on, just use run_daily.bat
echo.
pause
