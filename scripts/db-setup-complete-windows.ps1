# ================================
# Complete Database Setup for Windows
# YuYu Lolita Shopping System
# Enterprise-grade database initialization
# ================================

[CmdletBinding()]
param(
    [switch]$Force = $false,
    [switch]$SkipEnvironmentCheck = $false,
    [int]$TimeoutMinutes = 15
)

# Import common functions with validation
$commonLibPath = Join-Path $PSScriptRoot "PowerShell-Common.ps1"
if (-not (Test-Path $commonLibPath)) {
    Write-Error "Required PowerShell-Common.ps1 not found at: $commonLibPath"
    exit 1
}
. $commonLibPath

# Setup configuration
$Script:SETUP_TIMEOUT_SECONDS = $TimeoutMinutes * 60
$Script:REQUIRED_COMMANDS = @{
    "bun" = "Bun runtime (https://bun.sh/docs/installation)"
    "powershell" = "PowerShell 5.1+ (Windows built-in)"
}

# Phase configuration
$Script:SETUP_PHASES = @{
    "EnvironmentCheck" = @{
        Name = "Environment Validation"
        Description = "Windows environment and MySQL service validation"
        ScriptName = "db-environment-check-windows.ps1"
        Required = $true
    }
    "DatabaseMigrations" = @{
        Name = "Database Schema Migration"
        Description = "MySQL table creation and schema setup"
        Command = "npm"
        Arguments = @("run", "db:migrate:windows")
        WorkingDir = "."
        Required = $true
    }
    "UserSeeding" = @{
        Name = "Initial User Creation"
        Description = "Admin and test user account creation"
        Command = "npm"
        Arguments = @("run", "db:seed:windows")
        WorkingDir = "."
        Required = $true
    }
    "HealthCheck" = @{
        Name = "Final System Validation"
        Description = "Database connectivity and data integrity check"
        Command = "npm"
        Arguments = @("run", "db:health:mysql")
        WorkingDir = "."
        Required = $false
    }
}

# ==============================================================================
# DEPENDENCY VALIDATION
# ==============================================================================

function Test-SetupDependencies {
    <#
    .SYNOPSIS
    Validates all required dependencies for database setup
    #>
    
    Write-SafeSectionHeader "Setup Dependencies Check" -Step 1
    
    $allDependenciesFound = $true
    
    foreach ($command in $Script:REQUIRED_COMMANDS.Keys) {
        $commandPath = Get-Command $command -ErrorAction SilentlyContinue
        
        if ($commandPath) {
            $version = try {
                $versionOutput = & $command --version 2>&1
                $versionOutput -replace '\n.*', ''  # Take first line only
            } catch {
                "Unknown"
            }
            
            Write-SafeOutput "Found $command`: $version" -Status Success
        }
        else {
            Write-SafeOutput "Missing required command: $command" -Status Error
            Write-SafeOutput "Install: $($Script:REQUIRED_COMMANDS[$command])" -Status Info
            $allDependenciesFound = $false
        }
    }
    
    if (-not $allDependenciesFound) {
        Write-SafeOutput "Setup dependencies check failed" -Status Error
        return $false
    }
    
    Write-SafeOutput "All setup dependencies available" -Status Success
    return $true
}

function Test-ProjectStructure {
    <#
    .SYNOPSIS
    Validates project structure for database setup
    #>
    
    Write-SafeSectionHeader "Project Structure Validation" -Step 2
    
    $projectRoot = Get-ProjectRoot
    $allPathsValid = $true
    
    # Check DB package directory
    $dbPackagePath = Join-Path $projectRoot "packages\db"
    $dbPathTest = Test-PathSafely -Path $dbPackagePath -Type Directory
    
    if ($dbPathTest.Exists -and $dbPathTest.MatchesType) {
        Write-SafeOutput "Found database package directory" -Status Success
    }
    else {
        Write-SafeOutput "Missing database package directory: $dbPackagePath" -Status Error
        $allPathsValid = $false
    }
    
    # Check required scripts
    $envCheckScript = Join-Path $PSScriptRoot "db-environment-check-windows.ps1"
    $envScriptTest = Test-PathSafely -Path $envCheckScript -Type File
    
    if ($envScriptTest.Exists -and $envScriptTest.MatchesType) {
        Write-SafeOutput "Found environment check script" -Status Success
    }
    else {
        Write-SafeOutput "Missing environment check script: $envCheckScript" -Status Error
        $allPathsValid = $false
    }
    
    # Check seed script
    $seedScript = Join-Path $projectRoot "packages\db\src\seed-users.ts"
    $seedScriptTest = Test-PathSafely -Path $seedScript -Type File
    
    if ($seedScriptTest.Exists -and $seedScriptTest.MatchesType) {
        Write-SafeOutput "Found user seed script" -Status Success
    }
    else {
        Write-SafeOutput "Missing user seed script: $seedScript" -Status Error
        $allPathsValid = $false
    }
    
    if (-not $allPathsValid) {
        Write-SafeOutput "Project structure validation failed" -Status Error
        return $false
    }
    
    Write-SafeOutput "Project structure validation passed" -Status Success
    return $true
}

# ==============================================================================
# SETUP PHASE OPERATIONS
# ==============================================================================

function Invoke-EnvironmentCheckPhase {
    <#
    .SYNOPSIS
    Executes environment validation phase
    #>
    param(
        [switch]$AutoFix
    )
    
    Write-SafeSectionHeader "Environment Validation Phase" -Step 0
    
    $checkScript = Join-Path $PSScriptRoot $Script:SETUP_PHASES["EnvironmentCheck"].ScriptName
    $scriptTest = Test-PathSafely -Path $checkScript -Type File
    
    if (-not ($scriptTest.Exists -and $scriptTest.MatchesType)) {
        Write-SafeOutput "Environment check script not found: $checkScript" -Status Error
        return @{ Success = $false; Message = "Script not found"; Phase = "EnvironmentCheck" }
    }
    
    $arguments = @("-ExecutionPolicy", "Bypass", "-File", $checkScript)
    if ($AutoFix) {
        $arguments += "-Fix"
    }
    
    $result = Invoke-SafeCommand -Command "powershell" -Arguments $arguments -Description "Running environment validation" -TimeoutSeconds $Script:SETUP_TIMEOUT_SECONDS -IgnoreErrors
    
    if ($result.Success) {
        Write-SafeOutput "Environment validation completed successfully" -Status Success
        return @{ 
            Success = $true
            Phase = "EnvironmentCheck"
            Duration = $result.Duration
            Message = "Environment validation passed"
        }
    }
    else {
        Write-SafeOutput "Environment validation failed (exit code: $($result.ExitCode))" -Status Error
        Write-SafeOutput "Fix environment issues and run again" -Status Info
        return @{ 
            Success = $false
            Phase = "EnvironmentCheck"
            ExitCode = $result.ExitCode
            Message = "Environment validation failed"
            Output = $result.Output
        }
    }
}

function Invoke-DatabasePhase {
    <#
    .SYNOPSIS
    Executes database-related phases (migrations, seeding, health check)
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$PhaseName,
        
        [Parameter(Mandatory = $true)]
        [hashtable]$PhaseConfig
    )
    
    Write-SafeSectionHeader "$($PhaseConfig.Name) Phase" -Step 0
    Write-SafeOutput "$($PhaseConfig.Description)..." -Status Processing
    
    $projectRoot = Get-ProjectRoot
    $workingDirectory = Join-Path $projectRoot $PhaseConfig.WorkingDir
    
    # Validate working directory
    $dirTest = Test-PathSafely -Path $workingDirectory -Type Directory
    if (-not ($dirTest.Exists -and $dirTest.MatchesType)) {
        Write-SafeOutput "Working directory not found: $workingDirectory" -Status Error
        return @{ Success = $false; Phase = $PhaseName; Message = "Working directory not found" }
    }
    
    # Execute phase command
    $result = Invoke-SafeCommand -Command $PhaseConfig.Command -Arguments $PhaseConfig.Arguments -WorkingDirectory $workingDirectory -Description $PhaseConfig.Name -TimeoutSeconds $Script:SETUP_TIMEOUT_SECONDS
    
    if ($result.Success) {
        Write-SafeOutput "$($PhaseConfig.Name) completed successfully" -Status Success
        return @{ 
            Success = $true
            Phase = $PhaseName
            Duration = $result.Duration
            Message = "$($PhaseConfig.Name) completed"
        }
    }
    else {
        Write-SafeOutput "$($PhaseConfig.Name) failed (exit code: $($result.ExitCode))" -Status Error
        Write-SafeOutput "Phase error: $($result.Output)" -Status Error
        return @{ 
            Success = $false
            Phase = $PhaseName
            ExitCode = $result.ExitCode
            Message = "$($PhaseConfig.Name) failed"
            Output = $result.Output
        }
    }
}

# ==============================================================================
# SETUP ORCHESTRATION
# ==============================================================================

function Invoke-DatabaseInitialization {
    <#
    .SYNOPSIS
    Main database initialization orchestration function
    #>
    
    Write-SafeHeader "Complete Database Setup for Windows"
    Write-SafeOutput "YuYu Lolita Shopping System - Full Database Initialization" -Status Info
    Write-SafeOutput "MySQL8 + Auto User Creation" -Status Info
    Write-Host ""
    
    # Step 1: Validate dependencies
    $dependenciesOk = Test-SetupDependencies
    if (-not $dependenciesOk) {
        return @{ Success = $false; Message = "Dependencies validation failed" }
    }
    
    # Step 2: Validate project structure
    $structureOk = Test-ProjectStructure
    if (-not $structureOk) {
        return @{ Success = $false; Message = "Project structure validation failed" }
    }
    
    # Step 3: Execute setup phases
    $phaseResults = @()
    $stepCounter = 3
    
    # Phase 1: Environment Check (unless skipped)
    if (-not $SkipEnvironmentCheck) {
        $envResult = Invoke-EnvironmentCheckPhase -AutoFix:$Force
        $phaseResults += $envResult
        
        if (-not $envResult.Success -and -not $Force) {
            Write-SafeOutput "Environment validation failed - stopping setup process" -Status Error
            return @{
                Success = $false
                Results = $phaseResults
                Message = "Environment validation failed"
            }
        }
    }
    else {
        Write-SafeOutput "Skipping environment check (requested)" -Status Skip
        $phaseResults += @{ Success = $true; Phase = "EnvironmentCheck"; Skipped = $true }
    }
    
    # Phase 2: Database Migrations
    $migrationsResult = Invoke-DatabasePhase -PhaseName "DatabaseMigrations" -PhaseConfig $Script:SETUP_PHASES["DatabaseMigrations"]
    $phaseResults += $migrationsResult
    
    if (-not $migrationsResult.Success -and -not $Force) {
        Write-SafeOutput "Database migrations failed - stopping setup process" -Status Error
        return @{
            Success = $false
            Results = $phaseResults
            Message = "Database migrations failed"
        }
    }
    
    # Phase 3: User Seeding
    $seedingResult = Invoke-DatabasePhase -PhaseName "UserSeeding" -PhaseConfig $Script:SETUP_PHASES["UserSeeding"]
    $phaseResults += $seedingResult
    
    if (-not $seedingResult.Success -and -not $Force) {
        Write-SafeOutput "User seeding failed - stopping setup process" -Status Error
        return @{
            Success = $false
            Results = $phaseResults
            Message = "User seeding failed"
        }
    }
    
    # Phase 4: Health Check
    $healthResult = Invoke-DatabasePhase -PhaseName "HealthCheck" -PhaseConfig $Script:SETUP_PHASES["HealthCheck"]
    $phaseResults += $healthResult
    
    # Health check failure is not critical if not forced
    if (-not $healthResult.Success) {
        Write-SafeOutput "Health check failed - continuing (not critical)" -Status Warning
    }
    
    return @{
        Success = ($phaseResults | Where-Object { $_.Phase -ne "HealthCheck" -and -not $_.Success -and -not $_.Skipped }).Count -eq 0
        Results = $phaseResults
        TotalPhases = $phaseResults.Count
        SuccessfulPhases = ($phaseResults | Where-Object { $_.Success -and -not $_.Skipped }).Count
        SkippedPhases = ($phaseResults | Where-Object { $_.Skipped }).Count
    }
}

function Show-SetupSummary {
    <#
    .SYNOPSIS
    Displays comprehensive setup results summary
    #>
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$SetupResult
    )
    
    Write-Host ""
    Write-SafeHeader "Database Setup Summary"
    
    # Show individual phase results
    foreach ($result in $SetupResult.Results) {
        if ($result.Skipped) {
            Write-SafeOutput "$($result.Phase): SKIPPED" -Status Skip
        }
        elseif ($result.Success) {
            $durationText = if ($result.Duration) { " ($([math]::Round($result.Duration, 1))s)" } else { "" }
            Write-SafeOutput "$($result.Phase): SUCCESS$durationText" -Status Success
        }
        else {
            Write-SafeOutput "$($result.Phase): FAILED - $($result.Message)" -Status Error
        }
    }
    
    # Show overall statistics
    Write-Host ""
    Write-SafeOutput "Total phases: $($SetupResult.TotalPhases)" -Status Info
    Write-SafeOutput "Successful phases: $($SetupResult.SuccessfulPhases)" -Status Success
    Write-SafeOutput "Skipped phases: $($SetupResult.SkippedPhases)" -Status Skip
    Write-SafeOutput "Failed phases: $(($SetupResult.Results | Where-Object { -not $_.Success -and -not $_.Skipped }).Count)" -Status Error
    
    # Final status and next steps
    Write-Host ""
    if ($SetupResult.Success) {
        Write-SafeOutput "Database initialization completed successfully!" -Status Complete
        Write-Host ""
        Write-SafeOutput "Next Steps:" -Status Info
        Write-SafeOutput "  Start development server: npm run dev" -Status Info
        Write-SafeOutput "  Or start production: npm run start:windows" -Status Info
        Write-SafeOutput "  Check database: npm run health:mysql (from packages/db)" -Status Info
        Write-SafeOutput "  Admin login: admin@yuyulolita.com / (see credentials.txt)" -Status Info
    }
    else {
        Write-SafeOutput "Database initialization failed!" -Status Error
        Write-Host ""
        Write-SafeOutput "Troubleshooting:" -Status Info
        Write-SafeOutput "  1. Check MySQL service: services.msc" -Status Info
        Write-SafeOutput "  2. Verify .env file configuration" -Status Info
        Write-SafeOutput "  3. Review error messages above for specific issues" -Status Info
        Write-SafeOutput "  4. Try force mode: powershell -File $PSCommandPath -Force" -Status Info
    }
}

# ==============================================================================
# SCRIPT ENTRY POINT
# ==============================================================================

try {
    # Execute database initialization
    $setupResult = Invoke-DatabaseInitialization
    
    # Display results
    Show-SetupSummary -SetupResult $setupResult
    
    # Exit with appropriate code
    exit $(if ($setupResult.Success) { 0 } else { 1 })
}
catch {
    Write-SafeOutput "Critical error during database setup: $($_.Exception.Message)" -Status Error
    Write-SafeOutput "Please check the PowerShell execution environment" -Status Info
    exit 1
}