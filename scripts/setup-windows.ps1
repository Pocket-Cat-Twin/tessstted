# Lolita Fashion Shopping - Windows Setup Script
# Complete Windows environment setup

param(
    [switch]$SkipMySQL = $false,
    [switch]$SkipBun = $false,
    [string]$MySQLVersion = "8.0"
)

Write-Host "[SETUP] Lolita Fashion Shopping - Windows Setup" -ForegroundColor Green
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

# Step 2: Check/Install MySQL8
if (-not $SkipMySQL) {
    Write-Host ""
    Write-Host "[STEP 2] Checking MySQL8 installation..." -ForegroundColor Cyan
    
    # Check if MySQL is installed
    $mysqlServices = Get-Service -Name "MySQL*" -ErrorAction SilentlyContinue
    $mysqlCommand = Get-Command mysql -ErrorAction SilentlyContinue
    
    # Look for MySQL service (prefer MySQL80)
    $targetService = $null
    if ($mysqlServices) {
        $targetService = $mysqlServices | Where-Object { $_.Name -like "*80*" } | Select-Object -First 1
        if (-not $targetService) {
            $targetService = $mysqlServices | Select-Object -First 1
        }
    }
    
    if ($targetService -or $mysqlCommand) {
        Write-Host "[SUCCESS] MySQL is already installed" -ForegroundColor Green
        if ($targetService) {
            Write-Host "          Using service: $($targetService.DisplayName)" -ForegroundColor White
        }
        
        # Start MySQL service if it's not running
        if ($targetService -and $targetService.Status -ne "Running") {
            Write-Host "[INFO] Starting MySQL service: $($targetService.Name)..." -ForegroundColor Yellow
            try {
                Start-Service $targetService.Name -ErrorAction Stop
                Write-Host "[SUCCESS] MySQL service started" -ForegroundColor Green
            }
            catch {
                Write-Host "[WARNING] Failed to start MySQL service: $_" -ForegroundColor Yellow
                Write-Host "          Please start MySQL manually or run as Administrator" -ForegroundColor White
            }
        }
        elseif ($targetService -and $targetService.Status -eq "Running") {
            Write-Host "[INFO] MySQL service is already running" -ForegroundColor Green
        }
    }
    else {
        Write-Host "[WARNING] MySQL not found. Please install MySQL8:" -ForegroundColor Yellow
        Write-Host "          1. Download from: https://dev.mysql.com/downloads/windows/" -ForegroundColor White
        Write-Host "          2. Or use Chocolatey: choco install mysql" -ForegroundColor White
        Write-Host "          3. Or use Scoop: scoop install mysql" -ForegroundColor White
        Write-Host ""
        
        $response = Read-Host "Do you want to continue setup without MySQL? (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-Host "[ERROR] Setup cancelled. Please install MySQL8 and run again." -ForegroundColor Red
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
$envMySQLTemplate = ".env.mysql"

if (Test-Path $envMySQLTemplate) {
    Write-Host "[INFO] Using MySQL environment template..." -ForegroundColor Yellow
    Copy-Item $envMySQLTemplate $envFile -Force
    Write-Host "[SUCCESS] Environment file created from MySQL template" -ForegroundColor Green
}
elseif (-not (Test-Path $envFile)) {
    Write-Host "[INFO] Creating default MySQL environment file..." -ForegroundColor Yellow
    
    # Create the environment file content as a string variable
    $envContent = @"
# API Configuration
API_HOST=localhost
API_PORT=3001
CORS_ORIGIN=http://localhost:5173

# Web App Configuration
WEB_PORT=5173
HOST=0.0.0.0
PUBLIC_API_URL=http://localhost:3001

# Database Configuration (MySQL8)
DB_HOST=localhost
DB_PORT=3306
DB_NAME=yuyu_lolita
DB_USER=root
DB_PASSWORD=

# JWT Configuration
JWT_SECRET=mysql-jwt-secret-change-in-production

# Environment
NODE_ENV=development
SKIP_SEED=false

# Email Configuration (optional for development)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yuyulolita.com

# SMS Configuration (optional for development)  
SMS_PROVIDER=mock
SMS_RU_API_ID=your-sms-ru-api-id
SMS_RU_API_KEY=your-sms-ru-api-key
"@
    
    # Write the content to file
    $envContent | Out-File -FilePath $envFile -Encoding UTF8
    Write-Host "[SUCCESS] Default MySQL environment file created" -ForegroundColor Green
}
else {
    Write-Host "[SUCCESS] Environment file already exists" -ForegroundColor Green
}

# Step 5: Setup database
Write-Host ""
Write-Host "[STEP 5] Setting up MySQL database..." -ForegroundColor Cyan
try {
    bun run db:setup:mysql
    Write-Host "[SUCCESS] MySQL database setup completed" -ForegroundColor Green
}
catch {
    Write-Host "[WARNING] MySQL database setup failed or skipped" -ForegroundColor Yellow
    Write-Host "          You may need to setup MySQL manually and run: bun run db:migrate:mysql" -ForegroundColor White
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
Write-Host "           2. Configure MySQL8 with proper root password" -ForegroundColor White
Write-Host "           3. Create 'yuyu_lolita' database in MySQL" -ForegroundColor White
Write-Host "           4. Add project folder to Windows Defender exclusions" -ForegroundColor White