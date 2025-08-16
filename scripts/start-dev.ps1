# YuYu Lolita Shopping - Development Startup Script
# Starts both API and Web app in separate windows

param(
    [switch]$NoNewWindows = $false,
    [switch]$SkipBrowser = $false
)

Write-Host "[DEV] Starting YuYu Lolita Shopping - Development Mode" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green

# Get the project root directory
$projectRoot = Split-Path -Parent $PSScriptRoot

# Function to check if PostgreSQL is running
function Test-PostgreSQL {
    try {
        # Get all PostgreSQL services and prioritize v16
        $pgServices = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
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
        
        if ($targetService -and $targetService.Status -eq "Running") {
            return $true
        }
        
        # Alternative check using psql command
        $null = psql --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            # Try to connect to test if server is running
            $env:PGPASSWORD = "password"
            $testResult = psql -h localhost -U postgres -d postgres -c "SELECT 1;" 2>$null
            return $LASTEXITCODE -eq 0
        }
        
        return $false
    }
    catch {
        return $false
    }
}

# Function to get the target PostgreSQL service
function Get-TargetPostgreSQLService {
    $pgServices = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
    if ($pgServices) {
        $targetService = $pgServices | Where-Object { $_.Name -like "*16*" } | Select-Object -First 1
        if (-not $targetService) {
            $targetService = $pgServices | Where-Object { $_.Name -like "*15*" } | Select-Object -First 1
        }
        if (-not $targetService) {
            $targetService = $pgServices | Select-Object -First 1
        }
        return $targetService
    }
    return $null
}

# Step 1: Check PostgreSQL
Write-Host "[DB] Checking PostgreSQL..." -ForegroundColor Cyan
if (Test-PostgreSQL) {
    Write-Host "[SUCCESS] PostgreSQL is running" -ForegroundColor Green
}
else {
    Write-Host "[WARNING] PostgreSQL is not running or not accessible" -ForegroundColor Yellow
    Write-Host "          Attempting to start PostgreSQL service..." -ForegroundColor Yellow
    
    try {
        $targetService = Get-TargetPostgreSQLService
        if ($targetService) {
            Write-Host "          Attempting to start: $($targetService.DisplayName)" -ForegroundColor White
            Start-Service $targetService.Name -ErrorAction Stop
            Start-Sleep -Seconds 3
            Write-Host "[SUCCESS] PostgreSQL service started" -ForegroundColor Green
        }
        else {
            Write-Host "[ERROR] PostgreSQL service not found. Please ensure PostgreSQL is installed." -ForegroundColor Red
            Write-Host "        Install from: https://www.postgresql.org/download/windows/" -ForegroundColor White
        }
    }
    catch {
        Write-Host "[WARNING] Failed to start PostgreSQL service: $_" -ForegroundColor Yellow
        Write-Host "          Please start PostgreSQL manually or run as Administrator" -ForegroundColor White
        Write-Host "          You can also try: net start postgresql-x64-16" -ForegroundColor White
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

# Set development environment variables
$env:NODE_ENV = "development"
$env:WEB_PORT = "5173"
$env:HOST = "localhost"
$env:API_PORT = "3001"
$env:API_HOST = "localhost"

# Explicitly remove PORT to avoid conflicts
$env:PORT = $null

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
    Start-Process bun -ArgumentList "--filter=@yuyu/api", "dev" -WorkingDirectory $projectRoot -WindowStyle Hidden
    
    Start-Sleep -Seconds 3
    
    Write-Host "[INFO] Starting Web app..." -ForegroundColor Yellow
    bun --filter=@yuyu/web dev
}
else {
    # Start API server in new window
    Write-Host "[API] Starting API server in new window..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\apps\api'; `$env:NODE_ENV='development'; `$env:API_PORT='3001'; `$env:API_HOST='localhost'; Remove-Item Env:PORT -ErrorAction SilentlyContinue; Write-Host '[API] YuYu Lolita API Server' -ForegroundColor Green; Write-Host 'Environment: API_PORT=3001, API_HOST=localhost' -ForegroundColor Cyan; bun run dev:windows"
    
    # Wait a moment for API to start
    Start-Sleep -Seconds 3
    
    # Start Web app in new window
    Write-Host "[WEB] Starting Web app in new window..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\apps\web'; `$env:NODE_ENV='development'; `$env:WEB_PORT='5173'; `$env:HOST='localhost'; Remove-Item Env:API_PORT -ErrorAction SilentlyContinue; Write-Host '[WEB] YuYu Lolita Web App' -ForegroundColor Blue; Write-Host 'Environment: WEB_PORT=5173, HOST=localhost' -ForegroundColor Cyan; bun run dev:windows"
    
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