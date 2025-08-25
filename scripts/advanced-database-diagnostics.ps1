# Advanced Database Diagnostics - Enterprise Integration Module
# Integrates PowerShell diagnostics with TypeScript/Node.js enterprise systems
# Version: 3.0 - Production Ready with TypeScript Integration
# Author: Senior Database Reliability Engineer
# Last Modified: 2025-08-25

#Requires -Version 5.0

# ==============================================================================
# ENTERPRISE DIAGNOSTIC FUNCTIONS
# ==============================================================================

function Invoke-EnterpriseDatabaseDiagnostics {
    <#
    .SYNOPSIS
    Runs comprehensive enterprise-grade database diagnostics using TypeScript modules
    #>
    
    param(
        [switch]$Detailed = $false,
        [switch]$AutoFix = $false,
        [switch]$GenerateReport = $false
    )
    
    Write-SafeHeader "ENTERPRISE DATABASE DIAGNOSTICS v3.0" "="
    Write-SafeOutput "Integrating PowerShell and TypeScript diagnostic systems..." -Status Processing
    
    $diagnostics = @{
        PowerShellResults = @{}
        TypeScriptResults = @{}
        IntegrationStatus = @{}
        OverallHealth = $false
        AutoFixAttempts = @()
        Recommendations = @()
    }
    
    try {
        # Step 1: Run TypeScript Environment Diagnostics
        Write-SafeSectionHeader "TypeScript Environment Diagnostics" 1
        $envDiagnostics = Invoke-SafeCommand -Command "bun" -Arguments @("run", "--silent", "-e", "
            import { runEnvironmentDiagnostics, displayEnvironmentReport } from './packages/db/src/environment-diagnostics.ts';
            const result = await runEnvironmentDiagnostics();
            console.log(JSON.stringify({
                success: result.success,
                issueCount: result.issues.length,
                criticalIssues: result.issues.filter(i => i.type === 'critical').length,
                autoFixAvailable: result.autoFixAvailable,
                databaseConfigValid: result.databaseConfig.validated
            }, null, 2));
        ") -Description "Running TypeScript environment diagnostics" -IgnoreErrors
        
        if ($envDiagnostics.Success) {
            try {
                $envResults = $envDiagnostics.Output | ConvertFrom-Json -ErrorAction Stop
                $diagnostics.TypeScriptResults.Environment = $envResults
                Write-SafeOutput "Environment diagnostics: $($envResults.issueCount) issues found" -Status $(if ($envResults.success) { "Success" } else { "Warning" })
                if ($envResults.criticalIssues -gt 0) {
                    Write-SafeOutput "Critical issues detected: $($envResults.criticalIssues)" -Status Error
                }
            }
            catch {
                Write-SafeOutput "Failed to parse TypeScript environment diagnostics" -Status Warning
                $diagnostics.TypeScriptResults.Environment = $null
            }
        } else {
            Write-SafeOutput "TypeScript environment diagnostics failed" -Status Error
            $diagnostics.TypeScriptResults.Environment = $null
        }
        
        # Step 2: Run TypeScript Configuration Manager
        Write-SafeSectionHeader "Configuration Management Analysis" 2
        $configAnalysis = Invoke-SafeCommand -Command "bun" -Arguments @("run", "--silent", "-e", "
            import { loadConfiguration, validateConfiguration } from './packages/db/src/config-manager.ts';
            try {
                const config = await loadConfiguration();
                const validation = validateConfiguration();
                console.log(JSON.stringify({
                    configLoaded: config.runtime.loaded,
                    sourcesCount: config.runtime.sources.length,
                    errorsCount: config.runtime.errors.length,
                    validationPassed: validation.valid,
                    validationErrors: validation.errors.length,
                    validationWarnings: validation.warnings.length,
                    databaseConfigured: config.database.validated
                }, null, 2));
            } catch (error) {
                console.log(JSON.stringify({ error: error.message }, null, 2));
            }
        ") -Description "Running configuration analysis" -IgnoreErrors
        
        if ($configAnalysis.Success) {
            try {
                $configResults = $configAnalysis.Output | ConvertFrom-Json -ErrorAction Stop
                $diagnostics.TypeScriptResults.Configuration = $configResults
                
                if ($configResults.configLoaded) {
                    Write-SafeOutput "Configuration loaded from $($configResults.sourcesCount) sources" -Status Success
                } else {
                    Write-SafeOutput "Configuration loading failed" -Status Error
                }
                
                if ($configResults.validationPassed) {
                    Write-SafeOutput "Configuration validation: PASSED" -Status Success
                } else {
                    Write-SafeOutput "Configuration validation: FAILED ($($configResults.validationErrors) errors)" -Status Error
                }
            }
            catch {
                Write-SafeOutput "Failed to parse configuration analysis" -Status Warning
                $diagnostics.TypeScriptResults.Configuration = $null
            }
        } else {
            Write-SafeOutput "Configuration analysis failed" -Status Error
            $diagnostics.TypeScriptResults.Configuration = $null
        }
        
        # Step 3: Database Connection Analysis with Error Handling
        Write-SafeSectionHeader "Database Connection Analysis" 3
        $dbConnectionTest = Invoke-SafeCommand -Command "bun" -Arguments @("run", "--silent", "-e", "
            import { handleDatabaseError } from './packages/db/src/database-error-handler.ts';
            import { db, users } from './packages/db/src/index.ts';
            
            try {
                await db.select().from(users).limit(0);
                console.log(JSON.stringify({
                    connectionWorking: true,
                    error: null,
                    errorCategory: null,
                    autoRecoverable: false
                }, null, 2));
            } catch (error) {
                try {
                    const dbError = await handleDatabaseError(error, 'diagnostic-test');
                    console.log(JSON.stringify({
                        connectionWorking: false,
                        error: error.message,
                        errorCategory: dbError.category,
                        errorSeverity: dbError.severity,
                        autoRecoverable: dbError.recovery.autoRecoverable,
                        solutionsCount: dbError.solutions.length
                    }, null, 2));
                } catch (handlerError) {
                    console.log(JSON.stringify({
                        connectionWorking: false,
                        error: error.message,
                        handlerError: handlerError.message
                    }, null, 2));
                }
            }
        ") -Description "Testing database connection with error analysis" -IgnoreErrors
        
        if ($dbConnectionTest.Success) {
            try {
                $dbResults = $dbConnectionTest.Output | ConvertFrom-Json -ErrorAction Stop
                $diagnostics.TypeScriptResults.DatabaseConnection = $dbResults
                
                if ($dbResults.connectionWorking) {
                    Write-SafeOutput "Database connection: SUCCESS" -Status Success
                } else {
                    Write-SafeOutput "Database connection: FAILED ($($dbResults.errorCategory))" -Status Error
                    if ($dbResults.autoRecoverable) {
                        Write-SafeOutput "Auto-recovery available with $($dbResults.solutionsCount) solutions" -Status Info
                    }
                }
            }
            catch {
                Write-SafeOutput "Failed to parse database connection results" -Status Warning
                $diagnostics.TypeScriptResults.DatabaseConnection = $null
            }
        } else {
            Write-SafeOutput "Database connection test failed" -Status Error
            $diagnostics.TypeScriptResults.DatabaseConnection = $null
        }
        
        # Step 4: Overall Health Assessment
        Write-SafeSectionHeader "Overall Health Assessment" 4
        $healthScore = 0
        $maxScore = 0
        
        # Environment health (25 points)
        $maxScore += 25
        if ($diagnostics.TypeScriptResults.Environment) {
            if ($diagnostics.TypeScriptResults.Environment.success) {
                $healthScore += 25
            } elseif ($diagnostics.TypeScriptResults.Environment.criticalIssues -eq 0) {
                $healthScore += 15
            } else {
                $healthScore += 5
            }
        }
        
        # Configuration health (25 points)
        $maxScore += 25
        if ($diagnostics.TypeScriptResults.Configuration) {
            if ($diagnostics.TypeScriptResults.Configuration.configLoaded -and $diagnostics.TypeScriptResults.Configuration.validationPassed) {
                $healthScore += 25
            } elseif ($diagnostics.TypeScriptResults.Configuration.configLoaded) {
                $healthScore += 15
            } else {
                $healthScore += 5
            }
        }
        
        # Database connection health (50 points)
        $maxScore += 50
        if ($diagnostics.TypeScriptResults.DatabaseConnection) {
            if ($diagnostics.TypeScriptResults.DatabaseConnection.connectionWorking) {
                $healthScore += 50
            } elseif ($diagnostics.TypeScriptResults.DatabaseConnection.autoRecoverable) {
                $healthScore += 20
            } else {
                $healthScore += 5
            }
        }
        
        $healthPercentage = if ($maxScore -gt 0) { [math]::Round(($healthScore / $maxScore) * 100, 1) } else { 0 }
        $diagnostics.OverallHealth = $healthPercentage -ge 80
        
        Write-SafeOutput "Overall System Health: $healthPercentage% ($healthScore/$maxScore)" -Status $(
            if ($healthPercentage -ge 90) { "Success" }
            elseif ($healthPercentage -ge 70) { "Warning" }
            else { "Error" }
        )
        
        # Step 5: Auto-fix attempts if requested
        if ($AutoFix -and $diagnostics.TypeScriptResults.DatabaseConnection -and 
            -not $diagnostics.TypeScriptResults.DatabaseConnection.connectionWorking -and 
            $diagnostics.TypeScriptResults.DatabaseConnection.autoRecoverable) {
            
            Write-SafeSectionHeader "Automatic Recovery Attempts" 5
            Write-SafeOutput "Attempting automatic database error recovery..." -Status Processing
            
            $autoFixResult = Invoke-SafeCommand -Command "bun" -Arguments @("run", "--silent", "-e", "
                import { handleDatabaseError, attemptAutoRecovery } from './packages/db/src/database-error-handler.ts';
                import { db, users } from './packages/db/src/index.ts';
                
                try {
                    await db.select().from(users).limit(0);
                    console.log(JSON.stringify({ recovered: true, alreadyWorking: true }));
                } catch (error) {
                    try {
                        const dbError = await handleDatabaseError(error, 'auto-recovery-attempt');
                        const recovered = await attemptAutoRecovery(dbError);
                        console.log(JSON.stringify({ recovered: recovered, alreadyWorking: false }));
                    } catch (recoveryError) {
                        console.log(JSON.stringify({ recovered: false, error: recoveryError.message }));
                    }
                }
            ") -Description "Running automatic recovery" -IgnoreErrors
            
            if ($autoFixResult.Success) {
                try {
                    $recoveryResults = $autoFixResult.Output | ConvertFrom-Json -ErrorAction Stop
                    $diagnostics.AutoFixAttempts += $recoveryResults
                    
                    if ($recoveryResults.recovered) {
                        Write-SafeOutput "Auto-recovery: SUCCESS" -Status Success
                        $diagnostics.Recommendations += "Database connection has been automatically restored"
                    } else {
                        Write-SafeOutput "Auto-recovery: FAILED" -Status Warning
                        $diagnostics.Recommendations += "Manual intervention required - automatic recovery was unsuccessful"
                    }
                }
                catch {
                    Write-SafeOutput "Auto-recovery results could not be parsed" -Status Warning
                }
            } else {
                Write-SafeOutput "Auto-recovery attempt failed" -Status Error
                $diagnostics.Recommendations += "Auto-recovery system is not functional"
            }
        }
        
        # Step 6: Generate comprehensive report
        if ($GenerateReport) {
            Write-SafeSectionHeader "Generating Comprehensive Report" 6
            $reportPath = "database-diagnostics-report-$(Get-Date -Format 'yyyyMMdd-HHmmss').json"
            
            try {
                $diagnostics | ConvertTo-Json -Depth 10 | Out-File -FilePath $reportPath -Encoding UTF8
                Write-SafeOutput "Diagnostics report saved to: $reportPath" -Status Success
            }
            catch {
                Write-SafeOutput "Failed to save diagnostics report: $($_.Exception.Message)" -Status Warning
            }
        }
        
        return $diagnostics
        
    } catch {
        Write-SafeOutput "Enterprise diagnostics encountered an error: $($_.Exception.Message)" -Status Error
        return $diagnostics
    }
}

function Invoke-StartupSystemCheck {
    <#
    .SYNOPSIS
    Performs critical system checks required before application startup
    #>
    
    Write-SafeHeader "STARTUP SYSTEM CHECK" "="
    Write-SafeOutput "Verifying system readiness for application startup..." -Status Processing
    
    $startupResults = @{
        PostgreSQLService = $false
        EnvironmentConfig = $false
        DatabaseConnection = $false
        RequiredPorts = $false
        SystemDependencies = $false
        OverallReady = $false
        BlockingIssues = @()
        Warnings = @()
    }
    
    try {
        # Check 1: PostgreSQL Service
        Write-SafeOutput "Checking PostgreSQL service..." -Status Processing
        $pgService = Get-Service -Name "*postgresql*" -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "Running" } | Select-Object -First 1
        
        if ($pgService) {
            $startupResults.PostgreSQLService = $true
            Write-SafeOutput "PostgreSQL service: RUNNING ($($pgService.Name))" -Status Success
        } else {
            $startupResults.BlockingIssues += "PostgreSQL service is not running"
            Write-SafeOutput "PostgreSQL service: NOT RUNNING" -Status Error
        }
        
        # Check 2: Environment Configuration
        Write-SafeOutput "Checking environment configuration..." -Status Processing
        $envCheck = Test-Path ".env"
        
        if ($envCheck) {
            $envContent = Get-Content ".env" -Raw
            $hasDatabaseUrl = $envContent -match "DATABASE_URL\s*="
            $hasApiPort = $envContent -match "API_PORT\s*="
            
            if ($hasDatabaseUrl -and $hasApiPort) {
                $startupResults.EnvironmentConfig = $true
                Write-SafeOutput "Environment configuration: VALID" -Status Success
            } else {
                $startupResults.BlockingIssues += "Environment configuration is incomplete"
                Write-SafeOutput "Environment configuration: INCOMPLETE" -Status Error
            }
        } else {
            $startupResults.BlockingIssues += ".env file is missing"
            Write-SafeOutput "Environment configuration: MISSING" -Status Error
        }
        
        # Check 3: Database Connection
        Write-SafeOutput "Testing database connection..." -Status Processing
        $dbTest = Invoke-SafeCommand -Command "bun" -Arguments @("run", "--silent", "-e", "
            import { db, users } from './packages/db/src/index.ts';
            try {
                await db.select().from(users).limit(0);
                console.log('SUCCESS');
            } catch (error) {
                console.log('FAILED: ' + error.message);
            }
        ") -Description "Testing database connection" -IgnoreErrors -TimeoutSeconds 10
        
        if ($dbTest.Success -and $dbTest.Output -eq "SUCCESS") {
            $startupResults.DatabaseConnection = $true
            Write-SafeOutput "Database connection: SUCCESS" -Status Success
        } else {
            $startupResults.BlockingIssues += "Database connection failed"
            Write-SafeOutput "Database connection: FAILED" -Status Error
        }
        
        # Check 4: Required Ports
        Write-SafeOutput "Checking required ports..." -Status Processing
        $apiPortFree = -not (Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue)
        $webPortFree = -not (Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue)
        
        if ($apiPortFree -and $webPortFree) {
            $startupResults.RequiredPorts = $true
            Write-SafeOutput "Required ports (3001, 5173): AVAILABLE" -Status Success
        } else {
            $portIssues = @()
            if (-not $apiPortFree) { $portIssues += "3001" }
            if (-not $webPortFree) { $portIssues += "5173" }
            $startupResults.Warnings += "Ports in use: $($portIssues -join ', ')"
            Write-SafeOutput "Required ports: IN USE ($($portIssues -join ', '))" -Status Warning
            # Not blocking - applications can handle port conflicts
            $startupResults.RequiredPorts = $true
        }
        
        # Check 5: System Dependencies
        Write-SafeOutput "Checking system dependencies..." -Status Processing
        $bunAvailable = Invoke-SafeCommand -Command "bun" -Arguments @("--version") -Description "Checking Bun availability" -IgnoreErrors
        $nodeAvailable = Invoke-SafeCommand -Command "node" -Arguments @("--version") -Description "Checking Node.js availability" -IgnoreErrors
        
        if ($bunAvailable.Success) {
            $startupResults.SystemDependencies = $true
            Write-SafeOutput "System dependencies: AVAILABLE (Bun $($bunAvailable.Output))" -Status Success
        } elseif ($nodeAvailable.Success) {
            $startupResults.SystemDependencies = $true
            $startupResults.Warnings += "Using Node.js instead of Bun (performance may be reduced)"
            Write-SafeOutput "System dependencies: AVAILABLE (Node.js $($nodeAvailable.Output))" -Status Warning
        } else {
            $startupResults.BlockingIssues += "Neither Bun nor Node.js is available"
            Write-SafeOutput "System dependencies: MISSING" -Status Error
        }
        
        # Overall Assessment
        $startupResults.OverallReady = $startupResults.PostgreSQLService -and 
                                     $startupResults.EnvironmentConfig -and 
                                     $startupResults.DatabaseConnection -and 
                                     $startupResults.RequiredPorts -and 
                                     $startupResults.SystemDependencies
        
        Write-SafeSectionHeader "STARTUP READINESS SUMMARY"
        
        if ($startupResults.OverallReady) {
            Write-SafeOutput "System Status: READY FOR STARTUP" -Status Complete
            Write-SafeOutput "All critical checks passed successfully" -Status Success
            
            if ($startupResults.Warnings.Count -gt 0) {
                Write-SafeOutput "Warnings:" -Status Warning
                $startupResults.Warnings | ForEach-Object {
                    Write-SafeOutput "  - $_" -Status Warning
                }
            }
        } else {
            Write-SafeOutput "System Status: NOT READY FOR STARTUP" -Status Error
            Write-SafeOutput "Blocking issues found:" -Status Error
            $startupResults.BlockingIssues | ForEach-Object {
                Write-SafeOutput "  - $_" -Status Error
            }
            
            Write-SafeOutput "Resolution steps:" -Status Info
            Write-SafeOutput "  1. Fix blocking issues listed above" -Status Info
            Write-SafeOutput "  2. Run startup check again: .\scripts\db-doctor.ps1 -StartupCheck" -Status Info
            Write-SafeOutput "  3. Or run auto-fix: .\scripts\db-doctor.ps1 -Fix" -Status Info
        }
        
        return $startupResults
        
    } catch {
        Write-SafeOutput "Startup check encountered an error: $($_.Exception.Message)" -Status Error
        $startupResults.BlockingIssues += "Startup check system error: $($_.Exception.Message)"
        return $startupResults
    }
}

function Invoke-ContinuousHealthCheck {
    <#
    .SYNOPSIS
    Performs continuous health monitoring of database and system components
    #>
    
    param(
        [int]$IntervalSeconds = 60,
        [int]$MaxIterations = 0, # 0 = infinite
        [switch]$LogToFile = $false
    )
    
    Write-SafeHeader "CONTINUOUS HEALTH CHECK" "="
    Write-SafeOutput "Starting continuous health monitoring..." -Status Processing
    Write-SafeOutput "Interval: $IntervalSeconds seconds" -Status Info
    Write-SafeOutput "Max iterations: $(if ($MaxIterations -eq 0) { 'Infinite' } else { $MaxIterations })" -Status Info
    
    $iteration = 0
    $logFile = if ($LogToFile) { "health-check-log-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt" } else { $null }
    
    if ($logFile) {
        "Health Check Log Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $logFile -Encoding UTF8
        Write-SafeOutput "Logging to: $logFile" -Status Info
    }
    
    try {
        while ($MaxIterations -eq 0 -or $iteration -lt $MaxIterations) {
            $iteration++
            $timestamp = Get-Date -Format 'HH:mm:ss'
            
            Write-Host "`n[$timestamp] Health Check #$iteration" -ForegroundColor Cyan
            
            $healthResults = @{
                Timestamp = Get-Date
                PostgreSQLService = $false
                DatabaseConnection = $false
                SystemMemory = 0
                DiskSpace = 0
                ActiveConnections = 0
                Issues = @()
            }
            
            # Check PostgreSQL Service
            $pgService = Get-Service -Name "*postgresql*" -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "Running" } | Select-Object -First 1
            $healthResults.PostgreSQLService = $pgService -ne $null
            
            if ($healthResults.PostgreSQLService) {
                Write-SafeOutput "PostgreSQL Service: RUNNING" -Status Success
            } else {
                Write-SafeOutput "PostgreSQL Service: STOPPED" -Status Error
                $healthResults.Issues += "PostgreSQL service is not running"
            }
            
            # Check Database Connection
            $dbTest = Invoke-SafeCommand -Command "bun" -Arguments @("run", "--silent", "-e", "
                import { db, users } from './packages/db/src/index.ts';
                try {
                    const start = Date.now();
                    await db.select().from(users).limit(1);
                    console.log('SUCCESS:' + (Date.now() - start) + 'ms');
                } catch (error) {
                    console.log('FAILED:' + error.message);
                }
            ") -Description "Database connection health check" -IgnoreErrors -TimeoutSeconds 15
            
            if ($dbTest.Success -and $dbTest.Output -match "SUCCESS:(\d+)ms") {
                $responseTime = $matches[1]
                $healthResults.DatabaseConnection = $true
                Write-SafeOutput "Database Connection: SUCCESS (${responseTime}ms)" -Status Success
                
                if ([int]$responseTime -gt 5000) {
                    $healthResults.Issues += "Database response time is high: ${responseTime}ms"
                    Write-SafeOutput "  Response time warning: ${responseTime}ms > 5000ms" -Status Warning
                }
            } else {
                Write-SafeOutput "Database Connection: FAILED" -Status Error
                $healthResults.Issues += "Database connection failed"
            }
            
            # Check System Resources
            try {
                $memory = Get-WmiObject -Class Win32_OperatingSystem
                $memoryUsagePercent = [math]::Round((($memory.TotalVisibleMemorySize - $memory.FreePhysicalMemory) / $memory.TotalVisibleMemorySize) * 100, 1)
                $healthResults.SystemMemory = $memoryUsagePercent
                
                Write-SafeOutput "System Memory: ${memoryUsagePercent}% used" -Status $(
                    if ($memoryUsagePercent -gt 90) { "Error" }
                    elseif ($memoryUsagePercent -gt 75) { "Warning" }
                    else { "Success" }
                )
                
                if ($memoryUsagePercent -gt 90) {
                    $healthResults.Issues += "High memory usage: ${memoryUsagePercent}%"
                }
            }
            catch {
                Write-SafeOutput "System Memory: Unable to check" -Status Warning
            }
            
            # Log results if requested
            if ($logFile) {
                $logEntry = "[$($healthResults.Timestamp.ToString('yyyy-MM-dd HH:mm:ss'))] " +
                           "PostgreSQL: $(if ($healthResults.PostgreSQLService) { 'OK' } else { 'FAIL' }) | " +
                           "Database: $(if ($healthResults.DatabaseConnection) { 'OK' } else { 'FAIL' }) | " +
                           "Memory: $($healthResults.SystemMemory)% | " +
                           "Issues: $($healthResults.Issues.Count)"
                
                $logEntry | Out-File -FilePath $logFile -Append -Encoding UTF8
                
                if ($healthResults.Issues.Count -gt 0) {
                    $healthResults.Issues | ForEach-Object {
                        "  - $_" | Out-File -FilePath $logFile -Append -Encoding UTF8
                    }
                }
            }
            
            # Wait for next iteration
            if ($MaxIterations -eq 0 -or $iteration -lt $MaxIterations) {
                Write-SafeOutput "Next check in $IntervalSeconds seconds... (Press Ctrl+C to stop)" -Status Info
                Start-Sleep -Seconds $IntervalSeconds
            }
        }
        
        Write-SafeOutput "Health monitoring completed after $iteration iterations" -Status Complete
        
    } catch {
        Write-SafeOutput "Health monitoring interrupted: $($_.Exception.Message)" -Status Warning
    }
}

# Export functions for use in main db-doctor.ps1
Export-ModuleMember -Function Invoke-EnterpriseDatabaseDiagnostics, Invoke-StartupSystemCheck, Invoke-ContinuousHealthCheck