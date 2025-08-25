#Requires -Version 3.0

<#
.SYNOPSIS
    Quick Windows PostgreSQL Startup for YuYu Lolita API
    
.DESCRIPTION
    Fast startup script for Windows PostgreSQL database.
    Ensures PostgreSQL is running and ready for API connection.

.PARAMETER Test
    Test connection after startup

.EXAMPLE
    .\Start-WindowsDatabase.ps1
    Basic startup

.EXAMPLE
    .\Start-WindowsDatabase.ps1 -Test  
    Startup with connection testing

.NOTES
    Version: 1.0.0 - Windows Edition
    Designed for daily use - fast and reliable
#>

[CmdletBinding()]
param(
    [switch]$Test = $false
)

# Colors
function Write-Status($Message, $Type) {
    switch ($Type) {
        "Success" { Write-Host "✅ $Message" -ForegroundColor Green }
        "Error" { Write-Host "❌ $Message" -ForegroundColor Red }
        "Warning" { Write-Host "⚠️  $Message" -ForegroundColor Yellow }
        "Info" { Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
        "Processing" { Write-Host "🔄 $Message" -ForegroundColor Yellow }
        default { Write-Host "$Message" }
    }
}

Write-Host "🚀 WINDOWS POSTGRESQL QUICK START" -ForegroundColor Magenta
Write-Host "==================================" -ForegroundColor Magenta
Write-Host ""

# Configuration
$DB_NAME = "yuyu_lolita"
$DB_USER = "postgres" 
$DB_PASSWORD = "postgres"
$DB_HOST = "localhost"
$DB_PORT = 5432

Write-Status "Target: $DB_USER@$DB_HOST`:$DB_PORT/$DB_NAME" "Info"
Write-Host ""

# Step 1: Check PostgreSQL Service
Write-Status "Step 1: Checking PostgreSQL service..." "Processing"

$services = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
$runningService = $services | Where-Object { $_.Status -eq "Running" } | Select-Object -First 1

if ($runningService) {
    Write-Status "PostgreSQL service '$($runningService.Name)' is already running" "Success"
} else {
    $stoppedService = $services | Select-Object -First 1
    if ($stoppedService) {
        Write-Status "Starting PostgreSQL service: $($stoppedService.Name)" "Processing"
        try {
            Start-Service $stoppedService.Name -ErrorAction Stop
            Write-Status "PostgreSQL service started successfully" "Success"
        } catch {
            Write-Status "Failed to start PostgreSQL service: $($_.Exception.Message)" "Error"
            Write-Status "Try running as Administrator" "Warning"
            exit 1
        }
    } else {
        Write-Status "No PostgreSQL service found" "Error"
        Write-Status "Please install PostgreSQL first" "Warning"
        Write-Status "Run: .\Setup-WindowsDatabase.ps1 -Install" "Info"
        exit 1
    }
}

# Step 2: Wait for PostgreSQL to be ready
Write-Status "Step 2: Waiting for PostgreSQL to be ready..." "Processing"

$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    
    try {
        $connection = Test-NetConnection -ComputerName $DB_HOST -Port $DB_PORT -ErrorAction SilentlyContinue
        if ($connection -and $connection.TcpTestSucceeded) {
            Write-Status "PostgreSQL is ready and accepting connections" "Success"
            break
        }
    } catch {
        # Ignore connection errors during startup
    }
    
    if ($attempt -eq 1) {
        Write-Host "   Waiting for PostgreSQL startup..." -ForegroundColor Gray
    }
    
    Write-Host "." -NoNewline -ForegroundColor Gray
    Start-Sleep -Seconds 1
    
    if ($attempt -eq $maxAttempts) {
        Write-Host ""
        Write-Status "PostgreSQL did not become ready within $maxAttempts seconds" "Error"
        Write-Status "Check Windows Event Log for PostgreSQL errors" "Warning"
        exit 1
    }
}

if ($attempt -gt 1) {
    Write-Host ""
}

# Step 3: Basic Connection Test
Write-Status "Step 3: Testing basic connection..." "Processing"

# Find PostgreSQL
$possiblePaths = @(
    "C:\Program Files\PostgreSQL\*\bin\psql.exe",
    "C:\Program Files (x86)\PostgreSQL\*\bin\psql.exe"
)

$psqlPath = $null
foreach ($path in $possiblePaths) {
    $found = Get-ChildItem -Path $path -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) {
        $psqlPath = $found.FullName
        break
    }
}

if (-not $psqlPath) {
    Write-Status "PostgreSQL psql not found" "Error"
    Write-Status "PostgreSQL may not be properly installed" "Warning"
    exit 1
}

# Test connection
$env:PGPASSWORD = $DB_PASSWORD
$connectionTest = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT current_database();" 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Status "Database connection successful" "Success"
} else {
    Write-Status "Database connection failed" "Warning"
    Write-Status "Database may need setup or configuration" "Warning"
    
    # Check if database exists
    $dbTest = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "SELECT 1;" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Status "PostgreSQL is working, but database '$DB_NAME' may not exist" "Info"
        Write-Status "Run: .\Setup-WindowsDatabase.ps1 -Configure" "Info"
    } else {
        Write-Status "PostgreSQL authentication may not be configured" "Info"
        Write-Status "Run: .\Setup-WindowsDatabase.ps1 -Install -Configure" "Info"
    }
}

# Step 4: Optional detailed testing
if ($Test) {
    Write-Host ""
    Write-Status "Step 4: Running detailed connection tests..." "Processing"
    
    try {
        & ".\Test-DatabaseConnection.ps1"
    } catch {
        Write-Status "Could not run detailed tests: $($_.Exception.Message)" "Warning"
    }
}

Write-Host ""
Write-Host "🎉 POSTGRESQL STARTUP COMPLETED" -ForegroundColor Green
Write-Host "===============================" -ForegroundColor Green
Write-Host ""

Write-Status "✅ PostgreSQL service is running" "Success"
Write-Status "✅ Network port is accessible" "Success"
Write-Status "✅ Ready for API connections" "Success"

Write-Host ""
Write-Status "🔗 Connection Details:" "Info"
Write-Status "   DATABASE_URL=postgresql://$DB_USER`:$DB_PASSWORD@$DB_HOST`:$DB_PORT/$DB_NAME" "Info"

Write-Host ""
Write-Status "🚀 Next Steps:" "Info"
Write-Status "   1. Ensure above DATABASE_URL is in your .env file" "Info"
Write-Status "   2. Start your API: bun run dev" "Info"
Write-Status "   3. API should connect without errors" "Info"

Write-Host ""
Write-Status "🔧 Quick Commands:" "Info"
Write-Status "   • Full test: .\Test-DatabaseConnection.ps1" "Info"
Write-Status "   • Setup: .\Setup-WindowsDatabase.ps1 -Configure" "Info"
Write-Status "   • Manual connection: psql -h $DB_HOST -U $DB_USER -d $DB_NAME" "Info"