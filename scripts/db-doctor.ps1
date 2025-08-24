# Database Doctor - Windows PostgreSQL Diagnostic and Recovery Script
# Enterprise-grade tool for diagnosing and fixing PostgreSQL issues on Windows
# Version: 2.0 - Unicode-Safe & Production-Ready
# Author: Senior DevOps Engineer  
# Last Modified: 2025-08-24

#Requires -Version 3.0

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

# Import the common PowerShell library
$commonLibPath = Join-Path $PSScriptRoot "PowerShell-Common.ps1"
if (Test-Path $commonLibPath) {
    . $commonLibPath
} else {
    Write-Error "PowerShell-Common.ps1 library not found. Please ensure it exists in the scripts directory."
    exit 1
}

Write-SafeHeader "Lolita Fashion Database Doctor v2.0" "="
Write-SafeOutput "Enterprise-grade PostgreSQL diagnostic tool for Windows" -Status Info

# ==============================================================================
# POSTGRESQL SPECIFIC FUNCTIONS
# ==============================================================================

function Test-PostgreSQLService {
    <#
    .SYNOPSIS
    Comprehensive PostgreSQL service detection and status check
    #>
    
    Write-SafeOutput "Checking PostgreSQL service status..." -Status Processing
    
    # Check for PostgreSQL services with version priority (16 > 15 > others)
    $pgServiceResult = Test-ServiceSafely -ServiceName "*postgresql*" -PreferredVersions @("16", "15")
    
    if (-not $pgServiceResult.Found) {
        Write-SafeOutput "No PostgreSQL services found" -Status Error
        Write-SafeOutput "Install PostgreSQL from: https://www.postgresql.org/download/windows/" -Status Info
        return @{
            Success = $false
            Service = $null
            Running = $false
            Message = "PostgreSQL service not found"
        }
    }
    
    $service = $pgServiceResult.Service
    $isRunning = $pgServiceResult.Status -eq "Running"
    
    $statusText = if ($isRunning) { "RUNNING" } else { "STOPPED" }
    $statusType = if ($isRunning) { "Success" } else { "Warning" }
    
    Write-SafeOutput "$($service.DisplayName): $statusText" -Status $statusType
    
    return @{
        Success = $true
        Service = $service
        Running = $isRunning
        Message = "PostgreSQL service: $($service.Name) - $statusText"
    }
}

function Test-PostgreSQLConnectivity {
    <#
    .SYNOPSIS
    Tests PostgreSQL network connectivity and database access
    #>
    
    Write-SafeOutput "Testing PostgreSQL connectivity..." -Status Processing
    
    # Test localhost name resolution
    try {
        $localhost = [System.Net.Dns]::GetHostEntry("localhost")
        Write-SafeOutput "Localhost resolves to: $($localhost.AddressList[0])" -Status Success
    }
    catch {
        Write-SafeOutput "Localhost resolution failed - try using 127.0.0.1" -Status Warning
    }
    
    # Test PostgreSQL port (5432)
    $portTest = Test-NetworkPortSafely -HostName "localhost" -Port 5432 -TimeoutMs 5000
    
    if ($portTest.Success) {
        Write-SafeOutput "Port 5432 is accessible" -Status Success
        
        # Try database connection test using Bun
        $dbTestResult = Invoke-SafeCommand -Command "bun" -Arguments @("run", "--silent", "packages/db/src/health-monitor.ts") -Description "Testing database connection" -IgnoreErrors
        
        if ($dbTestResult.Success) {
            Write-SafeOutput "Database connection successful" -Status Success
            return @{
                Success = $true
                NetworkOk = $true
                DatabaseOk = $true
                Message = "PostgreSQL is fully accessible"
            }
        } else {
            Write-SafeOutput "Database connection failed" -Status Warning
            return @{
                Success = $false
                NetworkOk = $true
                DatabaseOk = $false
                Message = "Network accessible but database connection failed"
            }
        }
    } else {
        Write-SafeOutput $portTest.Message -Status Error
        return @{
            Success = $false
            NetworkOk = $false
            DatabaseOk = $false
            Message = "PostgreSQL port 5432 is not accessible"
        }
    }
}

function Test-EnvironmentConfiguration {
    <#
    .SYNOPSIS
    Validates environment configuration for database connection
    #>
    
    Write-SafeOutput "Checking environment configuration..." -Status Processing
    
    $projectRoot = Get-ProjectRoot
    $envPath = Join-Path $projectRoot ".env"
    
    $envCheck = Test-PathSafely -Path $envPath -Type "File"
    
    if (-not $envCheck.Exists) {
        Write-SafeOutput ".env file not found - copy .env.example to .env" -Status Error
        return @{
            Success = $false
            EnvExists = $false
            DatabaseUrl = $null
            Message = "Environment file missing"
        }
    }
    
    Write-SafeOutput "Environment file found" -Status Success
    
    try {
        $envContent = Get-Content $envPath | Where-Object { $_ -like "DATABASE_URL=*" }
        
        if ($envContent) {
            # Mask sensitive information for display
            $maskedUrl = $envContent -replace "postgres:[^@]*@", "postgres:***@"
            Write-SafeOutput "DATABASE_URL configured: $maskedUrl" -Status Success
            return @{
                Success = $true
                EnvExists = $true
                DatabaseUrl = $envContent
                Message = "Environment properly configured"
            }
        } else {
            Write-SafeOutput "DATABASE_URL not found in .env file" -Status Error
            return @{
                Success = $false
                EnvExists = $true
                DatabaseUrl = $null
                Message = "DATABASE_URL missing from environment"
            }
        }
    }
    catch {
        Write-SafeOutput "Error reading environment file: $($_.Exception.Message)" -Status Error
        return @{
            Success = $false
            EnvExists = $true
            DatabaseUrl = $null
            Message = "Error reading environment configuration"
        }
    }
}

# ==============================================================================
# DIAGNOSTIC FUNCTIONS
# ==============================================================================

function Invoke-ComprehensiveDiagnostics {
    <#
    .SYNOPSIS
    Runs complete database system diagnostics
    #>
    
    Write-SafeHeader "COMPREHENSIVE DATABASE DIAGNOSTICS" "="
    
    $diagnostics = @{
        SystemInfo = @{}
        ServiceStatus = @{}
        NetworkStatus = @{}
        EnvironmentStatus = @{}
        Issues = @()
        Recommendations = @()
    }
    
    # System Information
    Write-SafeSectionHeader "System Information" 1
    $diagnostics.SystemInfo = @{
        OS = [Environment]::OSVersion.VersionString
        PowerShell = $PSVersionTable.PSVersion.ToString()
        Encoding = [Console]::OutputEncoding.EncodingName
        WorkingDirectory = (Get-Location).Path
        ProjectRoot = Get-ProjectRoot
    }
    
    Write-SafeOutput "OS: $($diagnostics.SystemInfo.OS)" -Status Info
    Write-SafeOutput "PowerShell: $($diagnostics.SystemInfo.PowerShell)" -Status Info
    Write-SafeOutput "Project Root: $($diagnostics.SystemInfo.ProjectRoot)" -Status Info
    
    # Service Status Check
    Write-SafeSectionHeader "PostgreSQL Service Status" 2
    $serviceCheck = Test-PostgreSQLService
    $diagnostics.ServiceStatus = $serviceCheck
    
    if (-not $serviceCheck.Success) {
        $diagnostics.Issues += "PostgreSQL service not found or accessible"
        $diagnostics.Recommendations += "Install PostgreSQL from https://www.postgresql.org/download/windows/"
    } elseif (-not $serviceCheck.Running) {
        $diagnostics.Issues += "PostgreSQL service is not running"
        $diagnostics.Recommendations += "Start PostgreSQL service or enable auto-start"
    }
    
    # Network Connectivity Check
    Write-SafeSectionHeader "Network Connectivity" 3
    $networkCheck = Test-PostgreSQLConnectivity
    $diagnostics.NetworkStatus = $networkCheck
    
    if (-not $networkCheck.NetworkOk) {
        $diagnostics.Issues += "PostgreSQL port 5432 is not accessible"
        $diagnostics.Recommendations += "Check Windows Firewall and PostgreSQL configuration"
    }
    
    if ($networkCheck.NetworkOk -and -not $networkCheck.DatabaseOk) {
        $diagnostics.Issues += "Network accessible but database connection failed"
        $diagnostics.Recommendations += "Check database credentials and permissions"
    }
    
    # Environment Configuration Check
    Write-SafeSectionHeader "Environment Configuration" 4
    $envCheck = Test-EnvironmentConfiguration
    $diagnostics.EnvironmentStatus = $envCheck
    
    if (-not $envCheck.Success) {
        $diagnostics.Issues += $envCheck.Message
        $diagnostics.Recommendations += "Configure .env file with proper DATABASE_URL"
    }
    
    # Summary Report
    Write-SafeSectionHeader "DIAGNOSTIC SUMMARY"
    
    if ($diagnostics.Issues.Count -eq 0) {
        Write-SafeOutput "No critical issues detected - system appears healthy" -Status Complete
    } else {
        Write-SafeOutput "$($diagnostics.Issues.Count) issues found requiring attention" -Status Warning
        
        Write-Host ""
        Write-SafeOutput "ISSUES IDENTIFIED:" -Status Warning
        foreach ($issue in $diagnostics.Issues) {
            Write-SafeOutput "  * $issue" -Status Error
        }
        
        Write-Host ""
        Write-SafeOutput "RECOMMENDED ACTIONS:" -Status Info
        foreach ($recommendation in $diagnostics.Recommendations) {
            Write-SafeOutput "  * $recommendation" -Status Info
        }
    }
    
    return $diagnostics
}

# ==============================================================================
# REPAIR FUNCTIONS
# ==============================================================================

function Invoke-AutomaticRepairs {
    <#
    .SYNOPSIS
    Attempts to automatically fix common PostgreSQL issues
    #>
    
    Write-SafeHeader "AUTOMATIC DATABASE REPAIR" "="
    
    $repairResults = @{
        Attempted = @()
        Successful = @()
        Failed = @()
    }
    
    # Repair 1: Start PostgreSQL Service
    Write-SafeSectionHeader "PostgreSQL Service Management" 1
    $repairResults.Attempted += "PostgreSQL service startup"
    
    $serviceCheck = Test-PostgreSQLService
    if ($serviceCheck.Success -and -not $serviceCheck.Running) {
        $startResult = Start-ServiceSafely -ServiceName $serviceCheck.Service.Name -Description "PostgreSQL"
        if ($startResult) {
            $repairResults.Successful += "Started PostgreSQL service"
        } else {
            $repairResults.Failed += "Failed to start PostgreSQL service"
        }
    } elseif ($serviceCheck.Running) {
        Write-SafeOutput "PostgreSQL service already running" -Status Success
        $repairResults.Successful += "PostgreSQL service verified running"
    } else {
        $repairResults.Failed += "PostgreSQL service not found"
    }
    
    # Repair 2: Console Encoding
    Write-SafeSectionHeader "Console Encoding Configuration" 2
    $repairResults.Attempted += "UTF-8 encoding setup"
    
    try {
        $result = Invoke-SafeCommand -Command "cmd" -Arguments @("/c", "chcp 65001 >nul") -Description "Setting UTF-8 encoding" -IgnoreErrors
        if ($result.Success) {
            $repairResults.Successful += "UTF-8 encoding configured"
        } else {
            $repairResults.Failed += "UTF-8 encoding setup failed"
        }
    }
    catch {
        $repairResults.Failed += "UTF-8 encoding setup failed"
    }
    
    # Repair 3: Windows Firewall
    Write-SafeSectionHeader "Windows Firewall Configuration" 3
    $repairResults.Attempted += "Windows Firewall rule setup"
    
    try {
        # Check if rule already exists
        $existingRule = netsh advfirewall firewall show rule name="PostgreSQL-5432" 2>$null
        
        if (-not $existingRule) {
            $firewallResult = Invoke-SafeCommand -Command "netsh" -Arguments @("advfirewall", "firewall", "add", "rule", "name=PostgreSQL-5432", "dir=in", "action=allow", "protocol=TCP", "localport=5432") -Description "Adding PostgreSQL firewall rule" -IgnoreErrors
            
            if ($firewallResult.Success) {
                $repairResults.Successful += "Added PostgreSQL firewall rule"
            } else {
                $repairResults.Failed += "Failed to add firewall rule (may need admin privileges)"
            }
        } else {
            Write-SafeOutput "PostgreSQL firewall rule already exists" -Status Success
            $repairResults.Successful += "PostgreSQL firewall rule verified"
        }
    }
    catch {
        $repairResults.Failed += "Firewall configuration failed"
    }
    
    # Repair 4: Database Setup Test
    Write-SafeSectionHeader "Database Setup Verification" 4
    $repairResults.Attempted += "Database setup verification"
    
    $dbSetupResult = Invoke-SafeCommand -Command "bun" -Arguments @("run", "db:setup") -Description "Testing database setup" -IgnoreErrors -TimeoutSeconds 60
    
    if ($dbSetupResult.Success) {
        $repairResults.Successful += "Database setup verified"
    } else {
        $repairResults.Failed += "Database setup failed"
    }
    
    # Repair Summary
    Write-SafeSectionHeader "REPAIR SUMMARY"
    
    Write-SafeOutput "REPAIRS ATTEMPTED: $($repairResults.Attempted.Count)" -Status Info
    foreach ($attempt in $repairResults.Attempted) {
        Write-SafeOutput "  * $attempt" -Status Info
    }
    
    Write-Host ""
    
    if ($repairResults.Successful.Count -gt 0) {
        Write-SafeOutput "SUCCESSFUL REPAIRS: $($repairResults.Successful.Count)" -Status Success
        foreach ($success in $repairResults.Successful) {
            Write-SafeOutput "  * $success" -Status Success
        }
    }
    
    if ($repairResults.Failed.Count -gt 0) {
        Write-Host ""
        Write-SafeOutput "FAILED REPAIRS: $($repairResults.Failed.Count)" -Status Warning
        foreach ($failure in $repairResults.Failed) {
            Write-SafeOutput "  * $failure" -Status Warning
        }
    }
    
    if ($repairResults.Failed.Count -eq 0) {
        Write-Host ""
        Write-SafeOutput "All automatic repairs completed successfully!" -Status Complete
        Write-SafeOutput "Run diagnostics to verify: .\scripts\db-doctor.ps1 -Diagnose" -Status Info
    } else {
        Write-Host ""
        Write-SafeOutput "Some repairs failed - manual intervention may be required" -Status Warning
    }
    
    return $repairResults
}

# ==============================================================================
# EMERGENCY RECOVERY
# ==============================================================================

function Invoke-EmergencyDatabaseRecovery {
    <#
    .SYNOPSIS
    Emergency recovery procedure for severe database issues
    #>
    
    Write-SafeHeader "EMERGENCY DATABASE RECOVERY" "="
    Write-SafeOutput "This will attempt comprehensive database recovery" -Status Warning
    Write-SafeOutput "Some configurations may be reset during this process" -Status Warning
    Write-Host ""
    
    $confirmation = Read-Host "Continue with emergency recovery? (Y/N)"
    if ($confirmation -ne "Y" -and $confirmation -ne "y") {
        Write-SafeOutput "Emergency recovery cancelled" -Status Info
        return
    }
    
    Write-SafeHeader "EMERGENCY RECOVERY IN PROGRESS" "="
    
    # Step 1: Full Diagnostics
    Write-SafeSectionHeader "Pre-Recovery Diagnostics" 1
    $preDiagnostics = Invoke-ComprehensiveDiagnostics
    
    # Step 2: Service Reset
    Write-SafeSectionHeader "PostgreSQL Service Reset" 2
    
    try {
        $services = Get-Service -Name "*postgresql*" -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "Running" }
        
        foreach ($service in $services) {
            Write-SafeOutput "Stopping service: $($service.Name)" -Status Processing
            try {
                Stop-Service -Name $service.Name -Force -ErrorAction Stop
                Write-SafeOutput "Stopped: $($service.Name)" -Status Success
            }
            catch {
                Write-SafeOutput "Could not stop: $($service.Name)" -Status Warning
            }
        }
        
        Start-Sleep -Seconds 3
        
        # Restart services
        foreach ($service in $services) {
            Write-SafeOutput "Starting service: $($service.Name)" -Status Processing
            $startResult = Start-ServiceSafely -ServiceName $service.Name -Description $service.DisplayName
        }
    }
    catch {
        Write-SafeOutput "Service reset encountered issues: $($_.Exception.Message)" -Status Warning
    }
    
    # Step 3: Connection Stabilization
    Write-SafeSectionHeader "Connection Stabilization" 3
    Write-SafeOutput "Waiting for services to stabilize..." -Status Processing
    Start-Sleep -Seconds 5
    
    # Step 4: Database Test
    Write-SafeSectionHeader "Database Connection Test" 4
    $testResult = Invoke-SafeCommand -Command "bun" -Arguments @("run", "db:test") -Description "Testing database connection" -IgnoreErrors
    
    if ($testResult.Success) {
        Write-SafeOutput "Database connection restored!" -Status Complete
    } else {
        Write-SafeOutput "Database connection still failing" -Status Error
        Write-SafeOutput "Manual PostgreSQL configuration may be required" -Status Warning
    }
    
    Write-SafeHeader "EMERGENCY RECOVERY COMPLETE" "="
    
    if ($testResult.Success) {
        Write-SafeOutput "Recovery successful - database is now accessible" -Status Complete
    } else {
        Write-SafeOutput "Recovery partially successful - manual steps may be required" -Status Warning
        Write-SafeOutput "Consider checking PostgreSQL installation and configuration" -Status Info
    }
}

# ==============================================================================
# MAIN SCRIPT LOGIC
# ==============================================================================

function Show-DatabaseDoctorHelp {
    <#
    .SYNOPSIS
    Displays comprehensive help information
    #>
    
    Write-SafeHeader "Database Doctor - PostgreSQL Diagnostic Tool"
    
    Write-SafeOutput "USAGE:" -Status Info
    Write-SafeOutput "  .\scripts\db-doctor.ps1 -Diagnose    # Run comprehensive diagnostics" -Status Info
    Write-SafeOutput "  .\scripts\db-doctor.ps1 -Fix         # Attempt automatic fixes" -Status Info
    Write-SafeOutput "  .\scripts\db-doctor.ps1 -Emergency   # Emergency recovery mode" -Status Info
    Write-SafeOutput "  .\scripts\db-doctor.ps1 -Test        # Quick connection test" -Status Info
    Write-SafeOutput "  .\scripts\db-doctor.ps1 -Report      # Generate health report" -Status Info
    Write-SafeOutput "  .\scripts\db-doctor.ps1 -Setup       # Database setup" -Status Info
    
    Write-Host ""
    Write-SafeOutput "EXAMPLES:" -Status Info
    Write-SafeOutput "  .\scripts\db-doctor.ps1 -Diagnose    # Check database health" -Status Info
    Write-SafeOutput "  .\scripts\db-doctor.ps1 -Fix         # Fix common issues" -Status Info
    Write-SafeOutput "  .\scripts\db-doctor.ps1 -Emergency   # Full recovery mode" -Status Info
    
    Write-Host ""
    Write-SafeOutput "For additional help: bun run db:help" -Status Info
}

# Main execution flow
switch ($true) {
    $Diagnose { 
        Invoke-ComprehensiveDiagnostics | Out-Null
    }
    
    $Fix { 
        Invoke-AutomaticRepairs | Out-Null
    }
    
    $Emergency { 
        Invoke-EmergencyDatabaseRecovery
    }
    
    $Test {
        Write-SafeHeader "Quick Database Connection Test"
        Invoke-SafeCommand -Command "bun" -Arguments @("run", "db:test") -Description "Testing database connection"
    }
    
    $Report {
        Write-SafeHeader "Database Health Report"
        Invoke-SafeCommand -Command "bun" -Arguments @("run", "db:health") -Description "Generating health report"
    }
    
    $Setup {
        Write-SafeHeader "Database Setup"
        Invoke-SafeCommand -Command "bun" -Arguments @("run", "db:setup") -Description "Running database setup"
    }
    
    default { 
        Show-DatabaseDoctorHelp 
    }
}

Write-Host ""
Write-SafeOutput "Database Doctor session completed" -Status Complete