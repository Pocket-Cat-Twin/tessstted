# YuYu Lolita Shopping - Production Startup Script
# Builds and starts the application in production mode

param(
    [switch]$SkipBuild = $false,
    [switch]$Daemon = $false,
    [string]$LogDir = "logs"
)

Write-Host "[PROD] Starting YuYu Lolita Shopping - Production Mode" -ForegroundColor Green
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
    Write-Host "[ERROR] PostgreSQL is not running. Starting service..." -ForegroundColor Red
    try {
        $targetService = Get-TargetPostgreSQLService
        if ($targetService) {
            Write-Host "          Attempting to start: $($targetService.DisplayName)" -ForegroundColor White
            Start-Service $targetService.Name -ErrorAction Stop
            Start-Sleep -Seconds 3
            Write-Host "[SUCCESS] PostgreSQL service started" -ForegroundColor Green
        }
        else {
            Write-Host "[ERROR] PostgreSQL service not found. Cannot start production without database." -ForegroundColor Red
            exit 1
        }
    }
    catch {
        Write-Host "[ERROR] Failed to start PostgreSQL service: $_" -ForegroundColor Red
        Write-Host "        Please start PostgreSQL manually as Administrator" -ForegroundColor White
        Write-Host "        You can try: net start postgresql-x64-16" -ForegroundColor White
        exit 1
    }
}

# Step 2: Setup environment for production
Write-Host ""
Write-Host "[ENV] Setting up production environment..." -ForegroundColor Cyan
Set-Location $projectRoot

# Set production environment variables
$env:NODE_ENV = "production"

if (-not (Test-Path ".env")) {
    Write-Host "[ERROR] .env file not found. Please run setup-windows.ps1 first" -ForegroundColor Red
    exit 1
}

# Update environment for production
$envContent = Get-Content ".env"
$envContent = $envContent -replace "NODE_ENV=development", "NODE_ENV=production"
$envContent = $envContent -replace "PUBLIC_API_URL=.*", "PUBLIC_API_URL=http://localhost:3001"

# Ensure proper port configuration
if (-not ($envContent | Select-String "^API_PORT=")) {
    $envContent += "API_PORT=3001"
}
if (-not ($envContent | Select-String "^WEB_PORT=")) {
    $envContent += "WEB_PORT=5173"
}
if (-not ($envContent | Select-String "^HOST=")) {
    $envContent += "HOST=0.0.0.0"
}

$envContent | Set-Content ".env"

# Set environment variables for this session
$env:NODE_ENV = "production"
$env:API_PORT = "3001"
$env:WEB_PORT = "5173"
$env:HOST = "0.0.0.0"

# Explicitly remove PORT to avoid conflicts
$env:PORT = $null

# Step 3: Run database migrations
Write-Host ""
Write-Host "[DB] Running database migrations..." -ForegroundColor Cyan
try {
    bun run db:migrate:windows
    Write-Host "[SUCCESS] Database migrations completed" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] Database migrations failed" -ForegroundColor Red
    exit 1
}

# Step 4: Build applications
if (-not $SkipBuild) {
    Write-Host ""
    Write-Host "[BUILD] Building applications..." -ForegroundColor Cyan
    
    try {
        # Build packages first
        Write-Host "[BUILD] Building shared packages..." -ForegroundColor Yellow
        Set-Location "packages/shared"
        bun run build
        Set-Location "../.."
        
        Set-Location "packages/db"
        bun run build
        Set-Location "../.."
        
        # Build applications
        Write-Host "[BUILD] Building API..." -ForegroundColor Yellow
        bun run build:api
        
        Write-Host "[BUILD] Building Web app..." -ForegroundColor Yellow
        bun run build:web
        
        Write-Host "[SUCCESS] Build completed successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "[ERROR] Build failed" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        exit 1
    }
}

# Step 5: Create logs directory
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    Write-Host "[INFO] Created logs directory: $LogDir" -ForegroundColor Cyan
}

# Step 6: Start production servers
Write-Host ""
Write-Host "[SERVERS] Starting production servers..." -ForegroundColor Cyan

if ($Daemon) {
    # Start as background services with logging
    Write-Host "[API] Starting API server as background service..." -ForegroundColor Yellow
    $apiLogFile = Join-Path $LogDir "api.log"
    Start-Process bun -ArgumentList "--filter=@yuyu/api", "start" -WorkingDirectory $projectRoot -RedirectStandardOutput $apiLogFile -RedirectStandardError $apiLogFile -WindowStyle Hidden
    
    Start-Sleep -Seconds 3
    
    Write-Host "[WEB] Starting Web app as background service..." -ForegroundColor Yellow
    $webLogFile = Join-Path $LogDir "web.log"
    Start-Process bun -ArgumentList "--filter=@yuyu/web", "start" -WorkingDirectory $projectRoot -RedirectStandardOutput $webLogFile -RedirectStandardError $webLogFile -WindowStyle Hidden
    
    Write-Host "[SUCCESS] Services started in background" -ForegroundColor Green
    Write-Host "[LOGS] Logs are being written to:" -ForegroundColor Cyan
    Write-Host "       API: $apiLogFile" -ForegroundColor White
    Write-Host "       Web: $webLogFile" -ForegroundColor White
}
else {
    # Start API server in new window
    Write-Host "[API] Starting API server..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; `$env:NODE_ENV='production'; `$env:API_PORT='3001'; `$env:API_HOST='0.0.0.0'; Remove-Item Env:PORT -ErrorAction SilentlyContinue; Write-Host '[API] YuYu Lolita API Server - PRODUCTION' -ForegroundColor Red; Write-Host 'Environment: API_PORT=3001, API_HOST=0.0.0.0' -ForegroundColor Cyan; bun --filter=@yuyu/api start"
    
    Start-Sleep -Seconds 3
    
    # Start Web app in new window
    Write-Host "[WEB] Starting Web app..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; `$env:NODE_ENV='production'; `$env:WEB_PORT='5173'; `$env:HOST='0.0.0.0'; Remove-Item Env:API_PORT -ErrorAction SilentlyContinue; Write-Host '[WEB] YuYu Lolita Web App - PRODUCTION' -ForegroundColor Red; Write-Host 'Environment: WEB_PORT=5173, HOST=0.0.0.0' -ForegroundColor Cyan; bun --filter=@yuyu/web start:windows"
}

# Wait for services to start
Start-Sleep -Seconds 5

# Step 7: Verify services are running
Write-Host ""
Write-Host "[VERIFY] Verifying services..." -ForegroundColor Cyan

try {
    $apiResponse = Invoke-WebRequest -Uri "http://localhost:3001" -Method GET -TimeoutSec 10 -ErrorAction SilentlyContinue
    if ($apiResponse.StatusCode -eq 200) {
        Write-Host "[SUCCESS] API server is responding" -ForegroundColor Green
    }
    else {
        Write-Host "[WARNING] API server returned status: $($apiResponse.StatusCode)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "[ERROR] API server is not responding" -ForegroundColor Red
}

try {
    $webResponse = Invoke-WebRequest -Uri "http://localhost:5173" -Method GET -TimeoutSec 10 -ErrorAction SilentlyContinue
    if ($webResponse.StatusCode -eq 200) {
        Write-Host "[SUCCESS] Web app is responding" -ForegroundColor Green
    }
    else {
        Write-Host "[WARNING] Web app returned status: $($webResponse.StatusCode)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "[ERROR] Web app is not responding" -ForegroundColor Red
}

# Display access information
Write-Host ""
Write-Host "[COMPLETE] Production servers started!" -ForegroundColor Green
Write-Host "=============================" -ForegroundColor Green
Write-Host ""
Write-Host "[ACCESS] Access URLs:" -ForegroundColor Cyan
Write-Host "         Web App: http://localhost:5173" -ForegroundColor White
Write-Host "         API: http://localhost:3001" -ForegroundColor White
Write-Host "         API Docs: http://localhost:3001/swagger" -ForegroundColor White
Write-Host ""

if ($Daemon) {
    Write-Host "[STATUS] Services running in background" -ForegroundColor Yellow
    Write-Host "         Use Task Manager to stop processes if needed" -ForegroundColor White
    Write-Host "         Or run: Get-Process bun | Stop-Process" -ForegroundColor White
}
else {
    Write-Host "[STOP] To stop servers:" -ForegroundColor Yellow
    Write-Host "       Close the PowerShell windows or press Ctrl+C in each" -ForegroundColor White
}

Write-Host ""
Write-Host "[SECURITY] Security reminders:" -ForegroundColor Red
Write-Host "           - Update JWT_SECRET in .env" -ForegroundColor White
Write-Host "           - Use strong PostgreSQL password" -ForegroundColor White
Write-Host "           - Configure Windows Firewall properly" -ForegroundColor White
Write-Host "           - Keep system and dependencies updated" -ForegroundColor White