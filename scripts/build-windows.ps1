# ================================
# Production Build Script for Windows
# YuYu Lolita Shopping System
# Enterprise-grade build orchestration
# ================================

[CmdletBinding()]
param(
    [switch]$Clean = $false,
    [switch]$SkipAPI = $false,
    [switch]$SkipWeb = $false,
    [switch]$SkipShared = $false,
    [int]$TimeoutMinutes = 10
)

# Import common functions with validation
$commonLibPath = Join-Path $PSScriptRoot "PowerShell-Common.ps1"
if (-not (Test-Path $commonLibPath)) {
    Write-Error "Required PowerShell-Common.ps1 not found at: $commonLibPath"
    exit 1
}
. $commonLibPath

# Build configuration
$Script:BUILD_TIMEOUT_SECONDS = $TimeoutMinutes * 60
$Script:REQUIRED_COMMANDS = @{
    "bun" = "Bun runtime (https://bun.sh/docs/installation)"
    "node" = "Node.js runtime (https://nodejs.org/)"
}

# Project structure configuration
$Script:PROJECT_COMPONENTS = @{
    "Shared" = @{
        Path = "packages\shared"
        BuildCommand = "npm"
        BuildArgs = @("run", "build")
        OutputPath = "dist"
        CleanPaths = @("dist", "node_modules\.cache")
        Description = "Shared utilities package"
    }
    "API" = @{
        Path = "apps\api"
        BuildCommand = "bun"
        BuildArgs = @("build", "src\index.ts", "--outdir=dist", "--target=bun")
        OutputPath = "dist"
        CleanPaths = @("dist")
        Description = "API server"
        DependsOn = @("Shared")
    }
    "Web" = @{
        Path = "apps\web"
        BuildCommand = "bun"
        BuildArgs = @("run", "build")
        OutputPath = "build"
        CleanPaths = @("build", ".svelte-kit", "node_modules\.vite")
        Description = "Web application"
        DependsOn = @("Shared")
    }
}

# ==============================================================================
# DEPENDENCY VALIDATION
# ==============================================================================

function Test-BuildDependencies {
    <#
    .SYNOPSIS
    Validates all required build dependencies are available
    #>
    
    Write-SafeSectionHeader "Build Dependencies Check" -Step 1
    
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
        Write-SafeOutput "Build dependencies check failed" -Status Error
        return $false
    }
    
    Write-SafeOutput "All build dependencies available" -Status Success
    return $true
}

function Test-ProjectStructure {
    <#
    .SYNOPSIS
    Validates project structure and component paths
    #>
    
    Write-SafeSectionHeader "Project Structure Validation" -Step 2
    
    $projectRoot = Get-ProjectRoot
    $allPathsValid = $true
    
    foreach ($componentName in $Script:PROJECT_COMPONENTS.Keys) {
        $component = $Script:PROJECT_COMPONENTS[$componentName]
        $componentPath = Join-Path $projectRoot $component.Path
        
        $pathTest = Test-PathSafely -Path $componentPath -Type Directory
        
        if ($pathTest.Exists -and $pathTest.MatchesType) {
            Write-SafeOutput "Found component: $componentName ($($component.Description))" -Status Success
        }
        else {
            Write-SafeOutput "Missing component directory: $componentName at $componentPath" -Status Error
            $allPathsValid = $false
        }
    }
    
    if (-not $allPathsValid) {
        Write-SafeOutput "Project structure validation failed" -Status Error
        return $false
    }
    
    Write-SafeOutput "Project structure validation passed" -Status Success
    return $true
}

# ==============================================================================
# BUILD OPERATIONS
# ==============================================================================

function Invoke-ComponentClean {
    <#
    .SYNOPSIS
    Cleans build artifacts for a specific component
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$ComponentName,
        
        [Parameter(Mandatory = $true)]
        [hashtable]$ComponentConfig,
        
        [Parameter(Mandatory = $true)]
        [string]$ComponentPath
    )
    
    if (-not $Clean) {
        return $true
    }
    
    Write-SafeOutput "Cleaning $ComponentName build artifacts..." -Status Processing
    
    try {
        foreach ($cleanPath in $ComponentConfig.CleanPaths) {
            $fullCleanPath = Join-Path $ComponentPath $cleanPath
            
            if (Test-Path $fullCleanPath) {
                Remove-Item -Path $fullCleanPath -Recurse -Force -ErrorAction Stop
                Write-SafeOutput "Removed: $cleanPath" -Status Info
            }
        }
        
        Write-SafeOutput "$ComponentName cleanup completed" -Status Success
        return $true
    }
    catch {
        Write-SafeOutput "Cleanup failed for ${ComponentName}: $($_.Exception.Message)" -Status Error
        return $false
    }
}

function Invoke-ComponentBuild {
    <#
    .SYNOPSIS
    Builds a specific project component with full error handling
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$ComponentName,
        
        [Parameter(Mandatory = $true)]
        [hashtable]$ComponentConfig
    )
    
    $projectRoot = Get-ProjectRoot
    $componentPath = Join-Path $projectRoot $ComponentConfig.Path
    
    Write-SafeSectionHeader "$ComponentName Build" -Step 0
    Write-SafeOutput "Building $($ComponentConfig.Description)..." -Status Processing
    
    # Validate component directory exists
    if (-not (Test-Path $componentPath)) {
        Write-SafeOutput "Component directory not found: $componentPath" -Status Error
        return @{ Success = $false; Component = $ComponentName; Message = "Directory not found" }
    }
    
    # Clean if requested
    $cleanResult = Invoke-ComponentClean -ComponentName $ComponentName -ComponentConfig $ComponentConfig -ComponentPath $componentPath
    if (-not $cleanResult) {
        return @{ Success = $false; Component = $ComponentName; Message = "Clean failed" }
    }
    
    # Execute build command
    $buildResult = Invoke-SafeCommand -Command $ComponentConfig.BuildCommand -Arguments $ComponentConfig.BuildArgs -WorkingDirectory $componentPath -Description "Building $ComponentName" -TimeoutSeconds $Script:BUILD_TIMEOUT_SECONDS
    
    if ($buildResult.Success) {
        # Verify build output
        $outputPath = Join-Path $componentPath $ComponentConfig.OutputPath
        $outputValidation = Test-PathSafely -Path $outputPath -Type Directory
        
        if ($outputValidation.Exists) {
            # Calculate build size for informational purposes
            try {
                $buildSize = (Get-ChildItem -Path $outputPath -Recurse -File | Measure-Object -Property Length -Sum).Sum
                $buildSizeMB = [math]::Round($buildSize / 1MB, 2)
                Write-SafeOutput "$ComponentName build completed ($buildSizeMB MB)" -Status Success
            }
            catch {
                Write-SafeOutput "$ComponentName build completed" -Status Success
            }
            
            return @{ 
                Success = $true
                Component = $ComponentName
                Duration = $buildResult.Duration
                OutputPath = $outputPath
                Message = "Build successful"
            }
        }
        else {
            Write-SafeOutput "Build output directory not found: $outputPath" -Status Error
            return @{ Success = $false; Component = $ComponentName; Message = "Output validation failed" }
        }
    }
    else {
        Write-SafeOutput "$ComponentName build failed (exit code: $($buildResult.ExitCode))" -Status Error
        Write-SafeOutput "Build error: $($buildResult.Output)" -Status Error
        return @{ 
            Success = $false
            Component = $ComponentName
            ExitCode = $buildResult.ExitCode
            Message = "Build command failed"
            Output = $buildResult.Output
        }
    }
}

# ==============================================================================
# DEPENDENCY RESOLUTION
# ==============================================================================

function Get-BuildOrder {
    <#
    .SYNOPSIS
    Determines correct build order based on component dependencies
    #>
    
    $buildOrder = @()
    $processed = @()
    
    function Add-ComponentWithDependencies {
        param([string]$ComponentName)
        
        if ($ComponentName -in $processed) {
            return
        }
        
        $component = $Script:PROJECT_COMPONENTS[$ComponentName]
        
        # Add dependencies first
        if ($component.ContainsKey("DependsOn")) {
            foreach ($dependency in $component.DependsOn) {
                Add-ComponentWithDependencies -ComponentName $dependency
            }
        }
        
        # Add current component
        $buildOrder += $ComponentName
        $processed += $ComponentName
    }
    
    # Process all components
    foreach ($componentName in $Script:PROJECT_COMPONENTS.Keys) {
        Add-ComponentWithDependencies -ComponentName $componentName
    }
    
    return $buildOrder
}

# ==============================================================================
# BUILD ORCHESTRATION
# ==============================================================================

function Invoke-ProductionBuild {
    <#
    .SYNOPSIS
    Main build orchestration function
    #>
    
    Write-SafeHeader "Production Build for Windows"
    Write-SafeOutput "YuYu Lolita Shopping System - Enterprise Build Process" -Status Info
    Write-Host ""
    
    # Step 1: Validate dependencies
    $dependenciesOk = Test-BuildDependencies
    if (-not $dependenciesOk) {
        return @{ Success = $false; Message = "Dependencies validation failed" }
    }
    
    # Step 2: Validate project structure
    $structureOk = Test-ProjectStructure
    if (-not $structureOk) {
        return @{ Success = $false; Message = "Project structure validation failed" }
    }
    
    # Step 3: Determine build order
    $buildOrder = Get-BuildOrder
    Write-SafeSectionHeader "Build Order" -Step 3
    foreach ($component in $buildOrder) {
        Write-SafeOutput "$component ($($Script:PROJECT_COMPONENTS[$component].Description))" -Status Info
    }
    Write-Host ""
    
    # Step 4: Execute builds in correct order
    $buildResults = @()
    $stepCounter = 4
    
    foreach ($componentName in $buildOrder) {
        # Check if component should be skipped
        $skipComponent = switch ($componentName) {
            "Shared" { $SkipShared }
            "API" { $SkipAPI }
            "Web" { $SkipWeb }
            default { $false }
        }
        
        if ($skipComponent) {
            Write-SafeOutput "Skipping $componentName build (requested)" -Status Skip
            $buildResults += @{ Success = $true; Component = $componentName; Skipped = $true }
            continue
        }
        
        $componentConfig = $Script:PROJECT_COMPONENTS[$componentName]
        $buildResult = Invoke-ComponentBuild -ComponentName $componentName -ComponentConfig $componentConfig
        $buildResults += $buildResult
        
        # Stop on first failure unless forcing
        if (-not $buildResult.Success) {
            Write-SafeOutput "Build failed for $componentName - stopping build process" -Status Error
            break
        }
        
        $stepCounter++
    }
    
    return @{
        Success = ($buildResults | Where-Object { -not $_.Success -and -not $_.Skipped }).Count -eq 0
        Results = $buildResults
        TotalComponents = $buildResults.Count
        SuccessfulBuilds = ($buildResults | Where-Object { $_.Success -and -not $_.Skipped }).Count
        SkippedBuilds = ($buildResults | Where-Object { $_.Skipped }).Count
    }
}

function Show-BuildSummary {
    <#
    .SYNOPSIS
    Displays comprehensive build results summary
    #>
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$BuildResult
    )
    
    Write-Host ""
    Write-SafeHeader "Build Summary"
    
    # Show individual component results
    foreach ($result in $BuildResult.Results) {
        if ($result.Skipped) {
            Write-SafeOutput "$($result.Component): SKIPPED" -Status Skip
        }
        elseif ($result.Success) {
            $durationText = if ($result.Duration) { " ($([math]::Round($result.Duration, 1))s)" } else { "" }
            Write-SafeOutput "$($result.Component): SUCCESS$durationText" -Status Success
        }
        else {
            Write-SafeOutput "$($result.Component): FAILED - $($result.Message)" -Status Error
        }
    }
    
    # Show overall statistics
    Write-Host ""
    Write-SafeOutput "Total components: $($BuildResult.TotalComponents)" -Status Info
    Write-SafeOutput "Successful builds: $($BuildResult.SuccessfulBuilds)" -Status Success
    Write-SafeOutput "Skipped builds: $($BuildResult.SkippedBuilds)" -Status Skip
    Write-SafeOutput "Failed builds: $(($BuildResult.Results | Where-Object { -not $_.Success -and -not $_.Skipped }).Count)" -Status Error
    
    # Final status and next steps
    Write-Host ""
    if ($BuildResult.Success) {
        Write-SafeOutput "Production build completed successfully!" -Status Complete
        Write-Host ""
        Write-SafeOutput "Next Steps:" -Status Info
        Write-SafeOutput "  Start API server: cd apps/api && bun run start" -Status Info
        Write-SafeOutput "  Deploy web app: Use contents of apps/web/build" -Status Info
        Write-SafeOutput "  Or start production: npm run start:windows" -Status Info
    }
    else {
        Write-SafeOutput "Production build failed!" -Status Error
        Write-Host ""
        Write-SafeOutput "Troubleshooting:" -Status Info
        Write-SafeOutput "  1. Check that all dependencies are installed: npm install" -Status Info
        Write-SafeOutput "  2. Verify TypeScript compilation: npm run type-check" -Status Info
        Write-SafeOutput "  3. Review error messages above for specific issues" -Status Info
        Write-SafeOutput "  4. Try cleaning build: npm run build -- -Clean" -Status Info
    }
}

# ==============================================================================
# SCRIPT ENTRY POINT
# ==============================================================================

try {
    # Execute production build
    $buildResult = Invoke-ProductionBuild
    
    # Display results
    Show-BuildSummary -BuildResult $buildResult
    
    # Exit with appropriate code
    exit $(if ($buildResult.Success) { 0 } else { 1 })
}
catch {
    Write-SafeOutput "Critical error during build process: $($_.Exception.Message)" -Status Error
    Write-SafeOutput "Please check the build environment and try again" -Status Info
    exit 1
}