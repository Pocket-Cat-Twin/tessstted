# YuYu Lolita Shopping - Windows Setup Script
# Complete Windows environment setup

param(
    [switch]$SkipPostgreSQL = $false,
    [switch]$SkipBun = $false,
    [string]$PostgreSQLVersion = "15"
)

Write-Host "[SETUP] YuYu Lolita Shopping - Windows Setup" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# Function to check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check for administrator privileges
if (-not (Test-Administrator)) {
    Write-Host "[WARNING] This script requires administrator privileges for some operations." -ForegroundColor Yellow
    Write-Host "          Consider running PowerShell as Administrator for full setup." -ForegroundColor Yellow
    Write-Host ""
}

# Step 1: Check/Install Bun
if (-not $SkipBun) {
    Write-Host "[STEP 1] Checking Bun installation..." -ForegroundColor Cyan
    
    try {
        $bunVersion = bun --version
        Write-Host "[SUCCESS] Bun is already installed (version: $bunVersion)" -ForegroundColor Green
    }
    catch {
        Write-Host "[INFO] Installing Bun..." -ForegroundColor Yellow
        try {
            irm bun.sh/install.ps1 | iex
            Write-Host "[SUCCESS] Bun installed successfully" -ForegroundColor Green
        }
        catch {
            Write-Host "[ERROR] Failed to install Bun. Please install manually from https://bun.sh/" -ForegroundColor Red
            Write-Host "        Alternative: npm install -g bun" -ForegroundColor Yellow
        }
    }
}

# Step 2: Check/Install PostgreSQL
if (-not $SkipPostgreSQL) {
    Write-Host ""
    Write-Host "[STEP 2] Checking PostgreSQL installation..." -ForegroundColor Cyan
    
    # Check if PostgreSQL is installed (prioritize v16)
    $pgServices = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
    $pgCommand = Get-Command psql -ErrorAction SilentlyContinue
    
    # Prefer PostgreSQL 16, then 15, then others
    $targetService = $null
    if ($pgServices) {
        $targetService = $pgServices | Where-Object { $_.Name -like "*16*" } | Select-Object -First 1
        if (-not $targetService) {
            $targetService = $pgServices | Where-Object { $_.Name -like "*15*" } | Select-Object -First 1
        }
        if (-not $targetService) {
            $targetService = $pgServices | Select-Object -First 1
        }
    }
    
    if ($targetService -or $pgCommand) {
        Write-Host "[SUCCESS] PostgreSQL is already installed" -ForegroundColor Green
        if ($targetService) {
            Write-Host "          Using service: $($targetService.DisplayName)" -ForegroundColor White
        }
        
        # Start PostgreSQL service if it's not running
        if ($targetService -and $targetService.Status -ne "Running") {
            Write-Host "[INFO] Starting PostgreSQL service: $($targetService.Name)..." -ForegroundColor Yellow
            try {
                Start-Service $targetService.Name -ErrorAction Stop
                Write-Host "[SUCCESS] PostgreSQL service started" -ForegroundColor Green
            }
            catch {
                Write-Host "[WARNING] Failed to start PostgreSQL service: $_" -ForegroundColor Yellow
                Write-Host "          Please start PostgreSQL manually or run as Administrator" -ForegroundColor White
            }
        }
        elseif ($targetService -and $targetService.Status -eq "Running") {
            Write-Host "[INFO] PostgreSQL service is already running" -ForegroundColor Green
        }
    }
    else {
        Write-Host "[WARNING] PostgreSQL not found. Please install PostgreSQL:" -ForegroundColor Yellow
        Write-Host "          1. Download from: https://www.postgresql.org/download/windows/" -ForegroundColor White
        Write-Host "          2. Or use Chocolatey: choco install postgresql$PostgreSQLVersion" -ForegroundColor White
        Write-Host "          3. Or use Scoop: scoop install postgresql" -ForegroundColor White
        Write-Host ""
        
        $response = Read-Host "Do you want to continue setup without PostgreSQL? (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-Host "[ERROR] Setup cancelled. Please install PostgreSQL and run again." -ForegroundColor Red
            exit 1
        }
    }
}

# Step 3: Install Node.js dependencies
Write-Host ""
Write-Host "[STEP 3] Installing project dependencies..." -ForegroundColor Cyan
try {
    Set-Location $PSScriptRoot\..
    bun install
    Write-Host "[SUCCESS] Dependencies installed successfully" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}

# Step 4: Setup environment file
Write-Host ""
Write-Host "[STEP 4] Setting up environment configuration..." -ForegroundColor Cyan

$envFile = ".env"
$envWindowsTemplate = ".env.windows"

if (Test-Path $envWindowsTemplate) {
    Write-Host "[INFO] Using Windows environment template..." -ForegroundColor Yellow
    Copy-Item $envWindowsTemplate $envFile -Force
    Write-Host "[SUCCESS] Environment file created from Windows template" -ForegroundColor Green
}
elseif (-not (Test-Path $envFile)) {
    Write-Host "[INFO] Creating default environment file..." -ForegroundColor Yellow
    
    # Create the environment file content as a string variable
    $envContent = @"
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/yuyu_lolita

# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production

# API Configuration
API_PORT=3001
API_HOST=localhost

# Web App Configuration
PUBLIC_API_URL=http://localhost:3001

# Email Configuration (for user registration)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yuyulolita.com

# File Upload Configuration
MAX_FILE_SIZE=10485760
UPLOAD_DIR=uploads
ALLOWED_FILE_TYPES=image/jpeg,image/jpg,image/png,image/gif,image/webp

# External APIs
CURRENCY_API_KEY=your-currency-api-key
CURRENCY_API_URL=https://api.exchangerate-api.com/v4/latest/CNY

# Environment
NODE_ENV=development
CORS_ORIGIN=http://localhost:5173
SKIP_SEED=false

# Security
BCRYPT_ROUNDS=12
SESSION_SECRET=your-session-secret-change-this-in-production
"@
    
    # Write the content to file
    $envContent | Out-File -FilePath $envFile -Encoding UTF8
    Write-Host "[SUCCESS] Default environment file created" -ForegroundColor Green
}
else {
    Write-Host "[SUCCESS] Environment file already exists" -ForegroundColor Green
}

# Step 5: Setup database
Write-Host ""
Write-Host "[STEP 5] Setting up database..." -ForegroundColor Cyan
try {
    bun run db:setup:windows
    Write-Host "[SUCCESS] Database setup completed" -ForegroundColor Green
}
catch {
    Write-Host "[WARNING] Database setup failed or skipped" -ForegroundColor Yellow
    Write-Host "          You may need to setup PostgreSQL manually and run: bun run db:migrate" -ForegroundColor White
}

# Step 6: Build packages
Write-Host ""
Write-Host "[STEP 6] Building packages..." -ForegroundColor Cyan
try {
    # Build shared package
    Set-Location "packages/shared"
    bun run build
    Set-Location "../.."
    
    # Build db package  
    Set-Location "packages/db"
    bun run build
    Set-Location "../.."
    
    Write-Host "[SUCCESS] Packages built successfully" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] Failed to build packages" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}

# Final instructions
Write-Host ""
Write-Host "[COMPLETE] Setup completed!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "[NEXT] To start development:" -ForegroundColor Cyan
Write-Host "       .\scripts\start-dev.ps1" -ForegroundColor White
Write-Host ""
Write-Host "[NEXT] To start production:" -ForegroundColor Cyan  
Write-Host "       .\scripts\start-prod.ps1" -ForegroundColor White
Write-Host ""
Write-Host "[NEXT] Or run individual commands:" -ForegroundColor Cyan
Write-Host "       bun run dev:windows" -ForegroundColor White
Write-Host ""
Write-Host "[ACCESS] Access URLs:" -ForegroundColor Cyan
Write-Host "         Web App: http://localhost:5173" -ForegroundColor White
Write-Host "         API: http://localhost:3001" -ForegroundColor White
Write-Host "         API Docs: http://localhost:3001/swagger" -ForegroundColor White

Write-Host ""
Write-Host "[REMINDER] Remember to:" -ForegroundColor Yellow
Write-Host "           1. Update .env file with your actual credentials" -ForegroundColor White
Write-Host "           2. Configure PostgreSQL with proper password" -ForegroundColor White
Write-Host "           3. Add project folder to Windows Defender exclusions" -ForegroundColor White