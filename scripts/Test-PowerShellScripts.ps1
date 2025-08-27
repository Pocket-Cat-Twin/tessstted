# ================================
# PowerShell Scripts Integration Tests
# YuYu Lolita Shopping System
# Enterprise-grade testing framework
# ================================

[CmdletBinding()]
param(
    [switch]$SkipNetworkTests = $false,
    [string[]]$TestSuites = @("Common", "Environment", "Build", "Setup")
)

# Import common functions with validation
$commonLibPath = Join-Path $PSScriptRoot "PowerShell-Common.ps1"
if (-not (Test-Path $commonLibPath)) {
    Write-Error "Required PowerShell-Common.ps1 not found at: $commonLibPath"
    exit 1
}
. $commonLibPath

# Test configuration
$Script:TEST_TIMEOUT_SECONDS = 30
$Script:TEST_RESULTS = @{
    Total = 0
    Passed = 0
    Failed = 0
    Skipped = 0
    Suites = @{}
}

# ==============================================================================
# TEST FRAMEWORK
# ==============================================================================

function Test-Function {
    <#
    .SYNOPSIS
    Executes a test function with proper error handling and result tracking
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$TestName,
        
        [Parameter(Mandatory = $true)]
        [ScriptBlock]$TestBlock,
        
        [string]$Suite = "General",
        
        [switch]$SkipTest
    )
    
    $Script:TEST_RESULTS.Total++
    
    if (-not $Script:TEST_RESULTS.Suites.ContainsKey($Suite)) {
        $Script:TEST_RESULTS.Suites[$Suite] = @{
            Total = 0
            Passed = 0
            Failed = 0
            Skipped = 0
            Tests = @()
        }
    }
    
    $Script:TEST_RESULTS.Suites[$Suite].Total++
    
    if ($SkipTest) {
        Write-SafeOutput "SKIP: $TestName" -Status Skip
        $Script:TEST_RESULTS.Skipped++
        $Script:TEST_RESULTS.Suites[$Suite].Skipped++
        $Script:TEST_RESULTS.Suites[$Suite].Tests += @{
            Name = $TestName
            Status = "Skipped"
            Message = "Test skipped by request"
        }
        return
    }
    
    try {
        $startTime = Get-Date
        $result = & $TestBlock
        $duration = (Get-Date) - $startTime
        
        if ($result -eq $true -or ($result -is [hashtable] -and $result.Success -eq $true)) {
            Write-SafeOutput "PASS: $TestName ($([math]::Round($duration.TotalSeconds, 2))s)" -Status Success
            $Script:TEST_RESULTS.Passed++
            $Script:TEST_RESULTS.Suites[$Suite].Passed++
            $Script:TEST_RESULTS.Suites[$Suite].Tests += @{
                Name = $TestName
                Status = "Passed"
                Duration = $duration.TotalSeconds
                Message = if ($result -is [hashtable] -and $result.Message) { $result.Message } else { "Test passed" }
            }
        }
        else {
            $errorMessage = if ($result -is [hashtable] -and $result.Message) { $result.Message } else { "Test returned false" }
            Write-SafeOutput "FAIL: $TestName - $errorMessage" -Status Error
            $Script:TEST_RESULTS.Failed++
            $Script:TEST_RESULTS.Suites[$Suite].Failed++
            $Script:TEST_RESULTS.Suites[$Suite].Tests += @{
                Name = $TestName
                Status = "Failed"
                Duration = $duration.TotalSeconds
                Message = $errorMessage
                Error = if ($result -is [hashtable] -and $result.Error) { $result.Error } else { $null }
            }
        }
    }
    catch {
        Write-SafeOutput "FAIL: $TestName - Exception: $($_.Exception.Message)" -Status Error
        $Script:TEST_RESULTS.Failed++
        $Script:TEST_RESULTS.Suites[$Suite].Failed++
        $Script:TEST_RESULTS.Suites[$Suite].Tests += @{
            Name = $TestName
            Status = "Failed"
            Duration = 0
            Message = "Test threw exception"
            Error = $_.Exception.Message
        }
    }
}

# ==============================================================================
# POWERSHELL-COMMON.PS1 TESTS
# ==============================================================================

function Test-CommonLibraryFunctions {
    Write-SafeSectionHeader "PowerShell-Common.ps1 Function Tests" -Step 1
    
    # Test Write-SafeOutput
    Test-Function -TestName "Write-SafeOutput Function" -Suite "Common" -TestBlock {
        try {
            Write-SafeOutput "Test message" -Status Info
            return $true
        }
        catch {
            return @{ Success = $false; Message = "Write-SafeOutput failed"; Error = $_.Exception.Message }
        }
    }
    
    # Test Get-ProjectRoot
    Test-Function -TestName "Get-ProjectRoot Function" -Suite "Common" -TestBlock {
        $projectRoot = Get-ProjectRoot
        if ($projectRoot -and (Test-Path $projectRoot)) {
            return @{ Success = $true; Message = "Project root found: $projectRoot" }
        }
        else {
            return @{ Success = $false; Message = "Project root not found or invalid" }
        }
    }
    
    # Test Test-PathSafely
    Test-Function -TestName "Test-PathSafely Function" -Suite "Common" -TestBlock {
        $tempPath = $env:TEMP
        $result = Test-PathSafely -Path $tempPath -Type Directory
        
        if ($result.Exists -and $result.MatchesType) {
            return @{ Success = $true; Message = "Path validation successful" }
        }
        else {
            return @{ Success = $false; Message = "Path validation failed: $($result.Message)" }
        }
    }
    
    # Test New-TempConfigFile
    Test-Function -TestName "New-TempConfigFile Function" -Suite "Common" -TestBlock {
        $testContent = "test=value`nkey=data"
        $result = New-TempConfigFile -Content $testContent
        
        if ($result.Success -and (Test-Path $result.FilePath)) {
            # Cleanup
            if ($result.CleanupAction) {
                & $result.CleanupAction $result.FilePath $false
            }
            return @{ Success = $true; Message = "Temp config file created and cleaned up" }
        }
        else {
            return @{ Success = $false; Message = "Temp config file creation failed" }
        }
    }
    
    # Test Read-EnvFileSafely with mock data
    Test-Function -TestName "Read-EnvFileSafely Function" -Suite "Common" -TestBlock {
        $tempEnvContent = @"
# Test environment file
TEST_VAR1=value1
TEST_VAR2="quoted value"
TEST_VAR3=unquoted value
"@
        
        $tempEnvFile = [System.IO.Path]::GetTempFileName()
        try {
            $tempEnvContent | Out-File -FilePath $tempEnvFile -Encoding ASCII -Force
            
            $result = Read-EnvFileSafely -EnvFilePath $tempEnvFile -RequiredVariables @("TEST_VAR1", "TEST_VAR2")
            
            if ($result.Success -and $result.Variables["TEST_VAR1"] -eq "value1" -and $result.Variables["TEST_VAR2"] -eq "quoted value") {
                return @{ Success = $true; Message = "Environment file parsing successful" }
            }
            else {
                return @{ Success = $false; Message = "Environment file parsing failed: $($result.Message)" }
            }
        }
        finally {
            if (Test-Path $tempEnvFile) {
                Remove-Item $tempEnvFile -Force -ErrorAction SilentlyContinue
            }
        }
    }
    
    # Test Test-CommandAvailability
    Test-Function -TestName "Test-CommandAvailability Function" -Suite "Common" -TestBlock {
        $commands = @{
            "powershell" = "Windows PowerShell (built-in)"
            "cmd" = "Windows Command Prompt (built-in)"
        }
        
        $result = Test-CommandAvailability -CommandMap $commands -ShowVersions
        
        if ($result.AllAvailable) {
            return @{ Success = $true; Message = "Command availability test passed" }
        }
        else {
            return @{ Success = $false; Message = "Some required commands not available" }
        }
    }
}

# ==============================================================================
# ENVIRONMENT CHECK SCRIPT TESTS
# ==============================================================================

function Test-EnvironmentCheckScript {
    Write-SafeSectionHeader "db-environment-check-windows.ps1 Tests" -Step 2
    
    $envCheckScript = Join-Path $PSScriptRoot "db-environment-check-windows.ps1"
    
    # Test script existence
    Test-Function -TestName "Environment Check Script Exists" -Suite "Environment" -TestBlock {
        $scriptTest = Test-PathSafely -Path $envCheckScript -Type File
        if ($scriptTest.Exists -and $scriptTest.MatchesType) {
            return @{ Success = $true; Message = "Environment check script found" }
        }
        else {
            return @{ Success = $false; Message = "Environment check script not found" }
        }
    }
    
    # Test script syntax
    Test-Function -TestName "Environment Check Script Syntax" -Suite "Environment" -TestBlock {
        try {
            $null = [System.Management.Automation.PSParser]::Tokenize((Get-Content $envCheckScript -Raw), [ref]$null)
            return @{ Success = $true; Message = "Script syntax is valid" }
        }
        catch {
            return @{ Success = $false; Message = "Script syntax error"; Error = $_.Exception.Message }
        }
    }
    
    # Test script help
    Test-Function -TestName "Environment Check Script Help" -Suite "Environment" -TestBlock {
        try {
            $result = & powershell -ExecutionPolicy Bypass -File $envCheckScript -? 2>&1
            if ($result -like "*SYNOPSIS*" -or $result -like "*environment*") {
                return @{ Success = $true; Message = "Script help available" }
            }
            else {
                return @{ Success = $false; Message = "Script help not available or incomplete" }
            }
        }
        catch {
            return @{ Success = $false; Message = "Script help test failed"; Error = $_.Exception.Message }
        }
    }
}

# ==============================================================================
# BUILD SCRIPT TESTS
# ==============================================================================

function Test-BuildScript {
    Write-SafeSectionHeader "build-windows.ps1 Tests" -Step 3
    
    $buildScript = Join-Path $PSScriptRoot "build-windows.ps1"
    
    # Test script existence
    Test-Function -TestName "Build Script Exists" -Suite "Build" -TestBlock {
        $scriptTest = Test-PathSafely -Path $buildScript -Type File
        if ($scriptTest.Exists -and $scriptTest.MatchesType) {
            return @{ Success = $true; Message = "Build script found" }
        }
        else {
            return @{ Success = $false; Message = "Build script not found" }
        }
    }
    
    # Test script syntax
    Test-Function -TestName "Build Script Syntax" -Suite "Build" -TestBlock {
        try {
            $null = [System.Management.Automation.PSParser]::Tokenize((Get-Content $buildScript -Raw), [ref]$null)
            return @{ Success = $true; Message = "Script syntax is valid" }
        }
        catch {
            return @{ Success = $false; Message = "Script syntax error"; Error = $_.Exception.Message }
        }
    }
    
    # Test project structure validation (dry run)
    Test-Function -TestName "Build Script Project Structure Check" -Suite "Build" -TestBlock {
        $projectRoot = Get-ProjectRoot
        $packagesDir = Join-Path $projectRoot "packages"
        $appsDir = Join-Path $projectRoot "apps"
        
        $hasPackages = Test-Path $packagesDir
        $hasApps = Test-Path $appsDir
        
        if ($hasPackages -and $hasApps) {
            return @{ Success = $true; Message = "Project structure compatible with build script" }
        }
        else {
            return @{ Success = $false; Message = "Project structure may not be compatible with build script" }
        }
    }
}

# ==============================================================================
# SETUP SCRIPT TESTS
# ==============================================================================

function Test-SetupScript {
    Write-SafeSectionHeader "db-setup-complete-windows.ps1 Tests" -Step 4
    
    $setupScript = Join-Path $PSScriptRoot "db-setup-complete-windows.ps1"
    
    # Test script existence
    Test-Function -TestName "Setup Script Exists" -Suite "Setup" -TestBlock {
        $scriptTest = Test-PathSafely -Path $setupScript -Type File
        if ($scriptTest.Exists -and $scriptTest.MatchesType) {
            return @{ Success = $true; Message = "Setup script found" }
        }
        else {
            return @{ Success = $false; Message = "Setup script not found" }
        }
    }
    
    # Test script syntax
    Test-Function -TestName "Setup Script Syntax" -Suite "Setup" -TestBlock {
        try {
            $null = [System.Management.Automation.PSParser]::Tokenize((Get-Content $setupScript -Raw), [ref]$null)
            return @{ Success = $true; Message = "Script syntax is valid" }
        }
        catch {
            return @{ Success = $false; Message = "Script syntax error"; Error = $_.Exception.Message }
        }
    }
    
    # Test database package structure
    Test-Function -TestName "Database Package Structure" -Suite "Setup" -TestBlock {
        $projectRoot = Get-ProjectRoot
        $dbPackage = Join-Path $projectRoot "packages\db"
        $seedScript = Join-Path $dbPackage "src\seed-users.ts"
        
        $hasDbPackage = Test-Path $dbPackage
        $hasSeedScript = Test-Path $seedScript
        
        if ($hasDbPackage -and $hasSeedScript) {
            return @{ Success = $true; Message = "Database package structure valid" }
        }
        else {
            return @{ Success = $false; Message = "Database package structure incomplete" }
        }
    }
}

# ==============================================================================
# NETWORK AND SYSTEM TESTS
# ==============================================================================

function Test-NetworkAndSystemFunctions {
    Write-SafeSectionHeader "Network and System Function Tests" -Step 5
    
    # Test network port function (without actually connecting)
    Test-Function -TestName "Test-NetworkPortSafely Function" -Suite "Common" -TestBlock {
        # Test with a known closed port to verify function works
        $result = Test-NetworkPortSafely -HostName "127.0.0.1" -Port 9999 -TimeoutMs 1000
        
        # We expect this to fail (closed port), but function should work
        if ($result.ContainsKey("Success") -and $result.ContainsKey("Message")) {
            return @{ Success = $true; Message = "Network port test function working correctly" }
        }
        else {
            return @{ Success = $false; Message = "Network port test function not working properly" }
        }
    }
    
    # Test system resource monitoring
    Test-Function -TestName "Get-SystemResourceInfo Function" -Suite "Common" -TestBlock {
        $result = Get-SystemResourceInfo
        
        if ($result.Success -and $result.Memory -and $result.Processor) {
            return @{ Success = $true; Message = "System resource monitoring working" }
        }
        else {
            return @{ Success = $false; Message = "System resource monitoring failed" }
        }
    }
    
    # Test service checking (with a known Windows service)
    Test-Function -TestName "Test-ServiceSafely Function" -Suite "Common" -TestBlock {
        $result = Test-ServiceSafely -ServiceName "EventLog"  # Always present on Windows
        
        if ($result.Found) {
            return @{ Success = $true; Message = "Service checking function working" }
        }
        else {
            return @{ Success = $false; Message = "Service checking function failed to find known service" }
        }
    }
}

# ==============================================================================
# MAIN TEST EXECUTION
# ==============================================================================

function Invoke-PowerShellScriptTests {
    Write-SafeHeader "PowerShell Scripts Integration Tests"
    Write-SafeOutput "YuYu Lolita Shopping System - Enterprise Test Suite" -Status Info
    Write-Host ""
    
    # Run test suites based on parameters
    if ("Common" -in $TestSuites) {
        Test-CommonLibraryFunctions
        Test-NetworkAndSystemFunctions
    }
    
    if ("Environment" -in $TestSuites) {
        Test-EnvironmentCheckScript
    }
    
    if ("Build" -in $TestSuites) {
        Test-BuildScript
    }
    
    if ("Setup" -in $TestSuites) {
        Test-SetupScript
    }
}

function Show-TestResults {
    Write-Host ""
    Write-SafeHeader "Test Results Summary"
    
    # Overall statistics
    Write-SafeOutput "Total tests: $($Script:TEST_RESULTS.Total)" -Status Info
    Write-SafeOutput "Passed: $($Script:TEST_RESULTS.Passed)" -Status Success
    Write-SafeOutput "Failed: $($Script:TEST_RESULTS.Failed)" -Status Error
    Write-SafeOutput "Skipped: $($Script:TEST_RESULTS.Skipped)" -Status Skip
    
    # Suite breakdown
    Write-Host ""
    Write-SafeOutput "Test Suite Breakdown:" -Status Info
    foreach ($suiteName in $Script:TEST_RESULTS.Suites.Keys) {
        $suite = $Script:TEST_RESULTS.Suites[$suiteName]
        $passRate = if ($suite.Total -gt 0) { [math]::Round(($suite.Passed / $suite.Total) * 100, 1) } else { 0 }
        Write-SafeOutput "  $suiteName`: $($suite.Passed)/$($suite.Total) passed ($passRate%)" -Status Info
    }
    
    # Failed test details
    if ($Script:TEST_RESULTS.Failed -gt 0) {
        Write-Host ""
        Write-SafeOutput "Failed Tests:" -Status Error
        foreach ($suiteName in $Script:TEST_RESULTS.Suites.Keys) {
            $failedTests = $Script:TEST_RESULTS.Suites[$suiteName].Tests | Where-Object { $_.Status -eq "Failed" }
            foreach ($test in $failedTests) {
                Write-SafeOutput "  [$suiteName] $($test.Name): $($test.Message)" -Status Error
            }
        }
    }
    
    # Final status
    Write-Host ""
    $overallPassRate = if ($Script:TEST_RESULTS.Total -gt 0) { 
        [math]::Round(($Script:TEST_RESULTS.Passed / $Script:TEST_RESULTS.Total) * 100, 1) 
    } else { 0 }
    
    if ($Script:TEST_RESULTS.Failed -eq 0) {
        Write-SafeOutput "All tests passed! ($overallPassRate% success rate)" -Status Complete
        Write-SafeOutput "PowerShell scripts are ready for production use" -Status Success
        return $true
    }
    else {
        Write-SafeOutput "Some tests failed ($overallPassRate% success rate)" -Status Error
        Write-SafeOutput "Review failed tests and fix issues before production use" -Status Warning
        return $false
    }
}

# ==============================================================================
# SCRIPT ENTRY POINT
# ==============================================================================

try {
    # Execute integration tests
    Invoke-PowerShellScriptTests
    
    # Display results and exit with appropriate code
    $allTestsPassed = Show-TestResults
    
    exit $(if ($allTestsPassed) { 0 } else { 1 })
}
catch {
    Write-SafeOutput "Critical error during test execution: $($_.Exception.Message)" -Status Error
    Write-SafeOutput "Please check the test environment and try again" -Status Info
    exit 1
}