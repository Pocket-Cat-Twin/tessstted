# Lolita Fashion Shopping - Build Script for Windows
# Builds both API and Web app for production

param(
    [switch]$Clean = $false,
    [switch]$SkipAPI = $false,
    [switch]$SkipWeb = $false
)

Write-Host "[BUILD] Starting Lolita Fashion Shopping - Production Build" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green

# Get the project root directory
$projectRoot = Split-Path -Parent $PSScriptRoot

# Function to build API
function Build-API {
    Write-Host ""
    Write-Host "[API] Building API server..." -ForegroundColor Cyan
    
    try {
        Set-Location "$projectRoot\apps\api"
        
        # Clean if requested
        if ($Clean) {
            Write-Host "[API] Cleaning previous build..." -ForegroundColor Yellow
            if (Test-Path "dist") {
                Remove-Item -Recurse -Force "dist"
            }
        }
        
        # Run the build
        Write-Host "[API] Running Bun build..." -ForegroundColor Yellow
        $result = & bun build src/index.ts --outdir=dist --target=bun 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[SUCCESS] API build completed" -ForegroundColor Green
            
            # Verify the build output
            if (Test-Path "dist/index.js") {
                $fileSize = (Get-Item "dist/index.js").Length
                Write-Host "[INFO] Built file: dist/index.js ($([math]::Round($fileSize/1KB, 2)) KB)" -ForegroundColor White
            }
            return $true
        } else {
            Write-Host "[ERROR] API build failed:" -ForegroundColor Red
            Write-Host $result -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "[ERROR] API build failed with exception: $_" -ForegroundColor Red
        return $false
    }
    finally {
        Set-Location $projectRoot
    }
}

# Function to build Web app
function Build-Web {
    Write-Host ""
    Write-Host "[WEB] Building Web app..." -ForegroundColor Cyan
    
    try {
        Set-Location "$projectRoot\apps\web"
        
        # Clean if requested
        if ($Clean) {
            Write-Host "[WEB] Cleaning previous build..." -ForegroundColor Yellow
            if (Test-Path "build") {
                Remove-Item -Recurse -Force "build"
            }
            if (Test-Path ".svelte-kit") {
                Remove-Item -Recurse -Force ".svelte-kit"
            }
        }
        
        # Run the build
        Write-Host "[WEB] Running Vite build..." -ForegroundColor Yellow
        $result = & bunx vite build 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[SUCCESS] Web app build completed" -ForegroundColor Green
            
            # Verify the build output
            if (Test-Path "build") {
                $buildSize = (Get-ChildItem -Recurse "build" | Measure-Object -Property Length -Sum).Sum
                Write-Host "[INFO] Build directory: build ($([math]::Round($buildSize/1MB, 2)) MB)" -ForegroundColor White
            }
            return $true
        } else {
            Write-Host "[ERROR] Web app build failed:" -ForegroundColor Red
            Write-Host $result -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "[ERROR] Web app build failed with exception: $_" -ForegroundColor Red
        return $false
    }
    finally {
        Set-Location $projectRoot
    }
}

# Main build process
Set-Location $projectRoot

# Build tracking
$apiSuccess = $true
$webSuccess = $true

# Build API
if (-not $SkipAPI) {
    $apiSuccess = Build-API
} else {
    Write-Host "[SKIP] Skipping API build" -ForegroundColor Yellow
}

# Build Web app
if (-not $SkipWeb) {
    $webSuccess = Build-Web
} else {
    Write-Host "[SKIP] Skipping Web app build" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "[SUMMARY] Build Results:" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan

if ($apiSuccess) {
    Write-Host "[OK] API: SUCCESS" -ForegroundColor Green
} else {
    Write-Host "[FAIL] API: FAILED" -ForegroundColor Red
}

if ($webSuccess) {
    Write-Host "[OK] Web: SUCCESS" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Web: FAILED" -ForegroundColor Red
}

if ($apiSuccess -and $webSuccess) {
    Write-Host ""
    Write-Host "[COMPLETE] All builds successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "[NEXT STEPS]" -ForegroundColor Cyan
    Write-Host "  API server: cd apps/api && bun start" -ForegroundColor White
    Write-Host "  Web app: cd apps/web && node build" -ForegroundColor White
    Write-Host "  Or use: bun run start:windows" -ForegroundColor White
    exit 0
} else {
    Write-Host ""
    Write-Host "[FAILED] One or more builds failed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "[TROUBLESHOOTING]" -ForegroundColor Yellow
    Write-Host "  - Check that all dependencies are installed: bun install" -ForegroundColor White
    Write-Host "  - Verify TypeScript compilation: bun run type-check" -ForegroundColor White
    Write-Host "  - Check for syntax errors in the source code" -ForegroundColor White
    exit 1
}