# ================================
# MySQL8 Environment Checker for Windows
# YuYu Lolita Shopping System
# Enterprise-grade environment validation
# ================================

[CmdletBinding()]
param(
    [switch]$Fix = $false
)

# Import common functions with validation
$commonLibPath = Join-Path $PSScriptRoot "PowerShell-Common.ps1"
if (-not (Test-Path $commonLibPath)) {
    Write-Error "Required PowerShell-Common.ps1 not found at: $commonLibPath"
    exit 1
}
. $commonLibPath

# Environment configuration
$Script:MYSQL_SERVICE_NAMES = @("MySQL80", "MySQL")
$Script:MYSQL_DEFAULT_PORT = 3306
$Script:MYSQL_CONNECTION_TIMEOUT = 5000
$Script:ENV_REQUIRED_VARS = @("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")

# ==============================================================================
# ENVIRONMENT FILE OPERATIONS
# ==============================================================================

function Read-EnvFileSafely {
    <#
    .SYNOPSIS
    Safely reads and parses .env file with proper error handling
    #>
    param(
        [string]$EnvFilePath
    )
    
    if (-not $EnvFilePath) {
        $projectRoot = Get-ProjectRoot
        $EnvFilePath = Join-Path $projectRoot ".env"
    }
    
    if (-not (Test-Path $EnvFilePath)) {
        return @{
            Success = $false
            Variables = @{}
            Message = "Environment file not found: $EnvFilePath"
        }
    }
    
    try {
        $envVars = @{}
        $content = Get-Content $EnvFilePath -ErrorAction Stop
        
        foreach ($line in $content) {
            # Skip empty lines and comments
            if ([string]::IsNullOrWhiteSpace($line) -or $line.Trim().StartsWith("#")) {
                continue
            }
            
            # Parse KEY=VALUE format
            if ($line -match '^([^=]+)=(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                
                # Remove quotes if present
                if (($value.StartsWith('"') -and $value.EndsWith('"')) -or 
                    ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                    $value = $value.Substring(1, $value.Length - 2)
                }
                
                $envVars[$key] = $value
            }
        }
        
        return @{
            Success = $true
            Variables = $envVars
            Message = "Environment file loaded successfully"
            Path = $EnvFilePath
        }
    }
    catch {
        return @{
            Success = $false
            Variables = @{}
            Message = "Failed to read environment file: $($_.Exception.Message)"
        }
    }
}

function Test-EnvFileConfiguration {
    <#
    .SYNOPSIS
    Validates .env file existence and required variables
    #>
    param(
        [switch]$CreateFromTemplate
    )
    
    Write-SafeSectionHeader "Environment File Validation" -Step 1
    
    $projectRoot = Get-ProjectRoot
    $envPath = Join-Path $projectRoot ".env"
    $envExamplePath = Join-Path $projectRoot ".env.example"
    
    # Check if .env exists
    if (-not (Test-Path $envPath)) {
        Write-SafeOutput "Environment file not found: .env" -Status Error
        
        if ($CreateFromTemplate -and (Test-Path $envExamplePath)) {
            Write-SafeOutput "Creating .env from template..." -Status Processing
            try {
                Copy-Item $envExamplePath $envPath -ErrorAction Stop
                Write-SafeOutput "Environment file created from .env.example" -Status Success
                Write-SafeOutput "IMPORTANT: Configure DB_PASSWORD in .env file!" -Status Warning
            }
            catch {
                Write-SafeOutput "Failed to create .env file: $($_.Exception.Message)" -Status Error
                return $false
            }
        }
        else {
            Write-SafeOutput "Solution: Copy .env.example to .env and configure database settings" -Status Info
            return $false
        }
    }
    
    # Load and validate environment variables
    $envResult = Read-EnvFileSafely -EnvFilePath $envPath
    
    if (-not $envResult.Success) {
        Write-SafeOutput $envResult.Message -Status Error
        return $false
    }
    
    # Check required variables
    $missingVars = @()
    foreach ($requiredVar in $Script:ENV_REQUIRED_VARS) {
        $value = $envResult.Variables[$requiredVar]
        if ([string]::IsNullOrWhiteSpace($value)) {
            $missingVars += $requiredVar
        }
    }
    
    if ($missingVars.Count -gt 0) {
        Write-SafeOutput "Missing or empty environment variables: $($missingVars -join ', ')" -Status Error
        Write-SafeOutput "Configure these variables in .env file" -Status Info
        return $false
    }
    
    Write-SafeOutput "Environment file validation passed" -Status Success
    return $true
}

# ==============================================================================
# MYSQL SERVICE OPERATIONS
# ==============================================================================

function Test-MySQLService {
    <#
    .SYNOPSIS
    Tests MySQL service status and starts if needed
    #>
    param(
        [switch]$StartIfStopped
    )
    
    Write-SafeSectionHeader "MySQL Service Check" -Step 2
    
    $serviceResult = $null
    
    # Try multiple service names
    foreach ($serviceName in $Script:MYSQL_SERVICE_NAMES) {
        $serviceResult = Test-ServiceSafely -ServiceName $serviceName
        if ($serviceResult.Found) {
            break
        }
    }
    
    if (-not $serviceResult.Found) {
        Write-SafeOutput "MySQL service not found (tried: $($Script:MYSQL_SERVICE_NAMES -join ', '))" -Status Error
        Write-SafeOutput "Install MySQL 8.0 from: https://dev.mysql.com/downloads/mysql/" -Status Info
        return $false
    }
    
    $serviceName = $serviceResult.Name
    Write-SafeOutput "Found MySQL service: $($serviceResult.DisplayName)" -Status Success
    
    # Check service status
    if ($serviceResult.Status -ne "Running") {
        Write-SafeOutput "MySQL service is not running (Status: $($serviceResult.Status))" -Status Warning
        
        if ($StartIfStopped) {
            $startResult = Start-ServiceSafely -ServiceName $serviceName -Description "MySQL service"
            return $startResult
        }
        else {
            Write-SafeOutput "Start the service with: Start-Service -Name '$serviceName'" -Status Info
            return $false
        }
    }
    
    Write-SafeOutput "MySQL service is running correctly" -Status Success
    return $true
}

# ==============================================================================
# NETWORK CONNECTIVITY OPERATIONS
# ==============================================================================

function Test-MySQLNetworkAccess {
    <#
    .SYNOPSIS
    Tests MySQL network port accessibility
    #>
    param(
        [string]$HostName = "localhost",
        [int]$Port = $Script:MYSQL_DEFAULT_PORT
    )
    
    Write-SafeSectionHeader "MySQL Network Access Check" -Step 3
    
    $portTest = Test-NetworkPortSafely -HostName $HostName -Port $Port -TimeoutMs $Script:MYSQL_CONNECTION_TIMEOUT
    
    if ($portTest.Success) {
        Write-SafeOutput $portTest.Message -Status Success
        return $true
    }
    else {
        Write-SafeOutput $portTest.Message -Status Error
        Write-SafeOutput "Check MySQL configuration and Windows Firewall settings" -Status Info
        return $false
    }
}

# ==============================================================================
# MYSQL DATABASE OPERATIONS
# ==============================================================================

function Test-MySQLConnectionSecure {
    <#
    .SYNOPSIS
    Tests MySQL connection using secure methods (no password in command line)
    #>
    param(
        [hashtable]$ConnectionParams
    )
    
    Write-SafeSectionHeader "MySQL Connection Test" -Step 4
    
    $hostName = if ($ConnectionParams["DB_HOST"]) { $ConnectionParams["DB_HOST"] } else { "localhost" }
    $port = if ($ConnectionParams["DB_PORT"]) { $ConnectionParams["DB_PORT"] } else { "3306" }
    $user = if ($ConnectionParams["DB_USER"]) { $ConnectionParams["DB_USER"] } else { "root" }
    $password = $ConnectionParams["DB_PASSWORD"]
    
    if ([string]::IsNullOrWhiteSpace($password)) {
        Write-SafeOutput "DB_PASSWORD not configured in .env file" -Status Error
        Write-SafeOutput "Set DB_PASSWORD in .env file" -Status Info
        return $false
    }
    
    # Check if mysql client is available - CRITICAL REQUIREMENT
    Write-SafeOutput "Checking for MySQL client (mysql.exe) availability..." -Status Processing
    
    # Search for mysql.exe in common installation paths
    $commonMySQLPaths = @(
        "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
        "${env:ProgramFiles}\MySQL\MySQL Server 8.0\bin\mysql.exe",
        "${env:ProgramFiles}\MySQL\MySQL Server 5.7\bin\mysql.exe",
        "${env:ProgramFiles(x86)}\MySQL\MySQL Server 8.0\bin\mysql.exe",
        "${env:ProgramFiles(x86)}\MySQL\MySQL Server 5.7\bin\mysql.exe"
    )
    
    $mysqlCommand = Get-Command mysql -ErrorAction SilentlyContinue
    $mysqlPath = $null
    
    if ($mysqlCommand) {
        $mysqlPath = $mysqlCommand.Path
        Write-SafeOutput "MySQL client found in PATH: $mysqlPath" -Status Success
    } else {
        Write-SafeOutput "MySQL client not found in PATH, checking common installation locations..." -Status Processing
        
        foreach ($path in $commonMySQLPaths) {
            if (Test-Path $path) {
                $mysqlPath = $path
                Write-SafeOutput "MySQL client found at: $mysqlPath" -Status Success
                # Add to PATH temporarily for this session
                $env:PATH += ";$(Split-Path $mysqlPath -Parent)"
                break
            }
        }
    }
    
    if (-not $mysqlPath) {
        Write-SafeOutput "CRITICAL ERROR: MySQL client (mysql.exe) not found in PATH or common locations" -Status Error
        Write-SafeOutput "Searched locations:" -Status Error
        Write-SafeOutput "- System PATH environment variable" -Status Error
        foreach ($path in $commonMySQLPaths) {
            Write-SafeOutput "- $path" -Status Error
        }
        Write-SafeOutput "MySQL client is REQUIRED for database connectivity validation" -Status Error
        Write-SafeOutput "Install MySQL 8.0 from: https://dev.mysql.com/downloads/mysql/" -Status Info
        Write-SafeOutput "Or add existing MySQL installation to PATH" -Status Info
        return $false  # CRITICAL FAILURE
    }
    
    Write-SafeOutput "MySQL client validation passed: $mysqlPath" -Status Success
    
    # Create temporary configuration file for secure connection
    $tempConfigFile = [System.IO.Path]::GetTempFileName()
    $configContent = @"
[mysql]
host=$hostName
port=$port
user=$user
password=$password
"@
    
    try {
        # Write config to temp file
        $configContent | Out-File -FilePath $tempConfigFile -Encoding ASCII -Force
        
        # Test connection using config file
        $testQuery = "SELECT 1"
        $result = Invoke-SafeCommand -Command "mysql" -Arguments @("--defaults-file=$tempConfigFile", "--silent", "--execute=$testQuery") -Description "Testing MySQL connection" -IgnoreErrors
        
        if ($result.Success) {
            Write-SafeOutput "MySQL connection test successful" -Status Success
            return $true
        }
        else {
            Write-SafeOutput "MySQL connection failed - check credentials" -Status Error
            Write-SafeOutput "Verify username/password in .env file" -Status Info
            return $false
        }
    }
    catch {
        Write-SafeOutput "MySQL connection test failed: $($_.Exception.Message)" -Status Error
        return $false
    }
    finally {
        # Clean up temp file
        if (Test-Path $tempConfigFile) {
            Remove-Item $tempConfigFile -Force -ErrorAction SilentlyContinue
        }
    }
}

function Test-DatabaseExists {
    <#
    .SYNOPSIS
    Tests if the application database exists
    #>
    param(
        [hashtable]$ConnectionParams,
        [string]$DatabaseName
    )
    
    Write-SafeSectionHeader "Database Existence Check" -Step 5
    
    if ([string]::IsNullOrWhiteSpace($DatabaseName)) {
        $DatabaseName = if ($ConnectionParams["DB_NAME"]) { $ConnectionParams["DB_NAME"] } else { "yuyu_lolita" }
    }
    
    # Check if mysql client is available - CRITICAL REQUIREMENT
    Write-SafeOutput "Verifying MySQL client availability for database existence check..." -Status Processing
    
    # Search for mysql.exe in common installation paths  
    $commonMySQLPaths = @(
        "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
        "${env:ProgramFiles}\MySQL\MySQL Server 8.0\bin\mysql.exe",
        "${env:ProgramFiles}\MySQL\MySQL Server 5.7\bin\mysql.exe",
        "${env:ProgramFiles(x86)}\MySQL\MySQL Server 8.0\bin\mysql.exe",
        "${env:ProgramFiles(x86)}\MySQL\MySQL Server 5.7\bin\mysql.exe"
    )
    
    $mysqlCommand = Get-Command mysql -ErrorAction SilentlyContinue
    $mysqlPath = $null
    
    if ($mysqlCommand) {
        $mysqlPath = $mysqlCommand.Path
        Write-SafeOutput "MySQL client confirmed in PATH: $mysqlPath" -Status Success
    } else {
        Write-SafeOutput "MySQL client not in PATH, searching installation directories..." -Status Processing
        
        foreach ($path in $commonMySQLPaths) {
            if (Test-Path $path) {
                $mysqlPath = $path  
                Write-SafeOutput "MySQL client located at: $mysqlPath" -Status Success
                # Add to PATH temporarily for this session
                $env:PATH += ";$(Split-Path $mysqlPath -Parent)"
                break
            }
        }
    }
    
    if (-not $mysqlPath) {
        Write-SafeOutput "CRITICAL ERROR: MySQL client required but not found for database validation" -Status Error
        Write-SafeOutput "Cannot verify database existence without MySQL client" -Status Error
        Write-SafeOutput "Searched locations:" -Status Error
        Write-SafeOutput "- System PATH environment variable" -Status Error
        foreach ($path in $commonMySQLPaths) {
            Write-SafeOutput "- $path" -Status Error
        }
        Write-SafeOutput "Database existence validation is MANDATORY - cannot skip" -Status Error
        Write-SafeOutput "Install MySQL client or ensure it's in PATH" -Status Info
        return $false  # CRITICAL FAILURE - Cannot validate database
    }
    
    Write-SafeOutput "MySQL client validation passed for database check: $mysqlPath" -Status Success
    
    $hostName = if ($ConnectionParams["DB_HOST"]) { $ConnectionParams["DB_HOST"] } else { "localhost" }
    $port = if ($ConnectionParams["DB_PORT"]) { $ConnectionParams["DB_PORT"] } else { "3306" }
    $user = if ($ConnectionParams["DB_USER"]) { $ConnectionParams["DB_USER"] } else { "root" }
    $password = $ConnectionParams["DB_PASSWORD"]
    
    # Create temporary configuration file
    $tempConfigFile = [System.IO.Path]::GetTempFileName()
    $configContent = @"
[mysql]
host=$hostName
port=$port
user=$user
password=$password
"@
    
    try {
        $configContent | Out-File -FilePath $tempConfigFile -Encoding ASCII -Force
        
        $showDbQuery = "SHOW DATABASES LIKE '$DatabaseName'"
        $result = Invoke-SafeCommand -Command "mysql" -Arguments @("--defaults-file=$tempConfigFile", "--silent", "--execute=$showDbQuery") -Description "Checking database existence" -IgnoreErrors
        
        if ($result.Success -and $result.Output -like "*$DatabaseName*") {
            Write-SafeOutput "Database '$DatabaseName' exists" -Status Success
            return $true
        }
        else {
            Write-SafeOutput "Database '$DatabaseName' does not exist" -Status Warning
            Write-SafeOutput "Run database setup to create it" -Status Info
            return $false
        }
    }
    catch {
        Write-SafeOutput "Database check failed: $($_.Exception.Message)" -Status Error
        return $false
    }
    finally {
        if (Test-Path $tempConfigFile) {
            Remove-Item $tempConfigFile -Force -ErrorAction SilentlyContinue
        }
    }
}

# ==============================================================================
# MAIN EXECUTION PIPELINE
# ==============================================================================

function Invoke-EnvironmentCheck {
    <#
    .SYNOPSIS
    Main environment check orchestrator
    #>
    param(
        [switch]$AutoFix
    )
    
    Write-SafeHeader "MySQL8 Environment Checker for Windows" 
    Write-SafeOutput "YuYu Lolita Shopping System - Environment Validation" -Status Info
    Write-Host ""
    
    $checkResults = @()
    
    # Step 1: Environment file validation
    $envCheck = Test-EnvFileConfiguration -CreateFromTemplate:$AutoFix
    $checkResults += @{ Name = "Environment File"; Success = $envCheck }
    
    # Load environment variables for subsequent tests
    $envData = Read-EnvFileSafely
    $connectionParams = if ($envData.Success) { $envData.Variables } else { @{} }
    
    # Step 2: MySQL service check
    $serviceCheck = Test-MySQLService -StartIfStopped:$AutoFix
    $checkResults += @{ Name = "MySQL Service"; Success = $serviceCheck }
    
    # Step 3: Network access check
    $hostName = if ($connectionParams["DB_HOST"]) { $connectionParams["DB_HOST"] } else { "localhost" }
    $port = if ($connectionParams["DB_PORT"]) { [int]$connectionParams["DB_PORT"] } else { $Script:MYSQL_DEFAULT_PORT }
    $networkCheck = Test-MySQLNetworkAccess -HostName $hostName -Port $port
    $checkResults += @{ Name = "Network Access"; Success = $networkCheck }
    
    # Step 4: MySQL connection test
    $connectionCheck = Test-MySQLConnectionSecure -ConnectionParams $connectionParams
    $checkResults += @{ Name = "MySQL Connection"; Success = $connectionCheck }
    
    # Step 5: Database existence check
    $databaseCheck = Test-DatabaseExists -ConnectionParams $connectionParams
    $checkResults += @{ Name = "Database Existence"; Success = $databaseCheck }
    
    return $checkResults
}

function Show-CheckResults {
    <#
    .SYNOPSIS
    Displays formatted check results and summary
    #>
    param(
        [array]$Results
    )
    
    Write-Host ""
    Write-SafeHeader "Environment Check Results"
    
    $passedChecks = 0
    $totalChecks = $Results.Count
    
    foreach ($result in $Results) {
        $status = if ($result.Success) { "Success" } else { "Error" }
        Write-SafeOutput "$($result.Name)" -Status $status
        
        if ($result.Success) {
            $passedChecks++
        }
    }
    
    Write-Host ""
    Write-SafeOutput "Passed checks: $passedChecks of $totalChecks" -Status Info
    
    if ($passedChecks -eq $totalChecks) {
        Write-SafeOutput "All environment checks passed! System ready." -Status Complete
        Write-SafeOutput "Next step: Run database setup with 'npm run db:setup:full:windows'" -Status Info
        return $true
    }
    else {
        Write-SafeOutput "Some environment checks failed. Fix the issues above." -Status Error
        if (-not $Fix) {
            Write-SafeOutput "Tip: Use -Fix parameter for automatic fixes where possible" -Status Info
        }
        return $false
    }
}

# ==============================================================================
# SCRIPT ENTRY POINT
# ==============================================================================

try {
    # Run environment validation
    $checkResults = Invoke-EnvironmentCheck -AutoFix:$Fix
    
    # Display results and exit with appropriate code
    $allPassed = Show-CheckResults -Results $checkResults
    
    exit $(if ($allPassed) { 0 } else { 1 })
}
catch {
    Write-SafeOutput "Critical error during environment check: $($_.Exception.Message)" -Status Error
    Write-SafeOutput "Please check the PowerShell execution environment" -Status Info
    exit 1
}