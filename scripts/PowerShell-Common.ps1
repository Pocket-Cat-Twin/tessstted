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
            $result = & $Command $Arguments 2>&1
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

# ==============================================================================
# INITIALIZATION
# ==============================================================================

# Auto-initialize when script is loaded
if (-not (Test-PowerShellCompatibility)) {
    throw "PowerShell environment is not compatible"
}

Initialize-SafeEnvironment

Write-SafeOutput "PowerShell Common Library loaded successfully" -Status Success

# Export functions for use in other scripts
Export-ModuleMember -Function *