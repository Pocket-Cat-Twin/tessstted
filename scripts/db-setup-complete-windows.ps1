# ================================
# Complete Database Setup for Windows
# YuYu Lolita Shopping System
# ================================

[CmdletBinding()]
param(
    [switch]$Force = $false,
    [switch]$SkipEnvironmentCheck = $false,
    [switch]$Verbose = $false
)

# Import common functions
. "$PSScriptRoot\PowerShell-Common.ps1"

function Show-Header {
    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Magenta
    Write-Host "FULL DATABASE INITIALIZATION (WINDOWS)" -ForegroundColor Magenta
    Write-Host "YuYu Lolita Shopping System" -ForegroundColor Magenta  
    Write-Host "MySQL8 + Auto User Creation" -ForegroundColor Magenta
    Write-Host "==============================================" -ForegroundColor Magenta
    Write-Host ""
}

function Invoke-EnvironmentCheck {
    Write-Host "[PHASE 1] Windows Environment Check..." -ForegroundColor Cyan
    Write-Host ""
    
    $checkScript = Join-Path $PSScriptRoot "db-environment-check-windows.ps1"
    
    if (-not (Test-Path $checkScript)) {
        Write-Host "ERROR: Environment check script not found!" -ForegroundColor Red
        return $false
    }
    
    try {
        $result = & powershell -ExecutionPolicy Bypass -File $checkScript -Fix
        if ($LASTEXITCODE -eq 0) {
            Write-Host "SUCCESS: Environment check completed!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "ERROR: Environment check failed!" -ForegroundColor Red
            Write-Host "SOLUTION: Fix issues and run again" -ForegroundColor Yellow
            return $false
        }
    } catch {
        Write-Host "ERROR: Environment check exception: $_" -ForegroundColor Red
        return $false
    }
}

function Invoke-DatabaseMigrations {
    Write-Host ""
    Write-Host "[PHASE 2] Running database migrations..." -ForegroundColor Cyan
    Write-Host ""
    
    $projectRoot = Split-Path $PSScriptRoot -Parent
    $dbPackagePath = Join-Path $projectRoot "packages\db"
    
    if (-not (Test-Path $dbPackagePath)) {
        Write-Host "ERROR: DB package not found at: $dbPackagePath" -ForegroundColor Red
        return $false
    }
    
    try {
        Push-Location $dbPackagePath
        
        Write-Host "INFO: Moving to directory: $dbPackagePath" -ForegroundColor Blue
        Write-Host "INFO: Running migrations via bun..." -ForegroundColor Blue
        
        # Check bun availability
        $bunPath = Get-Command bun -ErrorAction SilentlyContinue
        if (-not $bunPath) {
            Write-Host "ERROR: Bun not found in system!" -ForegroundColor Red
            Write-Host "SOLUTION: Install Bun from https://bun.sh/docs/installation" -ForegroundColor Yellow
            return $false
        }
        
        # Run migrations
        Write-Host "EXECUTE: bun run migrate:windows" -ForegroundColor Green
        & bun run migrate:windows
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "SUCCESS: Migrations completed!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "ERROR: Migration execution failed!" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "ERROR: Migration exception: $_" -ForegroundColor Red
        return $false
    } finally {
        Pop-Location
    }
}

function Invoke-UserSeed {
    Write-Host ""
    Write-Host "[PHASE 3] Creating initial users..." -ForegroundColor Cyan
    Write-Host ""
    
    $projectRoot = Split-Path $PSScriptRoot -Parent
    $dbPackagePath = Join-Path $projectRoot "packages\db"
    
    try {
        Push-Location $dbPackagePath
        
        Write-Host "INFO: Creating admin and test users..." -ForegroundColor Blue
        
        # Check seed script exists
        $seedScript = Join-Path $dbPackagePath "src\seed-users.ts"
        if (!(Test-Path $seedScript)) {
            Write-Host "ERROR: User seed script not found" -ForegroundColor Red
            Write-Host "SOLUTION: Check path: $seedScript" -ForegroundColor Yellow
            return $false
        }
        
        Write-Host "EXECUTE: bun run src/seed-users.ts" -ForegroundColor Green
        $bunResult = & bun run src/seed-users.ts
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "SUCCESS: Users created successfully!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "ERROR: User creation failed!" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "ERROR: User creation exception: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    } finally {
        Pop-Location
    }
}

function Invoke-FinalHealthCheck {
    Write-Host ""
    Write-Host "[PHASE 4] Final health check..." -ForegroundColor Cyan
    Write-Host ""
    
    $projectRoot = Split-Path $PSScriptRoot -Parent
    $dbPackagePath = Join-Path $projectRoot "packages\db"
    
    try {
        Push-Location $dbPackagePath
        
        Write-Host "INFO: Running health check..." -ForegroundColor Blue
        
        Write-Host "EXECUTE: bun run health:mysql" -ForegroundColor Green
        & bun run health:mysql
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "SUCCESS: Health check passed!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "ERROR: Health check failed!" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "ERROR: Health check exception: $_" -ForegroundColor Red
        return $false
    } finally {
        Pop-Location
    }
}

# ================================
# MAIN EXECUTION
# ================================

Show-Header

$phases = @()

# Phase 1: Environment Check
if (-not $SkipEnvironmentCheck) {
    $phases += @{ Name = "Environment Check"; Result = (Invoke-EnvironmentCheck) }
} else {
    Write-Host "SKIP: Environment check skipped by request" -ForegroundColor Yellow
    $phases += @{ Name = "Environment Check"; Result = $true }
}

# Phase 2: Database Migrations
if ($phases[-1].Result -or $Force) {
    $phases += @{ Name = "DB Migrations"; Result = (Invoke-DatabaseMigrations) }
} else {
    Write-Host "SKIP: Migrations skipped due to previous errors" -ForegroundColor Yellow
    $phases += @{ Name = "DB Migrations"; Result = $false }
}

# Phase 3: User Seed
if ($phases[-1].Result -or $Force) {
    $phases += @{ Name = "User Creation"; Result = (Invoke-UserSeed) }
} else {
    Write-Host "SKIP: User creation skipped due to errors" -ForegroundColor Yellow
    $phases += @{ Name = "User Creation"; Result = $false }
}

# Phase 4: Final Health Check
if ($phases[-1].Result -or $Force) {
    $phases += @{ Name = "Final Check"; Result = (Invoke-FinalHealthCheck) }
} else {
    Write-Host "SKIP: Final check skipped" -ForegroundColor Yellow
    $phases += @{ Name = "Final Check"; Result = $false }
}

# Summary
Write-Host ""
Write-Host "=============================================" -ForegroundColor Magenta
Write-Host "FULL DB INITIALIZATION RESULTS" -ForegroundColor Magenta
Write-Host "=============================================" -ForegroundColor Magenta

$successfulPhases = 0
foreach ($phase in $phases) {
    $status = if ($phase.Result) { "SUCCESS" } else { "ERROR" }
    $color = if ($phase.Result) { "Green" } else { "Red" }
    Write-Host "$status - $($phase.Name)" -ForegroundColor $color
    if ($phase.Result) { 
        $successfulPhases++ 
    }
}

Write-Host ""
Write-Host "Successfully completed: $successfulPhases of $($phases.Count) phases" -ForegroundColor Cyan

if ($successfulPhases -eq $phases.Count) {
    Write-Host ""
    Write-Host "SUCCESS: Full initialization completed successfully!" -ForegroundColor Green
    Write-Host "NEXT: Database is ready to use!" -ForegroundColor Green
    Write-Host "INFO: Run 'npm run dev' to start the application" -ForegroundColor Yellow
    Write-Host ""
    exit 0
} else {
    Write-Host ""
    Write-Host "ERROR: Initialization completed with errors!" -ForegroundColor Red
    Write-Host "TIP: Check logs and fix problems" -ForegroundColor Yellow
    if (-not $Force) {
        Write-Host "TIP: Use -Force to force execute all phases" -ForegroundColor Yellow
    }
    Write-Host ""
    exit 1
}