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
Write-Host 'Loading environment from parent process...' -ForegroundColor Cyan

# Inherit all environment variables from parent
`$parentEnv = [Environment]::GetEnvironmentVariables()
foreach (`$kvp in `$parentEnv.GetEnumerator()) {
    [Environment]::SetEnvironmentVariable(`$kvp.Key, `$kvp.Value, [System.EnvironmentVariableTarget]::Process)
}

# Set API-specific overrides
[Environment]::SetEnvironmentVariable("NODE_ENV", "development", [System.EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable("API_PORT", "3001", [System.EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable("API_HOST", "localhost", [System.EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable("PORT", `$null, [System.EnvironmentVariableTarget]::Process)

Write-Host "Environment variables:" -ForegroundColor Cyan
Write-Host "  DATABASE_URL: `$([Environment]::GetEnvironmentVariable('DATABASE_URL') -replace ':[^@]*@', ':***@')" -ForegroundColor White
Write-Host "  API_PORT: `$([Environment]::GetEnvironmentVariable('API_PORT'))" -ForegroundColor White
Write-Host "  NODE_ENV: `$([Environment]::GetEnvironmentVariable('NODE_ENV'))" -ForegroundColor White

Write-Host 'Starting API server...' -ForegroundColor Green
bun --hot src/index-db.ts
"@
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $apiCommand
    
    # Wait a moment for API to start
    Start-Sleep -Seconds 3
    
    # Start Web app in new window with full environment inheritance
    Write-Host "[WEB] Starting Web app in new window..." -ForegroundColor Yellow
    $webCommand = @"
cd '$projectRoot\apps\web'
Write-Host '[WEB] Lolita Fashion Web App' -ForegroundColor Blue
Write-Host 'Loading environment from parent process...' -ForegroundColor Cyan

# Inherit all environment variables from parent
`$parentEnv = [Environment]::GetEnvironmentVariables()
foreach (`$kvp in `$parentEnv.GetEnumerator()) {
    [Environment]::SetEnvironmentVariable(`$kvp.Key, `$kvp.Value, [System.EnvironmentVariableTarget]::Process)
}

# Set Web-specific overrides
[Environment]::SetEnvironmentVariable("NODE_ENV", "development", [System.EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable("WEB_PORT", "5173", [System.EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable("HOST", "localhost", [System.EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable("API_PORT", `$null, [System.EnvironmentVariableTarget]::Process)

Write-Host "Environment variables:" -ForegroundColor Cyan
Write-Host "  PUBLIC_API_URL: `$([Environment]::GetEnvironmentVariable('PUBLIC_API_URL'))" -ForegroundColor White
Write-Host "  WEB_PORT: `$([Environment]::GetEnvironmentVariable('WEB_PORT'))" -ForegroundColor White
Write-Host "  HOST: `$([Environment]::GetEnvironmentVariable('HOST'))" -ForegroundColor White
Write-Host "  NODE_ENV: `$([Environment]::GetEnvironmentVariable('NODE_ENV'))" -ForegroundColor White

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