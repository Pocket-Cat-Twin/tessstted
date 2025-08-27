# PowerShell Common Library
# Enterprise-grade utilities for Lolita Fashion PowerShell scripts
# Version: 2.0 - Unicode-Safe Edition
# Author: Senior DevOps Engineer
# Last Modified: 2025-08-24

#Requires -Version 3.0

# Prevent script execution on non-Windows systems
if ($PSVersionTable.PSVersion.Major -lt 3 -or $env:OS -notlike "*Windows*") {
    Write-Error "This library is designed for Windows PowerShell 3.0+ only."
    exit 1
}

# ==============================================================================
# SAFE OUTPUT FUNCTIONS - Unicode/Encoding Safe
# ==============================================================================

# Safe status indicators - ASCII only
$Script:STATUS_SUCCESS = "[OK]"
$Script:STATUS_ERROR = "[ERROR]" 
$Script:STATUS_WARNING = "[WARN]"
$Script:STATUS_INFO = "[INFO]"
$Script:STATUS_PROCESSING = "[PROCESSING]"
$Script:STATUS_COMPLETE = "[COMPLETE]"
$Script:STATUS_SKIPPED = "[SKIP]"

# Color mapping for consistent output
$Script:COLOR_SUCCESS = "Green"
$Script:COLOR_ERROR = "Red"
$Script:COLOR_WARNING = "Yellow"
$Script:COLOR_INFO = "Cyan"
$Script:COLOR_PROCESSING = "Magenta"
$Script:COLOR_HEADER = "Blue"
$Script:COLOR_COMPLETE = "Green"

function Write-SafeOutput {
    <#
    .SYNOPSIS
    Writes output with safe ASCII characters and proper encoding
    
    .PARAMETER Message
    The message to display
    
    .PARAMETER Status
    Status type: Success, Error, Warning, Info, Processing, Complete, Skip
    
    .PARAMETER NoNewline
    Don't add newline at the end
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,
        
        [ValidateSet("Success", "Error", "Warning", "Info", "Processing", "Complete", "Skip")]
        [string]$Status = "Info",
        
        [switch]$NoNewline
    )
    
    $prefix = switch ($Status) {
        "Success" { $Script:STATUS_SUCCESS }
        "Error" { $Script:STATUS_ERROR }
        "Warning" { $Script:STATUS_WARNING }
        "Info" { $Script:STATUS_INFO }
        "Processing" { $Script:STATUS_PROCESSING }
        "Complete" { $Script:STATUS_COMPLETE }
        "Skip" { $Script:STATUS_SKIPPED }
    }
    
    $color = switch ($Status) {
        "Success" { $Script:COLOR_SUCCESS }
        "Error" { $Script:COLOR_ERROR }
        "Warning" { $Script:COLOR_WARNING }
        "Info" { $Script:COLOR_INFO }
        "Processing" { $Script:COLOR_PROCESSING }
        "Complete" { $Script:COLOR_COMPLETE }
        "Skip" { $Script:COLOR_WARNING }
    }
    
    $fullMessage = "$prefix $Message"
    
    if ($NoNewline) {
        Write-Host $fullMessage -ForegroundColor $color -NoNewline
    } else {
        Write-Host $fullMessage -ForegroundColor $color
    }
}

function Write-SafeHeader {
    <#
    .SYNOPSIS
    Writes a safe header with consistent formatting
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        
        [string]$Separator = "="
    )
    
    Write-Host ""
    Write-Host $Title -ForegroundColor $Script:COLOR_HEADER
    Write-Host ($Separator * $Title.Length) -ForegroundColor $Script:COLOR_HEADER
    Write-Host ""
}

function Write-SafeSectionHeader {
    <#
    .SYNOPSIS
    Writes a section header with step numbering
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        
        [int]$Step = 0
    )
    
    if ($Step -gt 0) {
        Write-Host ""
        Write-Host "[STEP $Step] $Title" -ForegroundColor $Script:COLOR_HEADER
    } else {
        Write-Host ""
        Write-Host "[$Title]" -ForegroundColor $Script:COLOR_HEADER
    }
}

# ==============================================================================
# ERROR HANDLING AND VALIDATION
# ==============================================================================

function Test-PowerShellCompatibility {
    <#
    .SYNOPSIS
    Validates PowerShell environment compatibility
    #>
    
    $issues = @()
    
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 3) {
        $issues += "PowerShell version $($PSVersionTable.PSVersion) is not supported. Requires 3.0+"
    }
    
    # Check Windows OS
    if ($env:OS -notlike "*Windows*") {
        $issues += "Non-Windows operating system detected. This is Windows-only."
    }
    
    # Check execution policy
    $executionPolicy = Get-ExecutionPolicy
    if ($executionPolicy -eq "Restricted") {
        $issues += "PowerShell execution policy is Restricted. Run: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"
    }
    
    if ($issues.Count -gt 0) {
        Write-SafeOutput "PowerShell Compatibility Issues Found:" -Status Error
        foreach ($issue in $issues) {
            Write-SafeOutput "  - $issue" -Status Error
        }
        return $false
    }
    
    return $true
}

function Invoke-SafeCommand {
    <#
    .SYNOPSIS
    Executes a command with proper error handling and logging
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        
        [string[]]$Arguments = @(),
        
        [string]$WorkingDirectory = $PWD,
        
        [string]$Description = "Running command",
        
        [switch]$IgnoreErrors,
        
        [int]$TimeoutSeconds = 300
    )
    
    Write-SafeOutput "$Description..." -Status Processing
    
    try {
        $originalLocation = Get-Location
        
        if ($WorkingDirectory -ne $PWD) {
            Set-Location $WorkingDirectory
        }
        
        $startTime = Get-Date
        
        if ($Arguments.Count -gt 0) {
            $result = & $Command @Arguments 2>&1
        } else {
            $result = & $Command 2>&1
        }
        
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        
        if ($LASTEXITCODE -eq 0) {
            Write-SafeOutput "$Description completed in $([math]::Round($duration, 1))s" -Status Success
            return @{
                Success = $true
                Output = $result
                ExitCode = $LASTEXITCODE
                Duration = $duration
            }
        } else {
            if ($IgnoreErrors) {
                Write-SafeOutput "$Description failed (exit code: $LASTEXITCODE) - continuing..." -Status Warning
                return @{
                    Success = $false
                    Output = $result
                    ExitCode = $LASTEXITCODE
                    Duration = $duration
                }
            } else {
                Write-SafeOutput "$Description failed (exit code: $LASTEXITCODE)" -Status Error
                Write-SafeOutput "Error output: $result" -Status Error
                throw "Command failed: $Command"
            }
        }
    }
    catch {
        Write-SafeOutput "$Description failed with exception: $($_.Exception.Message)" -Status Error
        if (-not $IgnoreErrors) {
            throw
        }
        return @{
            Success = $false
            Output = $_.Exception.Message
            ExitCode = -1
            Duration = 0
        }
    }
    finally {
        if ($WorkingDirectory -ne $PWD) {
            Set-Location $originalLocation
        }
    }
}

# ==============================================================================
# ENVIRONMENT AND SYSTEM UTILITIES
# ==============================================================================

function Initialize-SafeEnvironment {
    <#
    .SYNOPSIS
    Initializes safe environment settings for PowerShell scripts
    #>
    
    # Set error action preference for consistent behavior
    $ErrorActionPreference = "Stop"
    
    # Set UTF-8 encoding for console output (safe method)
    try {
        # Only set encoding if it's supported
        if ([Environment]::OSVersion.Version.Major -ge 10) {
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
            [Console]::InputEncoding = [System.Text.Encoding]::UTF8
        }
    }
    catch {
        Write-SafeOutput "Could not set UTF-8 encoding (not critical)" -Status Warning
    }
    
    # Set console title safely
    try {
        $Host.UI.RawUI.WindowTitle = "Lolita Fashion - PowerShell Script"
    }
    catch {
        # Silently continue if setting title fails (e.g., in ISE)
    }
    
    return $true
}

function Get-ProjectRoot {
    <#
    .SYNOPSIS
    Gets the project root directory safely
    #>
    
    $currentPath = $PSScriptRoot
    if (-not $currentPath) {
        $currentPath = $PWD
    }
    
    # Look for package.json or .git to identify project root
    $searchPath = $currentPath
    $maxDepth = 5
    $depth = 0
    
    while ($depth -lt $maxDepth) {
        if (Test-Path (Join-Path $searchPath "package.json")) {
            return $searchPath
        }
        
        if (Test-Path (Join-Path $searchPath ".git")) {
            return $searchPath
        }
        
        $parentPath = Split-Path $searchPath -Parent
        if ($parentPath -eq $searchPath) {
            break  # Reached root
        }
        
        $searchPath = $parentPath
        $depth++
    }
    
    # Fallback to script directory's parent
    return Split-Path $currentPath -Parent
}

# ==============================================================================
# SERVICE AND PROCESS MANAGEMENT
# ==============================================================================

function Test-ServiceSafely {
    <#
    .SYNOPSIS
    Tests if a Windows service exists and its status safely
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$ServiceName,
        
        [string[]]$PreferredVersions = @()
    )
    
    try {
        $services = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        
        if (-not $services) {
            return @{
                Found = $false
                Service = $null
                Status = "NotFound"
            }
        }
        
        # If multiple services found, prefer specific versions
        $targetService = $services | Select-Object -First 1
        
        if ($PreferredVersions.Count -gt 0 -and $services.Count -gt 1) {
            foreach ($version in $PreferredVersions) {
                $preferred = $services | Where-Object { $_.Name -like "*$version*" } | Select-Object -First 1
                if ($preferred) {
                    $targetService = $preferred
                    break
                }
            }
        }
        
        return @{
            Found = $true
            Service = $targetService
            Status = $targetService.Status
            Name = $targetService.Name
            DisplayName = $targetService.DisplayName
        }
    }
    catch {
        return @{
            Found = $false
            Service = $null
            Status = "Error"
            Error = $_.Exception.Message
        }
    }
}

function Start-ServiceSafely {
    <#
    .SYNOPSIS
    Starts a Windows service safely with proper error handling
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$ServiceName,
        
        [int]$TimeoutSeconds = 30,
        
        [string]$Description = "service"
    )
    
    try {
        Write-SafeOutput "Starting $Description ($ServiceName)..." -Status Processing
        
        Start-Service -Name $ServiceName -ErrorAction Stop
        
        # Wait for service to start
        $timeout = $TimeoutSeconds
        while ($timeout -gt 0) {
            $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
            if ($service -and $service.Status -eq "Running") {
                Write-SafeOutput "$Description started successfully" -Status Success
                return $true
            }
            
            Start-Sleep -Seconds 1
            $timeout--
        }
        
        Write-SafeOutput "$Description failed to start within $TimeoutSeconds seconds" -Status Error
        return $false
    }
    catch {
        Write-SafeOutput "Failed to start ${Description}: $($_.Exception.Message)" -Status Error
        return $false
    }
}

# ==============================================================================
# NETWORK AND CONNECTIVITY
# ==============================================================================

function Test-NetworkPortSafely {
    <#
    .SYNOPSIS
    Tests if a network port is accessible safely
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$HostName,
        
        [Parameter(Mandatory = $true)]
        [int]$Port,
        
        [int]$TimeoutMs = 5000
    )
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connectTask = $tcpClient.ConnectAsync($HostName, $Port)
        
        if ($connectTask.Wait($TimeoutMs)) {
            $tcpClient.Close()
            return @{
                Success = $true
                Message = "Port $Port on $HostName is accessible"
            }
        } else {
            return @{
                Success = $false
                Message = "Connection to $HostName`:$Port timed out"
            }
        }
    }
    catch {
        return @{
            Success = $false
            Message = "Failed to connect to $HostName`:$Port - $($_.Exception.Message)"
        }
    }
}

# ==============================================================================
# FILE AND DIRECTORY OPERATIONS
# ==============================================================================

function Test-PathSafely {
    <#
    .SYNOPSIS
    Tests if a path exists with enhanced error handling
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        
        [ValidateSet("Any", "File", "Directory")]
        [string]$Type = "Any"
    )
    
    try {
        $exists = Test-Path $Path
        
        if (-not $exists) {
            return @{
                Exists = $false
                Type = "None"
                Message = "Path does not exist: $Path"
            }
        }
        
        $item = Get-Item $Path -ErrorAction SilentlyContinue
        
        if (-not $item) {
            return @{
                Exists = $true
                Type = "Unknown"
                Message = "Path exists but cannot determine type: $Path"
            }
        }
        
        $actualType = if ($item -is [System.IO.DirectoryInfo]) { "Directory" } else { "File" }
        
        $matchesType = switch ($Type) {
            "Any" { $true }
            "File" { $actualType -eq "File" }
            "Directory" { $actualType -eq "Directory" }
        }
        
        return @{
            Exists = $true
            Type = $actualType
            MatchesType = $matchesType
            Message = if ($matchesType) { "Valid $actualType found: $Path" } else { "Expected $Type but found $actualType`: $Path" }
            Item = $item
        }
    }
    catch {
        return @{
            Exists = $false
            Type = "Error"
            MatchesType = $false
            Message = "Error checking path: $($_.Exception.Message)"
            Error = $_.Exception.Message
        }
    }
}

function New-TempConfigFile {
    <#
    .SYNOPSIS
    Creates a temporary configuration file with secure cleanup
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$Content,
        
        [string]$FileExtension = ".tmp",
        
        [switch]$SecureDelete
    )
    
    try {
        $tempFile = [System.IO.Path]::GetTempFileName()
        
        if ($FileExtension -ne ".tmp") {
            $newTempFile = [System.IO.Path]::ChangeExtension($tempFile, $FileExtension)
            Move-Item $tempFile $newTempFile -Force
            $tempFile = $newTempFile
        }
        
        # Write content with proper encoding
        $Content | Out-File -FilePath $tempFile -Encoding ASCII -Force
        
        return @{
            Success = $true
            FilePath = $tempFile
            CleanupAction = {
                param($Path, $Secure)
                try {
                    if (Test-Path $Path) {
                        if ($Secure) {
                            # Overwrite with random data before deletion
                            $randomData = -join ((1..1024) | ForEach-Object { Get-Random -Maximum 256 })
                            $randomData | Out-File -FilePath $Path -Encoding ASCII -Force -ErrorAction SilentlyContinue
                        }
                        Remove-Item $Path -Force -ErrorAction SilentlyContinue
                    }
                } catch {
                    # Silently continue if cleanup fails
                }
            }.GetNewClosure()
        }
    }
    catch {
        return @{
            Success = $false
            FilePath = $null
            Message = "Failed to create temp file: $($_.Exception.Message)"
            Error = $_.Exception.Message
        }
    }
}

function Invoke-WithTempFile {
    <#
    .SYNOPSIS
    Executes a script block with a temporary file that gets automatically cleaned up
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$Content,
        
        [Parameter(Mandatory = $true)]
        [ScriptBlock]$ScriptBlock,
        
        [string]$FileExtension = ".tmp",
        
        [switch]$SecureDelete
    )
    
    $tempFileResult = New-TempConfigFile -Content $Content -FileExtension $FileExtension -SecureDelete:$SecureDelete
    
    if (-not $tempFileResult.Success) {
        return @{
            Success = $false
            Message = $tempFileResult.Message
            Error = $tempFileResult.Error
        }
    }
    
    try {
        $result = & $ScriptBlock $tempFileResult.FilePath
        return @{
            Success = $true
            Result = $result
            TempFilePath = $tempFileResult.FilePath
        }
    }
    catch {
        return @{
            Success = $false
            Message = "Script block execution failed: $($_.Exception.Message)"
            Error = $_.Exception.Message
        }
    }
    finally {
        # Always cleanup the temp file
        if ($tempFileResult.CleanupAction) {
            & $tempFileResult.CleanupAction $tempFileResult.FilePath $SecureDelete
        }
    }
}

# ==============================================================================
# ENVIRONMENT AND CONFIGURATION MANAGEMENT
# ==============================================================================

function Read-EnvFileSafely {
    <#
    .SYNOPSIS
    Safely reads and parses .env files with comprehensive error handling
    #>
    param(
        [string]$EnvFilePath,
        
        [string[]]$RequiredVariables = @(),
        
        [switch]$CreateFromTemplate
    )
    
    if (-not $EnvFilePath) {
        $projectRoot = Get-ProjectRoot
        $EnvFilePath = Join-Path $projectRoot ".env"
    }
    
    # Check if .env exists, create from template if requested
    if (-not (Test-Path $EnvFilePath)) {
        if ($CreateFromTemplate) {
            $templatePath = $EnvFilePath -replace '\\.env$', '.env.example'
            if (Test-Path $templatePath) {
                try {
                    Copy-Item $templatePath $EnvFilePath -ErrorAction Stop
                    Write-SafeOutput "Created .env from template" -Status Success
                } catch {
                    return @{
                        Success = $false
                        Variables = @{}
                        Message = "Failed to create .env from template: $($_.Exception.Message)"
                        RequiredMissing = $RequiredVariables
                    }
                }
            } else {
                return @{
                    Success = $false
                    Variables = @{}
                    Message = "Environment file not found and no template available: $EnvFilePath"
                    RequiredMissing = $RequiredVariables
                }
            }
        } else {
            return @{
                Success = $false
                Variables = @{}
                Message = "Environment file not found: $EnvFilePath"
                RequiredMissing = $RequiredVariables
            }
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
        
        # Check required variables
        $missingVars = @()
        foreach ($requiredVar in $RequiredVariables) {
            $value = $envVars[$requiredVar]
            if ([string]::IsNullOrWhiteSpace($value)) {
                $missingVars += $requiredVar
            }
        }
        
        return @{
            Success = $missingVars.Count -eq 0
            Variables = $envVars
            Message = if ($missingVars.Count -eq 0) { "Environment file loaded successfully" } else { "Missing required variables: $($missingVars -join ', ')" }
            Path = $EnvFilePath
            RequiredMissing = $missingVars
        }
    }
    catch {
        return @{
            Success = $false
            Variables = @{}
            Message = "Failed to read environment file: $($_.Exception.Message)"
            Error = $_.Exception.Message
            RequiredMissing = $RequiredVariables
        }
    }
}

function Test-CommandAvailability {
    <#
    .SYNOPSIS
    Tests if multiple commands are available in the system PATH
    #>
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$CommandMap,
        
        [switch]$ShowVersions
    )
    
    $results = @{}
    $allAvailable = $true
    
    foreach ($command in $CommandMap.Keys) {
        $commandPath = Get-Command $command -ErrorAction SilentlyContinue
        
        if ($commandPath) {
            $version = "Unknown"
            if ($ShowVersions) {
                try {
                    $versionOutput = & $command --version 2>&1 | Select-Object -First 1
                    $version = $versionOutput -replace '\n.*', ''
                } catch {
                    $version = "Unknown"
                }
            }
            
            $results[$command] = @{
                Available = $true
                Path = $commandPath.Path
                Version = $version
                Message = "Found $command"
            }
            
            Write-SafeOutput "Found $command`: $version" -Status Success
        }
        else {
            $results[$command] = @{
                Available = $false
                Path = $null
                Version = $null
                Message = "Missing required command: $command"
                InstallInfo = $CommandMap[$command]
            }
            
            Write-SafeOutput "Missing required command: $command" -Status Error
            Write-SafeOutput "Install: $($CommandMap[$command])" -Status Info
            $allAvailable = $false
        }
    }
    
    return @{
        AllAvailable = $allAvailable
        Commands = $results
        MissingCount = ($results.Values | Where-Object { -not $_.Available }).Count
    }
}

# ==============================================================================
# DATABASE UTILITIES
# ==============================================================================

function Test-MySQLConnectionSecure {
    <#
    .SYNOPSIS
    Tests MySQL connection using secure temporary configuration files
    #>
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$ConnectionParams,
        
        [string]$TestQuery = "SELECT 1",
        
        [int]$TimeoutSeconds = 10
    )
    
    $hostName = if ($ConnectionParams["DB_HOST"]) { $ConnectionParams["DB_HOST"] } else { "localhost" }
    $port = if ($ConnectionParams["DB_PORT"]) { $ConnectionParams["DB_PORT"] } else { "3306" }
    $user = if ($ConnectionParams["DB_USER"]) { $ConnectionParams["DB_USER"] } else { "root" }
    $password = $ConnectionParams["DB_PASSWORD"]
    
    if ([string]::IsNullOrWhiteSpace($password)) {
        return @{
            Success = $false
            Message = "DB_PASSWORD not configured"
            Error = "Missing password"
        }
    }
    
    # Check if mysql client is available - CRITICAL REQUIREMENT
    Write-SafeOutput "Validating MySQL client availability for secure connection test..." -Status Processing
    
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
        Write-SafeOutput "MySQL client located in PATH: $mysqlPath" -Status Success
    } else {
        Write-SafeOutput "MySQL client not in PATH, checking standard installation paths..." -Status Processing
        
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
        Write-SafeOutput "CRITICAL ERROR: MySQL client is mandatory but not found" -Status Error
        Write-SafeOutput "Cannot perform secure MySQL connection testing without client" -Status Error
        Write-SafeOutput "Comprehensive search performed:" -Status Error
        Write-SafeOutput "- System PATH environment variable" -Status Error
        foreach ($path in $commonMySQLPaths) {
            Write-SafeOutput "- $path" -Status Error
        }
        
        return @{
            Success = $false
            Message = "CRITICAL FAILURE: MySQL client (mysql.exe) not found - database connectivity validation impossible"
            Error = "MySQL client not available in PATH or standard installation locations" 
            RequiredAction = "Install MySQL client or add existing installation to PATH"
            SearchedPaths = $commonMySQLPaths
            IsCritical = $true
        }
    }
    
    Write-SafeOutput "MySQL client validation successful: $mysqlPath" -Status Success
    
    # Create MySQL configuration content
    $configContent = @"
[mysql]
host=$hostName
port=$port
user=$user
password=$password
"@
    
    # Use secure temp file for connection
    $tempFileResult = Invoke-WithTempFile -Content $configContent -SecureDelete -ScriptBlock {
        param($TempConfigFile)
        
        try {
            $result = Invoke-SafeCommand -Command "mysql" -Arguments @("--defaults-file=$TempConfigFile", "--silent", "--execute=$TestQuery") -Description "Testing MySQL connection" -TimeoutSeconds $TimeoutSeconds -IgnoreErrors
            
            return @{
                Success = $result.Success
                Output = $result.Output
                ExitCode = $result.ExitCode
                Duration = $result.Duration
            }
        }
        catch {
            return @{
                Success = $false
                Output = $_.Exception.Message
                ExitCode = -1
                Duration = 0
            }
        }
    }
    
    if ($tempFileResult.Success -and $tempFileResult.Result.Success) {
        return @{
            Success = $true
            Message = "MySQL connection successful"
            Duration = $tempFileResult.Result.Duration
            Host = $hostName
            Port = $port
            User = $user
        }
    }
    else {
        $errorMessage = if ($tempFileResult.Success) { $tempFileResult.Result.Output } else { $tempFileResult.Message }
        return @{
            Success = $false
            Message = "MySQL connection failed"
            Error = $errorMessage
            Host = $hostName
            Port = $port
            User = $user
        }
    }
}

function Test-MySQLDatabase {
    <#
    .SYNOPSIS
    Tests if a specific MySQL database exists
    #>
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$ConnectionParams,
        
        [Parameter(Mandatory = $true)]
        [string]$DatabaseName,
        
        [int]$TimeoutSeconds = 10
    )
    
    $showDbQuery = "SHOW DATABASES LIKE '$DatabaseName'"
    
    $connectionTest = Test-MySQLConnectionSecure -ConnectionParams $ConnectionParams -TestQuery $showDbQuery -TimeoutSeconds $TimeoutSeconds
    
    if (-not $connectionTest.Success) {
        return $connectionTest  # Pass through connection error
    }
    
    # Check if database name appears in output
    if ($connectionTest.Success -and $connectionTest.ContainsKey("Output")) {
        $databaseExists = $connectionTest.Output -like "*$DatabaseName*"
        
        return @{
            Success = $true
            DatabaseExists = $databaseExists
            DatabaseName = $DatabaseName
            Message = if ($databaseExists) { "Database '$DatabaseName' exists" } else { "Database '$DatabaseName' does not exist" }
            Host = $connectionTest.Host
            Port = $connectionTest.Port
        }
    }
    
    return @{
        Success = $false
        DatabaseExists = $false
        DatabaseName = $DatabaseName
        Message = "Could not determine database existence"
        Error = "Unexpected response format"
    }
}

function Get-MySQLServiceInfo {
    <#
    .SYNOPSIS
    Gets comprehensive MySQL service information on Windows
    #>
    param(
        [string[]]$ServiceNames = @("MySQL80", "MySQL", "MySQL57"),
        
        [switch]$IncludeVersion
    )
    
    $serviceInfo = @{
        Found = $false
        Services = @()
        PreferredService = $null
        AllRunning = $false
    }
    
    foreach ($serviceName in $ServiceNames) {
        $serviceResult = Test-ServiceSafely -ServiceName $serviceName
        
        if ($serviceResult.Found) {
            $info = @{
                Name = $serviceResult.Name
                DisplayName = $serviceResult.DisplayName
                Status = $serviceResult.Status
                IsRunning = $serviceResult.Status -eq "Running"
                IsPreferred = $false
            }
            
            if ($IncludeVersion) {
                try {
                    # Try to get MySQL version if service is running
                    if ($info.IsRunning) {
                        $versionResult = & mysql --version 2>&1 | Select-Object -First 1
                        $info.Version = $versionResult -replace '.*Ver ([0-9\.]+).*', '$1'
                    }
                    else {
                        $info.Version = "Unknown (service not running)"
                    }
                }
                catch {
                    $info.Version = "Unknown"
                }
            }
            
            $serviceInfo.Services += $info
            $serviceInfo.Found = $true
            
            # Mark first found service as preferred
            if (-not $serviceInfo.PreferredService) {
                $info.IsPreferred = $true
                $serviceInfo.PreferredService = $info
            }
        }
    }
    
    $serviceInfo.AllRunning = ($serviceInfo.Services | Where-Object { -not $_.IsRunning }).Count -eq 0
    
    return $serviceInfo
}

# ==============================================================================
# PROCESS AND PERFORMANCE MONITORING
# ==============================================================================

function Get-SystemResourceInfo {
    <#
    .SYNOPSIS
    Gets current system resource information for monitoring
    #>
    param(
        [switch]$IncludeProcesses
    )
    
    try {
        $memoryInfo = Get-WmiObject -Class Win32_ComputerSystem -ErrorAction SilentlyContinue
        $osInfo = Get-WmiObject -Class Win32_OperatingSystem -ErrorAction SilentlyContinue
        $processorInfo = Get-WmiObject -Class Win32_Processor -ErrorAction SilentlyContinue | Select-Object -First 1
        
        $resourceInfo = @{
            Success = $true
            Timestamp = Get-Date
            Memory = @{
                TotalGB = if ($memoryInfo) { [math]::Round($memoryInfo.TotalPhysicalMemory / 1GB, 2) } else { "Unknown" }
                AvailableGB = if ($osInfo) { [math]::Round($osInfo.FreePhysicalMemory / 1MB / 1024, 2) } else { "Unknown" }
                UsedPercentage = if ($osInfo -and $memoryInfo) { 
                    [math]::Round((($memoryInfo.TotalPhysicalMemory - ($osInfo.FreePhysicalMemory * 1024)) / $memoryInfo.TotalPhysicalMemory) * 100, 1)
                } else { "Unknown" }
            }
            Processor = @{
                Name = if ($processorInfo) { $processorInfo.Name } else { "Unknown" }
                Cores = if ($processorInfo) { $processorInfo.NumberOfCores } else { "Unknown" }
                LogicalProcessors = if ($processorInfo) { $processorInfo.NumberOfLogicalProcessors } else { "Unknown" }
            }
            Disk = @{
                SystemDrive = $env:SystemDrive
                FreeSpaceGB = "Unknown"
            }
        }
        
        # Get disk space for system drive
        try {
            $systemDisk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='$($env:SystemDrive)'" -ErrorAction SilentlyContinue
            if ($systemDisk) {
                $resourceInfo.Disk.FreeSpaceGB = [math]::Round($systemDisk.FreeSpace / 1GB, 2)
                $resourceInfo.Disk.TotalSpaceGB = [math]::Round($systemDisk.Size / 1GB, 2)
                $resourceInfo.Disk.UsedPercentage = [math]::Round((($systemDisk.Size - $systemDisk.FreeSpace) / $systemDisk.Size) * 100, 1)
            }
        }
        catch {
            # Continue with unknown disk info
        }
        
        if ($IncludeProcesses) {
            $topProcesses = Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 5 | ForEach-Object {
                @{
                    Name = $_.ProcessName
                    MemoryMB = [math]::Round($_.WorkingSet / 1MB, 1)
                    CPU = if ($_.CPU) { [math]::Round($_.CPU, 1) } else { 0 }
                }
            }
            $resourceInfo.TopProcesses = $topProcesses
        }
        
        return $resourceInfo
    }
    catch {
        return @{
            Success = $false
            Message = "Failed to get system resource information: $($_.Exception.Message)"
            Error = $_.Exception.Message
        }
    }
}

# ==============================================================================
# INITIALIZATION
# ==============================================================================

# Auto-initialize when script is loaded
if (-not (Test-PowerShellCompatibility)) {
    throw "PowerShell environment is not compatible"
}

Initialize-SafeEnvironment

Write-SafeOutput "PowerShell Common Library v2.1 (Enterprise Enhanced) loaded successfully" -Status Success

# NOTE: Export-ModuleMember is not used in dot-sourced scripts
# Functions are automatically available when dot-sourcing
# For module architecture, use PowerShell-Common.psm1 instead