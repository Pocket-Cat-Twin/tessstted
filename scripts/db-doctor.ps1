# Database Doctor - Windows PostgreSQL Diagnostic and Recovery Script
# Comprehensive tool for diagnosing and fixing PostgreSQL issues on Windows

param(
    [switch]$Diagnose,
    [switch]$Fix,
    [switch]$Emergency,
    [switch]$Monitor,
    [switch]$Report,
    [switch]$Test,
    [switch]$Setup,
    [string]$Action = "help"
)

Write-Host "🏥 Lolita Fashion Database Doctor v1.0" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Check if running on Windows
if ($PSVersionTable.PSVersion.Major -lt 3 -or $env:OS -notlike "*Windows*") {
    Write-Host "❌ This script is designed for Windows PowerShell 3.0+" -ForegroundColor Red
    Write-Host "   Current version: $($PSVersionTable.PSVersion)" -ForegroundColor Yellow
    exit 1
}

# Set UTF-8 encoding for better Russian text support
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    [Console]::InputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host "⚠️  Could not set UTF-8 encoding" -ForegroundColor Yellow
}

# Function to check if PostgreSQL service is running
function Test-PostgreSQLService {
    Write-Host "🔍 Checking PostgreSQL service..." -ForegroundColor Yellow
    
    $services = Get-Service -Name "*postgresql*" -ErrorAction SilentlyContinue
    
    if ($services) {
        foreach ($service in $services) {
            $status = if ($service.Status -eq "Running") { "✅" } else { "❌" }
            Write-Host "   $status $($service.Name): $($service.Status)" -ForegroundColor $(if ($service.Status -eq "Running") { "Green" } else { "Red" })
        }
        return $services | Where-Object { $_.Status -eq "Running" }
    } else {
        Write-Host "   ❌ No PostgreSQL services found" -ForegroundColor Red
        Write-Host "   💡 Install PostgreSQL: https://www.postgresql.org/download/windows/" -ForegroundColor Blue
        return $false
    }
}

# Function to check network connectivity
function Test-DatabaseNetwork {
    Write-Host "🌐 Checking network connectivity..." -ForegroundColor Yellow
    
    # Test localhost resolution
    try {
        $localhost = [System.Net.Dns]::GetHostEntry("localhost")
        Write-Host "   ✅ Localhost resolves to: $($localhost.AddressList[0])" -ForegroundColor Green
    } catch {
        Write-Host "   ❌ Localhost resolution failed" -ForegroundColor Red
        Write-Host "   💡 Try using 127.0.0.1 instead of localhost" -ForegroundColor Blue
    }
    
    # Test port 5432
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.Connect("localhost", 5432)
        $tcpClient.Close()
        Write-Host "   ✅ Port 5432 is accessible" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "   ❌ Port 5432 is not accessible" -ForegroundColor Red
        Write-Host "   💡 Check if PostgreSQL is running on port 5432" -ForegroundColor Blue
        return $false
    }
}

# Function to start PostgreSQL service
function Start-PostgreSQLService {
    Write-Host "🚀 Attempting to start PostgreSQL service..." -ForegroundColor Yellow
    
    $services = Get-Service -Name "*postgresql*" -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "Stopped" }
    
    if ($services) {
        foreach ($service in $services) {
            try {
                Write-Host "   Starting $($service.Name)..." -ForegroundColor Yellow
                Start-Service -Name $service.Name
                Write-Host "   ✅ $($service.Name) started successfully" -ForegroundColor Green
                return $true
            } catch {
                Write-Host "   ❌ Failed to start $($service.Name): $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "   ⚠️  No stopped PostgreSQL services found" -ForegroundColor Yellow
    }
    return $false
}

# Function to run comprehensive diagnostics
function Invoke-DatabaseDiagnostics {
    Write-Host "🔍 Running comprehensive database diagnostics..." -ForegroundColor Cyan
    Write-Host ""
    
    # System information
    Write-Host "💻 System Information:" -ForegroundColor White
    Write-Host "   OS: $([Environment]::OSVersion.VersionString)" -ForegroundColor Gray
    Write-Host "   PowerShell: $($PSVersionTable.PSVersion)" -ForegroundColor Gray
    Write-Host "   Encoding: $([Console]::OutputEncoding.EncodingName)" -ForegroundColor Gray
    Write-Host ""
    
    # Service check
    $serviceRunning = Test-PostgreSQLService
    Write-Host ""
    
    # Network check
    $networkOk = Test-DatabaseNetwork
    Write-Host ""
    
    # Database connection test using Node.js
    Write-Host "🗃️  Testing database connection..." -ForegroundColor Yellow
    try {
        $result = bun run --silent packages/db/src/health-monitor.ts
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✅ Database connection successful" -ForegroundColor Green
        } else {
            Write-Host "   ❌ Database connection failed" -ForegroundColor Red
        }
    } catch {
        Write-Host "   ❌ Could not test database connection" -ForegroundColor Red
        Write-Host "   💡 Run: bun run db:test" -ForegroundColor Blue
    }
    Write-Host ""
    
    # Environment check
    Write-Host "⚙️  Environment Configuration:" -ForegroundColor White
    if (Test-Path ".env") {
        $envContent = Get-Content ".env" | Select-String "DATABASE_URL"
        if ($envContent) {
            $dbUrl = $envContent -replace "DATABASE_URL=", "" -replace "postgres:[^@]*@", "postgres:***@"
            Write-Host "   ✅ DATABASE_URL: $dbUrl" -ForegroundColor Green
        } else {
            Write-Host "   ❌ DATABASE_URL not found in .env" -ForegroundColor Red
        }
    } else {
        Write-Host "   ❌ .env file not found" -ForegroundColor Red
        Write-Host "   💡 Copy .env.example to .env" -ForegroundColor Blue
    }
    Write-Host ""
    
    # Summary
    Write-Host "📊 Diagnostic Summary:" -ForegroundColor White
    $issues = @()
    $recommendations = @()
    
    if (-not $serviceRunning) {
        $issues += "PostgreSQL service not running"
        $recommendations += "Start PostgreSQL service or install PostgreSQL"
    }
    
    if (-not $networkOk) {
        $issues += "Network connectivity issues"
        $recommendations += "Check firewall and PostgreSQL configuration"
    }
    
    if ($issues.Count -eq 0) {
        Write-Host "   ✅ No major issues detected" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Issues found: $($issues.Count)" -ForegroundColor Red
        foreach ($issue in $issues) {
            Write-Host "      • $issue" -ForegroundColor Red
        }
        Write-Host ""
        Write-Host "   💡 Recommendations:" -ForegroundColor Blue
        foreach ($rec in $recommendations) {
            Write-Host "      • $rec" -ForegroundColor Blue
        }
    }
}

# Function to attempt automatic fixes
function Invoke-DatabaseFix {
    Write-Host "🔧 Attempting automatic database fixes..." -ForegroundColor Cyan
    Write-Host ""
    
    $fixed = @()
    $failed = @()
    
    # Try to start PostgreSQL service
    Write-Host "1️⃣  Checking PostgreSQL service..." -ForegroundColor Yellow
    $serviceStarted = Start-PostgreSQLService
    if ($serviceStarted) {
        $fixed += "Started PostgreSQL service"
    } else {
        $failed += "Could not start PostgreSQL service"
    }
    
    # Set UTF-8 encoding
    Write-Host "2️⃣  Setting UTF-8 encoding..." -ForegroundColor Yellow
    try {
        cmd /c "chcp 65001 >nul"
        $fixed += "Set UTF-8 encoding"
    } catch {
        $failed += "Could not set UTF-8 encoding"
    }
    
    # Check firewall
    Write-Host "3️⃣  Checking Windows Firewall..." -ForegroundColor Yellow
    try {
        $firewallRules = netsh advfirewall firewall show rule name="PostgreSQL" 2>$null
        if (-not $firewallRules) {
            Write-Host "   Adding firewall rule for PostgreSQL..." -ForegroundColor Yellow
            netsh advfirewall firewall add rule name="PostgreSQL" dir=in action=allow protocol=TCP localport=5432 >$null
            $fixed += "Added firewall rule for PostgreSQL"
        } else {
            Write-Host "   ✅ Firewall rule already exists" -ForegroundColor Green
        }
    } catch {
        $failed += "Could not configure firewall"
    }
    
    # Test database creation
    Write-Host "4️⃣  Testing database setup..." -ForegroundColor Yellow
    try {
        $result = bun run db:setup 2>$null
        if ($LASTEXITCODE -eq 0) {
            $fixed += "Database setup completed"
        } else {
            $failed += "Database setup failed"
        }
    } catch {
        $failed += "Could not run database setup"
    }
    
    Write-Host ""
    Write-Host "📊 Fix Summary:" -ForegroundColor White
    if ($fixed.Count -gt 0) {
        Write-Host "   ✅ Fixed ($($fixed.Count)):" -ForegroundColor Green
        foreach ($fix in $fixed) {
            Write-Host "      • $fix" -ForegroundColor Green
        }
    }
    
    if ($failed.Count -gt 0) {
        Write-Host "   ❌ Failed ($($failed.Count)):" -ForegroundColor Red
        foreach ($fail in $failed) {
            Write-Host "      • $fail" -ForegroundColor Red
        }
    }
    
    if ($failed.Count -eq 0) {
        Write-Host ""
        Write-Host "🎉 All automatic fixes completed successfully!" -ForegroundColor Green
        Write-Host "   Run diagnostics again to verify: .\scripts\db-doctor.ps1 -Diagnose" -ForegroundColor Blue
    }
}

# Function to run emergency recovery
function Invoke-EmergencyRecovery {
    Write-Host "🆘 Emergency Database Recovery" -ForegroundColor Red
    Write-Host "==============================" -ForegroundColor Red
    Write-Host ""
    
    Write-Host "⚠️  This will attempt to recover your database connection" -ForegroundColor Yellow
    Write-Host "   and may reset some configurations. Continue? (Y/N)" -ForegroundColor Yellow
    
    $response = Read-Host
    if ($response -ne "Y" -and $response -ne "y") {
        Write-Host "   Recovery cancelled" -ForegroundColor Yellow
        return
    }
    
    Write-Host ""
    Write-Host "🔧 Starting emergency recovery..." -ForegroundColor Red
    
    # Step 1: Full diagnostics
    Invoke-DatabaseDiagnostics
    Write-Host ""
    
    # Step 2: Stop all PostgreSQL services
    Write-Host "1️⃣  Stopping all PostgreSQL services..." -ForegroundColor Yellow
    Get-Service -Name "*postgresql*" -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "Running" } | ForEach-Object {
        try {
            Stop-Service -Name $_.Name -Force
            Write-Host "   ✅ Stopped $($_.Name)" -ForegroundColor Green
        } catch {
            Write-Host "   ❌ Could not stop $($_.Name)" -ForegroundColor Red
        }
    }
    
    # Step 3: Start PostgreSQL services
    Write-Host "2️⃣  Starting PostgreSQL services..." -ForegroundColor Yellow
    Start-PostgreSQLService
    
    # Step 4: Wait and test
    Write-Host "3️⃣  Waiting for services to stabilize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # Step 5: Test connection
    Write-Host "4️⃣  Testing database connection..." -ForegroundColor Yellow
    try {
        $result = bun run db:test
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✅ Database connection restored!" -ForegroundColor Green
        } else {
            Write-Host "   ❌ Database connection still failing" -ForegroundColor Red
        }
    } catch {
        Write-Host "   ❌ Could not test connection" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "📊 Emergency Recovery Complete" -ForegroundColor Red
    Write-Host "==============================" -ForegroundColor Red
}

# Function to show usage help
function Show-Help {
    Write-Host "🏥 Database Doctor - PostgreSQL Diagnostic Tool" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor White
    Write-Host "  .\scripts\db-doctor.ps1 -Diagnose    # Run comprehensive diagnostics" -ForegroundColor Gray
    Write-Host "  .\scripts\db-doctor.ps1 -Fix         # Attempt automatic fixes" -ForegroundColor Gray
    Write-Host "  .\scripts\db-doctor.ps1 -Emergency   # Emergency recovery mode" -ForegroundColor Gray
    Write-Host "  .\scripts\db-doctor.ps1 -Test        # Quick connection test" -ForegroundColor Gray
    Write-Host "  .\scripts\db-doctor.ps1 -Report      # Generate health report" -ForegroundColor Gray
    Write-Host "  .\scripts\db-doctor.ps1 -Setup       # Database setup" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor White
    Write-Host "  .\scripts\db-doctor.ps1 -Diagnose    # Check database health" -ForegroundColor Blue
    Write-Host "  .\scripts\db-doctor.ps1 -Fix         # Fix common issues" -ForegroundColor Blue
    Write-Host "  .\scripts\db-doctor.ps1 -Emergency   # Full recovery mode" -ForegroundColor Blue
    Write-Host ""
    Write-Host "For more help: bun run db:help" -ForegroundColor Yellow
}

# Main script logic
switch ($true) {
    $Diagnose { Invoke-DatabaseDiagnostics }
    $Fix { Invoke-DatabaseFix }
    $Emergency { Invoke-EmergencyRecovery }
    $Test {
        Write-Host "🧪 Quick Database Connection Test" -ForegroundColor Cyan
        Write-Host "==================================" -ForegroundColor Cyan
        bun run db:test
    }
    $Report {
        Write-Host "📊 Database Health Report" -ForegroundColor Cyan
        Write-Host "=========================" -ForegroundColor Cyan
        bun run db:health
    }
    $Setup {
        Write-Host "⚙️  Database Setup" -ForegroundColor Cyan
        Write-Host "==================" -ForegroundColor Cyan
        bun run db:setup
    }
    default { Show-Help }
}

Write-Host ""
Write-Host "✅ Database Doctor completed" -ForegroundColor Green