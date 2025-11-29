@echo off
REM ============================================================================
REM  Graphia Plugin System - Installation Script
REM  This script installs all dependencies required by the Graph plugins
REM  into a local .packages folder using pip --target.
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo  ============================================
echo   Graphia Plugin System - Installer
echo  ============================================
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Look for Graph's Python executable (one level up from Plugins)
set "GRAPH_PYTHON=%SCRIPT_DIR%..\Python\python.exe"

if not exist "%GRAPH_PYTHON%" (
    echo [ERROR] Graph's Python executable not found at:
    echo         %GRAPH_PYTHON%
    echo.
    echo Please make sure this script is located in the Graph\Plugins folder.
    echo.
    pause
    exit /b 1
)

echo [INFO] Found Graph's Python at: %GRAPH_PYTHON%
echo.

REM Check and fix python37._pth if needed (enables site-packages)
set "PTH_FILE=%SCRIPT_DIR%..\Python\python37._pth"
if exist "%PTH_FILE%" (
    findstr /C:"#import site" "%PTH_FILE%" >nul 2>&1
    if not errorlevel 1 (
        echo [INFO] Enabling site-packages in Python configuration...
        powershell -Command "(Get-Content '%PTH_FILE%') -replace '#import site', 'import site' | Set-Content '%PTH_FILE%'"
        echo [OK] Python configuration updated.
        echo.
    )
)

REM Set packages directory
set "PACKAGES_DIR=%SCRIPT_DIR%.packages"

REM Check if .packages already exists
if exist "%PACKAGES_DIR%" (
    echo [WARNING] Packages folder already exists.
    set /p "OVERWRITE=Do you want to reinstall packages? (y/N): "
    if /i not "!OVERWRITE!"=="y" (
        echo [INFO] Keeping existing packages.
        goto :verify
    )
    echo [INFO] Removing existing packages...
    rmdir /s /q "%PACKAGES_DIR%"
)

:install_packages
REM Install packages to local folder
echo [INFO] Installing required packages to .packages folder...
echo        This may take a few minutes...
echo.

REM Create packages directory
mkdir "%PACKAGES_DIR%" 2>nul

REM Check if pip is available, if not download and install it
"%GRAPH_PYTHON%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] pip not found, downloading get-pip.py...
    
    REM Download get-pip.py using PowerShell
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/pip/3.7/get-pip.py' -OutFile '%SCRIPT_DIR%get-pip.py'"
    
    if not exist "%SCRIPT_DIR%get-pip.py" (
        echo [ERROR] Failed to download get-pip.py
        pause
        exit /b 1
    )
    
    echo [INFO] Installing pip...
    "%GRAPH_PYTHON%" "%SCRIPT_DIR%get-pip.py" --no-warn-script-location
    
    if errorlevel 1 (
        echo [ERROR] Failed to install pip.
        pause
        exit /b 1
    )
    
    echo [OK] pip installed successfully.
    echo.
    
    REM Clean up
    del "%SCRIPT_DIR%get-pip.py" 2>nul
)

REM Install from requirements.txt to target folder
if exist "requirements.txt" (
    "%GRAPH_PYTHON%" -m pip install -r requirements.txt --target "%PACKAGES_DIR%" --upgrade
    if errorlevel 1 (
        echo [ERROR] Failed to install some packages.
        pause
        exit /b 1
    )
) else (
    echo [WARNING] requirements.txt not found. Installing default packages...
    "%GRAPH_PYTHON%" -m pip install numpy==1.21.6 scipy==1.7.3 "Pillow<10.0.0" "urllib3<2.0.0" "requests<2.32.0" openai==0.28.1 "pydantic<2.0.0" "python-dotenv<1.0.0" --target "%PACKAGES_DIR%" --upgrade
)

echo.
echo [OK] All packages installed successfully!
echo.

:verify
REM Verify installation
echo [INFO] Verifying installation...
"%GRAPH_PYTHON%" -c "import sys; sys.path.insert(0, r'%PACKAGES_DIR%'); import numpy; print('  - NumPy:', numpy.__version__)"
"%GRAPH_PYTHON%" -c "import sys; sys.path.insert(0, r'%PACKAGES_DIR%'); import scipy; print('  - SciPy:', scipy.__version__)"
"%GRAPH_PYTHON%" -c "import sys; sys.path.insert(0, r'%PACKAGES_DIR%'); import PIL; print('  - Pillow:', PIL.__version__)"
"%GRAPH_PYTHON%" -c "import sys; sys.path.insert(0, r'%PACKAGES_DIR%'); import openai; print('  - OpenAI:', openai.__version__)"
"%GRAPH_PYTHON%" -c "import sys; sys.path.insert(0, r'%PACKAGES_DIR%'); import pydantic; print('  - Pydantic:', pydantic.VERSION)"
"%GRAPH_PYTHON%" -c "import sys; sys.path.insert(0, r'%PACKAGES_DIR%'); from dotenv import load_dotenv; print('  - python-dotenv: OK')"

echo.
echo  ============================================
echo   Installation Complete!
echo  ============================================
echo.
echo  You can now restart Graph to use the plugins.
echo.
echo  Optional: Create a .env file in this folder
echo  with your OpenAI API key for AI features:
echo.
echo    OPENAI_API_KEY=sk-your-key-here
echo    OPENAI_MODEL=gpt-4o-mini
echo.

pause
