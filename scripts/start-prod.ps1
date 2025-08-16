# YuYu Lolita Shopping - Production Startup Script
# Builds and starts the application in production mode

param(
    [switch]$SkipBuild = $false,
    [switch]$Daemon = $false,
    [string]$LogDir = "logs"
)

Write-Host "🚀 Starting YuYu Lolita Shopping - Production Mode" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green

# Get the project root directory
$projectRoot = Split-Path -Parent $PSScriptRoot

# Function to check if PostgreSQL is running
function Test-PostgreSQL {
    try {
        $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
        if ($pgService -and $pgService.Status -eq "Running") {
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

# Step 1: Check PostgreSQL
Write-Host "🗄️  Checking PostgreSQL..." -ForegroundColor Cyan
if (Test-PostgreSQL) {
    Write-Host "✅ PostgreSQL is running" -ForegroundColor Green
}
else {
    Write-Host "❌ PostgreSQL is not running. Starting service..." -ForegroundColor Red
    try {
        $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
        if ($pgService) {
            Start-Service $pgService.Name
            Start-Sleep -Seconds 3
            Write-Host "✅ PostgreSQL service started" -ForegroundColor Green
        }
        else {
            Write-Host "❌ PostgreSQL service not found. Cannot start production without database." -ForegroundColor Red
            exit 1
        }
    }
    catch {
        Write-Host "❌ Failed to start PostgreSQL service" -ForegroundColor Red
        exit 1
    }
}

# Step 2: Setup environment for production
Write-Host "`n⚙️  Setting up production environment..." -ForegroundColor Cyan
Set-Location $projectRoot

# Set production environment variables
$env:NODE_ENV = "production"

if (-not (Test-Path ".env")) {
    Write-Host "❌ .env file not found. Please run setup-windows.ps1 first" -ForegroundColor Red
    exit 1
}

# Update environment for production
$envContent = Get-Content ".env"
$envContent = $envContent -replace "NODE_ENV=development", "NODE_ENV=production"
$envContent = $envContent -replace "PUBLIC_API_URL=.*", "PUBLIC_API_URL=http://localhost:3001"
$envContent | Set-Content ".env"

# Step 3: Run database migrations
Write-Host "`n🗄️  Running database migrations..." -ForegroundColor Cyan
try {
    bun run db:migrate:windows
    Write-Host "✅ Database migrations completed" -ForegroundColor Green
}
catch {
    Write-Host "❌ Database migrations failed" -ForegroundColor Red
    exit 1
}

# Step 4: Build applications
if (-not $SkipBuild) {
    Write-Host "`n🔨 Building applications..." -ForegroundColor Cyan
    
    try {
        # Build packages first
        Write-Host "📦 Building shared packages..." -ForegroundColor Yellow
        Set-Location "packages/shared"
        bun run build
        Set-Location "../.."
        
        Set-Location "packages/db"
        bun run build
        Set-Location "../.."
        
        # Build applications
        Write-Host "🔌 Building API..." -ForegroundColor Yellow
        bun run build:api
        
        Write-Host "🌐 Building Web app..." -ForegroundColor Yellow
        bun run build:web
        
        Write-Host "✅ Build completed successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Build failed" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        exit 1
    }
}

# Step 5: Create logs directory
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    Write-Host "📁 Created logs directory: $LogDir" -ForegroundColor Cyan
}

# Step 6: Start production servers
Write-Host "`n🚀 Starting production servers..." -ForegroundColor Cyan

if ($Daemon) {
    # Start as background services with logging
    Write-Host "🔌 Starting API server as background service..." -ForegroundColor Yellow
    $apiLogFile = Join-Path $LogDir "api.log"
    Start-Process bun -ArgumentList "--filter=@yuyu/api", "start" -WorkingDirectory $projectRoot -RedirectStandardOutput $apiLogFile -RedirectStandardError $apiLogFile -WindowStyle Hidden
    
    Start-Sleep -Seconds 3
    
    Write-Host "🌐 Starting Web app as background service..." -ForegroundColor Yellow
    $webLogFile = Join-Path $LogDir "web.log"
    Start-Process bun -ArgumentList "--filter=@yuyu/web", "start" -WorkingDirectory $projectRoot -RedirectStandardOutput $webLogFile -RedirectStandardError $webLogFile -WindowStyle Hidden
    
    Write-Host "✅ Services started in background" -ForegroundColor Green
    Write-Host "📋 Logs are being written to:" -ForegroundColor Cyan
    Write-Host "   API: $apiLogFile" -ForegroundColor White
    Write-Host "   Web: $webLogFile" -ForegroundColor White
}
else {
    # Start API server in new window
    Write-Host "🔌 Starting API server..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; `$env:NODE_ENV='production'; Write-Host '🔌 YuYu Lolita API Server - PRODUCTION' -ForegroundColor Red; bun --filter=@yuyu/api start"
    
    Start-Sleep -Seconds 3
    
    # Start Web app in new window
    Write-Host "🌐 Starting Web app..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; `$env:NODE_ENV='production'; Write-Host '🌐 YuYu Lolita Web App - PRODUCTION' -ForegroundColor Red; bun --filter=@yuyu/web start"
}

# Wait for services to start
Start-Sleep -Seconds 5

# Step 7: Verify services are running
Write-Host "`n🔍 Verifying services..." -ForegroundColor Cyan

try {
    $apiResponse = Invoke-WebRequest -Uri "http://localhost:3001" -Method GET -TimeoutSec 10 -ErrorAction SilentlyContinue
    if ($apiResponse.StatusCode -eq 200) {
        Write-Host "✅ API server is responding" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  API server returned status: $($apiResponse.StatusCode)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "❌ API server is not responding" -ForegroundColor Red
}

try {
    $webResponse = Invoke-WebRequest -Uri "http://localhost:5173" -Method GET -TimeoutSec 10 -ErrorAction SilentlyContinue
    if ($webResponse.StatusCode -eq 200) {
        Write-Host "✅ Web app is responding" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  Web app returned status: $($webResponse.StatusCode)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "❌ Web app is not responding" -ForegroundColor Red
}

# Display access information
Write-Host "`n✅ Production servers started!" -ForegroundColor Green
Write-Host "=============================" -ForegroundColor Green
Write-Host ""
Write-Host "🔗 Access URLs:" -ForegroundColor Cyan
Write-Host "   📱 Web App: http://localhost:5173" -ForegroundColor White
Write-Host "   🔌 API: http://localhost:3001" -ForegroundColor White
Write-Host "   📚 API Docs: http://localhost:3001/swagger" -ForegroundColor White
Write-Host ""

if ($Daemon) {
    Write-Host "🏃 Services running in background" -ForegroundColor Yellow
    Write-Host "   Use Task Manager to stop processes if needed" -ForegroundColor White
    Write-Host "   Or run: Get-Process bun | Stop-Process" -ForegroundColor White
}
else {
    Write-Host "🛑 To stop servers:" -ForegroundColor Yellow
    Write-Host "   Close the PowerShell windows or press Ctrl+C in each" -ForegroundColor White
}

Write-Host ""
Write-Host "🔐 Security reminders:" -ForegroundColor Red
Write-Host "   - Update JWT_SECRET in .env" -ForegroundColor White
Write-Host "   - Use strong PostgreSQL password" -ForegroundColor White
Write-Host "   - Configure Windows Firewall properly" -ForegroundColor White
Write-Host "   - Keep system and dependencies updated" -ForegroundColor White