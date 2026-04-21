@echo off
REM ============================================================================
REM Duplicate Checker - Auto-Run Script
REM ============================================================================
REM This script runs the duplicate detection system using UV package manager
REM No Python installation needed!
REM ============================================================================

echo.
echo ========================================
echo  Duplicate Detection System v2.0
echo ========================================
echo.

REM Check if uv is installed
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: UV is not installed!
    echo.
    echo Please install UV first:
    echo 1. Download from: https://github.com/astral-sh/uv/releases/latest
    echo 2. Or run: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo.
    pause
    exit /b 1
)

echo [1/3] Checking UV installation... OK
echo.

REM Check if Source folder exists
if not exist "Source" (
    echo ERROR: Source folder not found!
    echo Please create a "Source" folder and add your files:
    echo   - Source\Master_Data.xlsx
    echo   - Source\New_Data.xlsx
    echo.
    pause
    exit /b 1
)

REM Check if files exist
if not exist "Source\Master_Data.xlsx" (
    echo ERROR: Master_Data.xlsx not found in Source folder!
    echo Please add your Master_Data.xlsx file to the Source folder.
    echo.
    pause
    exit /b 1
)

if not exist "Source\New_Data.xlsx" (
    echo ERROR: New_Data.xlsx not found in Source folder!
    echo Please add your New_Data.xlsx file to the Source folder.
    echo.
    pause
    exit /b 1
)

echo [2/3] Checking source files... OK
echo   - Master_Data.xlsx found
echo   - New_Data.xlsx found
echo.

REM Create Results folder if it doesn't exist
if not exist "Results" mkdir Results

echo [3/3] Running duplicate detection...
echo.
echo ----------------------------------------
echo.

REM Run the script with UV
uv run duplicate_checker_v2.py

REM Check if script ran successfully
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo  SUCCESS! Check the Results folder
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Open the Excel file in Results folder
    echo 2. Review the "Summary" sheet first
    echo 3. Check "Flagged_Duplicates" for manual review
    echo 4. All clean shops are auto-merged to Master_Data
    echo.
    echo Your Master_Data.xlsx has been updated!
    echo Backup created automatically.
    echo.
) else (
    echo.
    echo ========================================
    echo  ERROR! Something went wrong
    echo ========================================
    echo.
    echo Please check:
    echo 1. Are your Excel files formatted correctly?
    echo 2. Do they have the required columns?
    echo 3. Check error message above
    echo.
)

echo.
echo Press any key to close...
pause >nul
