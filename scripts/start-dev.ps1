# YuYu Lolita Shopping - Development Startup Script
# Starts both API and Web app in separate windows

param(
    [switch]$NoNewWindows = $false,
    [switch]$SkipBrowser = $false
)

Write-Host "🚀 Starting YuYu Lolita Shopping - Development Mode" -ForegroundColor Green
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

# Step 1: Check PostgreSQL
Write-Host "🗄️  Checking PostgreSQL..." -ForegroundColor Cyan
if (Test-PostgreSQL) {
    Write-Host "✅ PostgreSQL is running" -ForegroundColor Green
}
else {
    Write-Host "⚠️  PostgreSQL is not running or not accessible" -ForegroundColor Yellow
    Write-Host "   Attempting to start PostgreSQL service..." -ForegroundColor Yellow
    
    try {
        $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
        if ($pgService) {
            Start-Service $pgService.Name
            Start-Sleep -Seconds 3
            Write-Host "✅ PostgreSQL service started" -ForegroundColor Green
        }
        else {
            Write-Host "❌ PostgreSQL service not found. Please ensure PostgreSQL is installed." -ForegroundColor Red
            Write-Host "   Install from: https://www.postgresql.org/download/windows/" -ForegroundColor White
        }
    }
    catch {
        Write-Host "❌ Failed to start PostgreSQL service" -ForegroundColor Red
        Write-Host "   Please start PostgreSQL manually or check installation" -ForegroundColor White
    }
}

# Step 2: Setup environment
Write-Host "`n⚙️  Checking environment..." -ForegroundColor Cyan
Set-Location $projectRoot

if (-not (Test-Path ".env")) {
    Write-Host "⚠️  .env file not found. Creating from template..." -ForegroundColor Yellow
    if (Test-Path ".env.windows") {
        Copy-Item ".env.windows" ".env"
        Write-Host "✅ Environment file created" -ForegroundColor Green
    }
    else {
        Write-Host "❌ No environment template found. Please run setup-windows.ps1 first" -ForegroundColor Red
        exit 1
    }
}

# Step 3: Run database migrations if needed
Write-Host "`n🗄️  Checking database migrations..." -ForegroundColor Cyan
try {
    bun run db:migrate:windows
    Write-Host "✅ Database migrations completed" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Database migrations failed or skipped" -ForegroundColor Yellow
}

# Step 4: Start development servers
Write-Host "`n🚀 Starting development servers..." -ForegroundColor Cyan

if ($NoNewWindows) {
    # Start both in the same terminal (background API)
    Write-Host "Starting API server in background..." -ForegroundColor Yellow
    Start-Process bun -ArgumentList "--filter=@yuyu/api", "dev" -WorkingDirectory $projectRoot -WindowStyle Hidden
    
    Start-Sleep -Seconds 3
    
    Write-Host "Starting Web app..." -ForegroundColor Yellow
    bun --filter=@yuyu/web dev
}
else {
    # Start API server in new window
    Write-Host "🔌 Starting API server in new window..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\apps\api'; Write-Host '🔌 YuYu Lolita API Server' -ForegroundColor Green; bun run dev:windows"
    
    # Wait a moment for API to start
    Start-Sleep -Seconds 3
    
    # Start Web app in new window
    Write-Host "🌐 Starting Web app in new window..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\apps\web'; Write-Host '🌐 YuYu Lolita Web App' -ForegroundColor Blue; bun run dev:windows"
    
    # Wait for services to start
    Start-Sleep -Seconds 5
}

# Step 5: Open browser
if (-not $SkipBrowser) {
    Write-Host "`n🌐 Opening browser..." -ForegroundColor Cyan
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:5173"
}

# Display access information
Write-Host "`n✅ Development servers started!" -ForegroundColor Green
Write-Host "=============================" -ForegroundColor Green
Write-Host ""
Write-Host "🔗 Access URLs:" -ForegroundColor Cyan
Write-Host "   📱 Web App: http://localhost:5173" -ForegroundColor White
Write-Host "   🔌 API: http://localhost:3001" -ForegroundColor White
Write-Host "   📚 API Docs: http://localhost:3001/swagger" -ForegroundColor White
Write-Host ""
Write-Host "🛑 To stop servers:" -ForegroundColor Yellow
Write-Host "   Close the PowerShell windows or press Ctrl+C in each" -ForegroundColor White
Write-Host ""
Write-Host "🐛 Troubleshooting:" -ForegroundColor Cyan
Write-Host "   - Check that PostgreSQL is running" -ForegroundColor White
Write-Host "   - Verify .env configuration" -ForegroundColor White
Write-Host "   - Check Windows Firewall settings for ports 3001, 5173" -ForegroundColor White