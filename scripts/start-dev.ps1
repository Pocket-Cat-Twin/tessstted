# Lolita Fashion Shopping - Development Startup Script
# Starts both API and Web app in separate windows

param(
    [switch]$NoNewWindows = $false,
    [switch]$SkipBrowser = $false
)

Write-Host "[DEV] Starting Lolita Fashion Shopping - Development Mode" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green

# Get the project root directory
$projectRoot = Split-Path -Parent $PSScriptRoot

# Function to check if MySQL is running
function Test-MySQL {
    try {
        # Get all MySQL services
        $mysqlServices = Get-Service -Name "MySQL*" -ErrorAction SilentlyContinue
        $targetService = $null
        
        if ($mysqlServices) {
            $targetService = $mysqlServices | Where-Object { $_.Name -like "*80*" } | Select-Object -First 1
            if (-not $targetService) {
                $targetService = $mysqlServices | Select-Object -First 1
            }
        }
        
        if ($targetService -and $targetService.Status -eq "Running") {
            return $true
        }
        
        # Alternative check using mysql command
        $null = mysql --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            # Try to connect to test if server is running
            $testResult = mysql -h localhost -u root -e "SELECT 1;" 2>$null
            return $LASTEXITCODE -eq 0
        }
        
        return $false
    }
    catch {
        return $false
    }
}

# Function to get the target MySQL service
function Get-TargetMySQLService {
    $mysqlServices = Get-Service -Name "MySQL*" -ErrorAction SilentlyContinue
    if ($mysqlServices) {
        $targetService = $mysqlServices | Where-Object { $_.Name -like "*80*" } | Select-Object -First 1
        if (-not $targetService) {
            $targetService = $mysqlServices | Select-Object -First 1
        }
        return $targetService
    }
    return $null
}

# Step 1: Check MySQL8
Write-Host "[DB] Checking MySQL8..." -ForegroundColor Cyan
if (Test-MySQL) {
    Write-Host "[SUCCESS] MySQL8 is running" -ForegroundColor Green
}
else {
    Write-Host "[WARNING] MySQL8 is not running or not accessible" -ForegroundColor Yellow
    Write-Host "          Attempting to start MySQL service..." -ForegroundColor Yellow
    
    try {
        $targetService = Get-TargetMySQLService
        if ($targetService) {
            Write-Host "          Attempting to start: $($targetService.DisplayName)" -ForegroundColor White
            Start-Service $targetService.Name -ErrorAction Stop
            Start-Sleep -Seconds 3
            Write-Host "[SUCCESS] MySQL service started" -ForegroundColor Green
        }
        else {
            Write-Host "[ERROR] MySQL service not found. Please ensure MySQL8 is installed." -ForegroundColor Red
            Write-Host "        Install from: https://dev.mysql.com/downloads/windows/" -ForegroundColor White
        }
    }
    catch {
        Write-Host "[WARNING] Failed to start MySQL service: $_" -ForegroundColor Yellow
        Write-Host "          Please start MySQL manually or run as Administrator" -ForegroundColor White
        Write-Host "          You can also try: net start MySQL80" -ForegroundColor White
    }
}

# Step 2: Setup environment
Write-Host ""
Write-Host "[ENV] Checking environment..." -ForegroundColor Cyan
Set-Location $projectRoot

if (-not (Test-Path ".env")) {
    Write-Host "[WARNING] .env file not found. Creating from template..." -ForegroundColor Yellow
    if (Test-Path ".env.windows") {
        Copy-Item ".env.windows" ".env"
        Write-Host "[SUCCESS] Environment file created" -ForegroundColor Green
    }
    else {
        Write-Host "[ERROR] No environment template found. Please run setup-windows.ps1 first" -ForegroundColor Red
        exit 1
    }
}

# Load and validate .env file variables into current session
Write-Host "[ENV] Loading environment variables from .env..." -ForegroundColor Cyan
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]*)\s*=\s*(.*)\s*$") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            if ($name -and $value) {
                [Environment]::SetEnvironmentVariable($name, $value, [System.EnvironmentVariableTarget]::Process)
                Write-Host "   Loaded: $name" -ForegroundColor Green
            }
        }
    }
    Write-Host "[SUCCESS] Environment variables loaded from .env" -ForegroundColor Green
} else {
    Write-Host "[WARNING] .env file not found, using defaults" -ForegroundColor Yellow
}

# Set development environment variables with explicit Process scope
[Environment]::SetEnvironmentVariable("NODE_ENV", "development", [System.EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable("WEB_PORT", "5173", [System.EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable("HOST", "localhost", [System.EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable("API_PORT", "3001", [System.EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable("API_HOST", "localhost", [System.EnvironmentVariableTarget]::Process)

# Explicitly remove PORT to avoid conflicts
[Environment]::SetEnvironmentVariable("PORT", $null, [System.EnvironmentVariableTarget]::Process)

# Validate critical environment variables
Write-Host "[ENV] Validating critical environment variables..." -ForegroundColor Cyan
$requiredVars = @("DATABASE_URL", "API_PORT", "WEB_PORT")
$missingVars = @()

foreach ($var in $requiredVars) {
    $value = [Environment]::GetEnvironmentVariable($var)
    if (-not $value) {
        $missingVars += $var
        Write-Host "   Missing: $var" -ForegroundColor Red
    } else {
        $maskedValue = if ($var -eq "DATABASE_URL") { 
            $value -replace ":[^@]*@", ":***@" 
        } else { 
            $value 
        }
        Write-Host "   Valid: $var = $maskedValue" -ForegroundColor Green
    }
}

if ($missingVars.Count -gt 0) {
    Write-Host "[ERROR] Missing required environment variables: $($missingVars -join ', ')" -ForegroundColor Red
    Write-Host "        Please check your .env file and ensure all required variables are set." -ForegroundColor White
    exit 1
}

Write-Host "[SUCCESS] Environment validation completed" -ForegroundColor Green

# Step 3: Run database migrations if needed
Write-Host ""
Write-Host "[DB] Checking database migrations..." -ForegroundColor Cyan
try {
    bun run db:migrate:windows
    Write-Host "[SUCCESS] Database migrations completed" -ForegroundColor Green
}
catch {
    Write-Host "[WARNING] Database migrations failed or skipped" -ForegroundColor Yellow
}

# Step 4: Start development servers
Write-Host ""
Write-Host "[SERVERS] Starting development servers..." -ForegroundColor Cyan

if ($NoNewWindows) {
    # Start both in the same terminal (background API)
    Write-Host "[INFO] Starting API server in background..." -ForegroundColor Yellow
    Start-Process bun -ArgumentList "--filter=@lolita-fashion/api", "dev" -WorkingDirectory $projectRoot -WindowStyle Hidden
    
    Start-Sleep -Seconds 3
    
    Write-Host "[INFO] Starting Web app..." -ForegroundColor Yellow
    bun --filter=@lolita-fashion/web dev
}
else {
    # Start API server in new window with full environment inheritance
    Write-Host "[API] Starting API server in new window..." -ForegroundColor Yellow
    $apiCommand = @"
cd '$projectRoot\apps\api'
Write-Host '[API] Lolita Fashion API Server' -ForegroundColor Green

# Set environment variables using safer `$env: syntax
`$env:NODE_ENV = 'development'
`$env:API_PORT = '3001' 
`$env:API_HOST = 'localhost'
`$env:WEB_PORT = `$null
`$env:HOST = `$null
Remove-Item Env:PORT -ErrorAction SilentlyContinue

Write-Host "Environment variables:" -ForegroundColor Cyan
Write-Host "  NODE_ENV: `$env:NODE_ENV" -ForegroundColor White
Write-Host "  API_PORT: `$env:API_PORT" -ForegroundColor White
Write-Host "  API_HOST: `$env:API_HOST" -ForegroundColor White

Write-Host 'Starting API server...' -ForegroundColor Green
bun --hot src/index.ts
"@
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $apiCommand
    
    # Wait a moment for API to start
    Start-Sleep -Seconds 3
    
    # Start Web app in new window with full environment inheritance
    Write-Host "[WEB] Starting Web app in new window..." -ForegroundColor Yellow
    $webCommand = @"
cd '$projectRoot\apps\web'
Write-Host '[WEB] Lolita Fashion Web App' -ForegroundColor Blue

# Set environment variables using safer `$env: syntax  
`$env:NODE_ENV = 'development'
`$env:WEB_PORT = '5173'
`$env:HOST = 'localhost'
`$env:API_PORT = `$null
Remove-Item Env:API_PORT -ErrorAction SilentlyContinue

Write-Host "Environment variables:" -ForegroundColor Cyan
Write-Host "  NODE_ENV: `$env:NODE_ENV" -ForegroundColor White
Write-Host "  WEB_PORT: `$env:WEB_PORT" -ForegroundColor White
Write-Host "  HOST: `$env:HOST" -ForegroundColor White

Write-Host 'Starting Web server...' -ForegroundColor Blue
vite dev --host localhost
"@
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $webCommand
    
    # Wait for services to start
    Start-Sleep -Seconds 5
}

# Step 5: Open browser
if (-not $SkipBrowser) {
    Write-Host ""
    Write-Host "[BROWSER] Opening browser..." -ForegroundColor Cyan
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:5173"
}

# Display access information
Write-Host ""
Write-Host "[COMPLETE] Development servers started!" -ForegroundColor Green
Write-Host "=============================" -ForegroundColor Green
Write-Host ""
Write-Host "[ACCESS] Access URLs:" -ForegroundColor Cyan
Write-Host "         Web App: http://localhost:5173" -ForegroundColor White
Write-Host "         API: http://localhost:3001" -ForegroundColor White
Write-Host "         API Docs: http://localhost:3001/swagger" -ForegroundColor White
Write-Host ""
Write-Host "[STOP] To stop servers:" -ForegroundColor Yellow
Write-Host "       Close the PowerShell windows or press Ctrl+C in each" -ForegroundColor White
Write-Host ""
Write-Host "[HELP] Troubleshooting:" -ForegroundColor Cyan
Write-Host "       - Check that PostgreSQL is running" -ForegroundColor White
Write-Host "       - Verify .env configuration" -ForegroundColor White
Write-Host "       - Check Windows Firewall settings for ports 3001, 5173" -ForegroundColor White