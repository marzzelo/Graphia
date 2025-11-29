# ============================================================================
#  Graphia Plugin System - Installation Script (PowerShell)
#  This script installs all dependencies required by the Graph plugins
#  into a local .packages folder using pip --target.
# ============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host " ============================================" -ForegroundColor Cyan
Write-Host "  Graphia Plugin System - Installer" -ForegroundColor Cyan
Write-Host " ============================================" -ForegroundColor Cyan
Write-Host ""

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Look for Graph's Python executable (one level up from Plugins)
$GraphPython = Join-Path $ScriptDir "..\Python\python.exe"

if (-not (Test-Path $GraphPython)) {
    Write-Host "[ERROR] Graph's Python executable not found at:" -ForegroundColor Red
    Write-Host "        $GraphPython" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please make sure this script is located in the Graph\Plugins folder." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[INFO] Found Graph's Python at: $GraphPython" -ForegroundColor Green
Write-Host ""

# Check and fix python37._pth if needed (enables site-packages)
$PthFile = Join-Path (Split-Path $GraphPython) "python37._pth"
if (Test-Path $PthFile) {
    $pthContent = Get-Content $PthFile -Raw
    if ($pthContent -match '#import site') {
        Write-Host "[INFO] Enabling site-packages in Python configuration..." -ForegroundColor Cyan
        $newContent = $pthContent -replace '#import site', 'import site'
        Set-Content -Path $PthFile -Value $newContent -NoNewline
        Write-Host "[OK] Python configuration updated." -ForegroundColor Green
        Write-Host ""
    }
}

# Set packages directory
$PackagesDir = Join-Path $ScriptDir ".packages"

# Check if .packages already exists
if (Test-Path $PackagesDir) {
    Write-Host "[WARNING] Packages folder already exists." -ForegroundColor Yellow
    $overwrite = Read-Host "Do you want to reinstall packages? (y/N)"
    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        Write-Host "[INFO] Keeping existing packages." -ForegroundColor Cyan
    } else {
        Write-Host "[INFO] Removing existing packages..." -ForegroundColor Cyan
        Remove-Item -Recurse -Force $PackagesDir
        $installPackages = $true
    }
} else {
    $installPackages = $true
}

if ($installPackages) {
    # Install packages to local folder
    Write-Host "[INFO] Installing required packages to .packages folder..." -ForegroundColor Cyan
    Write-Host "       This may take a few minutes..." -ForegroundColor Gray
    Write-Host ""
    
    # Create packages directory
    New-Item -ItemType Directory -Path $PackagesDir -Force | Out-Null
    
    # Check if pip is available, if not download and install it
    $pipCheck = & $GraphPython -m pip --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[INFO] pip not found, downloading get-pip.py..." -ForegroundColor Cyan
        
        # Download get-pip.py (Python 3.7 compatible version)
        $getPipPath = Join-Path $ScriptDir "get-pip.py"
        try {
            Invoke-WebRequest -Uri "https://bootstrap.pypa.io/pip/3.7/get-pip.py" -OutFile $getPipPath
        } catch {
            Write-Host "[ERROR] Failed to download get-pip.py: $_" -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
        
        Write-Host "[INFO] Installing pip..." -ForegroundColor Cyan
        & $GraphPython $getPipPath --no-warn-script-location
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Failed to install pip." -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
        
        Write-Host "[OK] pip installed successfully." -ForegroundColor Green
        Write-Host ""
        
        # Clean up
        Remove-Item $getPipPath -Force -ErrorAction SilentlyContinue
    }
    
    # Install from requirements.txt to target folder
    $RequirementsPath = Join-Path $ScriptDir "requirements.txt"
    if (Test-Path $RequirementsPath) {
        & $GraphPython -m pip install -r $RequirementsPath --target $PackagesDir --upgrade
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Failed to install some packages." -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
    } else {
        Write-Host "[WARNING] requirements.txt not found. Installing default packages..." -ForegroundColor Yellow
        & $GraphPython -m pip install numpy==1.21.6 scipy==1.7.3 "Pillow<10.0.0" "urllib3<2.0.0" "requests<2.32.0" openai==0.28.1 "pydantic<2.0.0" "python-dotenv<1.0.0" --target $PackagesDir --upgrade
    }
    
    Write-Host ""
    Write-Host "[OK] All packages installed successfully!" -ForegroundColor Green
    Write-Host ""
}

# Verify installation
Write-Host "[INFO] Verifying installation..." -ForegroundColor Cyan
$env:PYTHONPATH = $PackagesDir
& $GraphPython -c "import sys; sys.path.insert(0, r'$PackagesDir'); import numpy; print('  - NumPy:', numpy.__version__)"
& $GraphPython -c "import sys; sys.path.insert(0, r'$PackagesDir'); import scipy; print('  - SciPy:', scipy.__version__)"
& $GraphPython -c "import sys; sys.path.insert(0, r'$PackagesDir'); import PIL; print('  - Pillow:', PIL.__version__)"
& $GraphPython -c "import sys; sys.path.insert(0, r'$PackagesDir'); import openai; print('  - OpenAI:', openai.__version__)"
& $GraphPython -c "import sys; sys.path.insert(0, r'$PackagesDir'); import pydantic; print('  - Pydantic:', pydantic.VERSION)"
& $GraphPython -c "import sys; sys.path.insert(0, r'$PackagesDir'); from dotenv import load_dotenv; print('  - python-dotenv: OK')"

Write-Host ""
Write-Host " ============================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host " ============================================" -ForegroundColor Green
Write-Host ""
Write-Host " You can now restart Graph to use the plugins." -ForegroundColor White
Write-Host ""
Write-Host " Optional: Create a .env file in this folder" -ForegroundColor Gray
Write-Host " with your OpenAI API key for AI features:" -ForegroundColor Gray
Write-Host ""
Write-Host "   OPENAI_API_KEY=sk-your-key-here" -ForegroundColor Yellow
Write-Host "   OPENAI_MODEL=gpt-4o-mini" -ForegroundColor Yellow
Write-Host ""

Read-Host "Press Enter to exit"
