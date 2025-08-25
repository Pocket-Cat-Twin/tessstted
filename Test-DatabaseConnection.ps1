#Requires -Version 3.0

<#
.SYNOPSIS
    Test Windows PostgreSQL Connection for YuYu Lolita API
    
.DESCRIPTION
    Comprehensive testing script for Windows PostgreSQL database connection.
    Tests all aspects that the API requires for proper functionality.

.PARAMETER Detailed
    Show detailed test results and diagnostics

.EXAMPLE
    .\Test-DatabaseConnection.ps1
    Basic connection testing

.EXAMPLE  
    .\Test-DatabaseConnection.ps1 -Detailed
    Detailed testing with full diagnostics

.NOTES
    Version: 1.0.0 - Windows Edition
    Requires: PostgreSQL installed and configured
#>

[CmdletBinding()]
param(
    [switch]$Detailed = $false
)

# Configuration
$DB_NAME = "yuyu_lolita"
$DB_USER = "postgres"
$DB_PASSWORD = "postgres"
$DB_HOST = "localhost"
$DB_PORT = 5432

# Colors
function Write-TestResult($Message, $Status) {
    switch ($Status) {
        "Success" { Write-Host "✅ $Message" -ForegroundColor Green }
        "Error" { Write-Host "❌ $Message" -ForegroundColor Red }
        "Warning" { Write-Host "⚠️  $Message" -ForegroundColor Yellow }
        "Info" { Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
        default { Write-Host "$Message" }
    }
}

Write-Host "🧪 WINDOWS POSTGRESQL CONNECTION TESTING" -ForegroundColor Magenta
Write-Host "=========================================" -ForegroundColor Magenta
Write-Host ""

Write-TestResult "Target Configuration:" "Info"
Write-TestResult "  Database: $DB_NAME" "Info"
Write-TestResult "  User: $DB_USER" "Info"
Write-TestResult "  Host: $DB_HOST`:$DB_PORT" "Info"
Write-Host ""

# Find PostgreSQL installation
function Find-PostgreSQL {
    $possiblePaths = @(
        "C:\Program Files\PostgreSQL\*\bin\psql.exe",
        "C:\Program Files (x86)\PostgreSQL\*\bin\psql.exe"
    )
    
    foreach ($path in $possiblePaths) {
        $found = Get-ChildItem -Path $path -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            return $found.FullName
        }
    }
    return $null
}

$psqlPath = Find-PostgreSQL
if (-not $psqlPath) {
    Write-TestResult "PostgreSQL psql not found in standard locations" "Error"
    Write-TestResult "Please ensure PostgreSQL is installed" "Error"
    exit 1
}

Write-TestResult "Found PostgreSQL: $psqlPath" "Success"

# Set environment for all tests
$env:PGPASSWORD = $DB_PASSWORD

# Test definitions
$tests = @(
    @{
        Name = "PostgreSQL Service Status"
        Description = "Check if PostgreSQL Windows service is running"
        Test = {
            $service = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "Running" } | Select-Object -First 1
            if ($service) {
                Write-TestResult "PostgreSQL service '$($service.Name)' is running" "Success"
                return $true
            } else {
                Write-TestResult "PostgreSQL service is not running" "Error"
                return $false
            }
        }
    },
    
    @{
        Name = "Network Connectivity"
        Description = "Test network connection to PostgreSQL port"
        Test = {
            try {
                $connection = Test-NetConnection -ComputerName $DB_HOST -Port $DB_PORT -ErrorAction Stop
                if ($connection.TcpTestSucceeded) {
                    Write-TestResult "Network connection to $DB_HOST`:$DB_PORT successful" "Success"
                    return $true
                } else {
                    Write-TestResult "Network connection to $DB_HOST`:$DB_PORT failed" "Error"
                    return $false
                }
            } catch {
                Write-TestResult "Network test failed: $($_.Exception.Message)" "Error"
                return $false
            }
        }
    },
    
    @{
        Name = "Basic Authentication"
        Description = "Test postgres user authentication"
        Test = {
            try {
                $result = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "SELECT current_user;" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-TestResult "Authentication successful for user '$DB_USER'" "Success"
                    if ($Detailed) { Write-TestResult "  Result: $result" "Info" }
                    return $true
                } else {
                    Write-TestResult "Authentication failed for user '$DB_USER'" "Error"
                    return $false
                }
            } catch {
                Write-TestResult "Authentication test error: $($_.Exception.Message)" "Error"
                return $false
            }
        }
    },
    
    @{
        Name = "Database Existence"
        Description = "Check if yuyu_lolita database exists"
        Test = {
            try {
                $query = "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';"
                $result = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -tAc $query 2>$null
                if ($LASTEXITCODE -eq 0 -and $result -eq "1") {
                    Write-TestResult "Database '$DB_NAME' exists" "Success"
                    return $true
                } else {
                    Write-TestResult "Database '$DB_NAME' does not exist" "Error"
                    return $false
                }
            } catch {
                Write-TestResult "Database existence check error: $($_.Exception.Message)" "Error"
                return $false
            }
        }
    },
    
    @{
        Name = "Database Connection"
        Description = "Test connection to yuyu_lolita database"
        Test = {
            try {
                $result = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT current_database(), current_user;" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-TestResult "Connection to database '$DB_NAME' successful" "Success"
                    if ($Detailed) { Write-TestResult "  Result: $result" "Info" }
                    return $true
                } else {
                    Write-TestResult "Connection to database '$DB_NAME' failed" "Error"
                    return $false
                }
            } catch {
                Write-TestResult "Database connection error: $($_.Exception.Message)" "Error"
                return $false
            }
        }
    },
    
    @{
        Name = "Schema Validation"
        Description = "Check database schema and tables"
        Test = {
            try {
                $query = "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
                $tableCount = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc $query 2>$null
                
                if ($LASTEXITCODE -eq 0) {
                    $count = [int]$tableCount
                    if ($count -ge 20) {
                        Write-TestResult "Database schema valid ($count tables found)" "Success"
                        return $true
                    } else {
                        Write-TestResult "Database schema incomplete ($count tables found, expected 20+)" "Warning"
                        return $false
                    }
                } else {
                    Write-TestResult "Schema validation failed" "Error"
                    return $false
                }
            } catch {
                Write-TestResult "Schema validation error: $($_.Exception.Message)" "Error"
                return $false
            }
        }
    },
    
    @{
        Name = "Config Table Access (API Critical)"
        Description = "Test access to config table (required by API)"
        Test = {
            try {
                $query = "SELECT COUNT(*) FROM config;"
                $result = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc $query 2>$null
                
                if ($LASTEXITCODE -eq 0) {
                    Write-TestResult "Config table accessible (API requirement satisfied)" "Success"
                    if ($Detailed) { Write-TestResult "  Config entries: $result" "Info" }
                    return $true
                } else {
                    Write-TestResult "Config table access failed (API will fail)" "Error"
                    return $false
                }
            } catch {
                Write-TestResult "Config table test error: $($_.Exception.Message)" "Error"
                return $false
            }
        }
    },
    
    @{
        Name = "Users Table Access"
        Description = "Test access to users table"
        Test = {
            try {
                $query = "SELECT COUNT(*) FROM users;"
                $result = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc $query 2>$null
                
                if ($LASTEXITCODE -eq 0) {
                    Write-TestResult "Users table accessible" "Success"
                    if ($Detailed) { Write-TestResult "  User count: $result" "Info" }
                    return $true
                } else {
                    Write-TestResult "Users table access failed" "Error"
                    return $false
                }
            } catch {
                Write-TestResult "Users table test error: $($_.Exception.Message)" "Error"
                return $false
            }
        }
    },
    
    @{
        Name = "Write Operation Test"
        Description = "Test database write capabilities"
        Test = {
            try {
                $query = "INSERT INTO config (key, value, type, description) VALUES ('connection_test', 'success', 'string', 'Connection test from Windows') ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP;"
                $result = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c $query 2>$null
                
                if ($LASTEXITCODE -eq 0) {
                    Write-TestResult "Write operation successful" "Success"
                    return $true
                } else {
                    Write-TestResult "Write operation failed" "Error"
                    return $false
                }
            } catch {
                Write-TestResult "Write operation error: $($_.Exception.Message)" "Error"
                return $false
            }
        }
    },
    
    @{
        Name = "Complex Query Test"
        Description = "Test complex SQL operations (JOIN, aggregates)"
        Test = {
            try {
                $query = @"
SELECT 
    (SELECT COUNT(*) FROM users) as users_count,
    (SELECT COUNT(*) FROM config) as config_count,
    (SELECT COUNT(*) FROM orders) as orders_count,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public') as tables_count;
"@
                $result = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c $query 2>$null
                
                if ($LASTEXITCODE -eq 0) {
                    Write-TestResult "Complex query execution successful" "Success"
                    if ($Detailed) { Write-TestResult "  Query result: $result" "Info" }
                    return $true
                } else {
                    Write-TestResult "Complex query failed" "Error"
                    return $false
                }
            } catch {
                Write-TestResult "Complex query error: $($_.Exception.Message)" "Error"
                return $false
            }
        }
    }
)

# Run all tests
Write-TestResult "Running $($tests.Count) connection tests..." "Info"
Write-Host ""

$passedTests = 0
$totalTests = $tests.Count

foreach ($test in $tests) {
    Write-Host "🔄 Testing: $($test.Name)" -ForegroundColor Yellow
    if ($Detailed) {
        Write-Host "   $($test.Description)" -ForegroundColor Gray
    }
    
    try {
        $result = & $test.Test
        if ($result) {
            $passedTests++
        }
    } catch {
        Write-TestResult "Test execution error: $($_.Exception.Message)" "Error"
    }
    
    Write-Host ""
}

# Results Summary
Write-Host "📊 TEST RESULTS SUMMARY" -ForegroundColor Magenta
Write-Host "=======================" -ForegroundColor Magenta
Write-Host ""

$successRate = [math]::Round(($passedTests / $totalTests) * 100, 1)

Write-TestResult "Tests passed: $passedTests/$totalTests ($successRate%)" "Info"

if ($passedTests -eq $totalTests) {
    Write-TestResult "🎉 ALL TESTS PASSED!" "Success"
    Write-TestResult "🚀 API WILL WORK PERFECTLY WITH THIS DATABASE!" "Success"
    Write-Host ""
    Write-TestResult "✅ Database Configuration Summary:" "Success"
    Write-TestResult "   • PostgreSQL service is running" "Success"
    Write-TestResult "   • Network connectivity is working" "Success"
    Write-TestResult "   • User authentication is configured" "Success"
    Write-TestResult "   • Database and schema are complete" "Success"
    Write-TestResult "   • All API-required tables are accessible" "Success"
    Write-TestResult "   • Read and write operations work" "Success"
    Write-Host ""
    Write-TestResult "🔗 CONNECTION STRING FOR API:" "Info"
    Write-Host "   DATABASE_URL=postgresql://$DB_USER`:$DB_PASSWORD@$DB_HOST`:$DB_PORT/$DB_NAME" -ForegroundColor Yellow
    
} elseif ($passedTests -ge ($totalTests * 0.8)) {
    Write-TestResult "⚠️  MOST TESTS PASSED - Minor issues detected" "Warning"
    Write-TestResult "API may work with limited functionality" "Warning"
    Write-TestResult "Run .\Setup-WindowsDatabase.ps1 -Configure to fix issues" "Info"
    
} else {
    Write-TestResult "❌ CRITICAL ISSUES DETECTED" "Error"
    Write-TestResult "API will likely fail to start" "Error"
    Write-TestResult "Run .\Setup-WindowsDatabase.ps1 -Install -Configure to fix" "Info"
}

Write-Host ""
Write-TestResult "💡 Troubleshooting Commands:" "Info"
Write-TestResult "   • Full setup: .\Setup-WindowsDatabase.ps1 -Install -Configure" "Info"
Write-TestResult "   • Configure only: .\Setup-WindowsDatabase.ps1 -Configure" "Info"
Write-TestResult "   • Check service: Get-Service postgresql*" "Info"
Write-TestResult "   • Manual connection: psql -h $DB_HOST -U $DB_USER -d $DB_NAME" "Info"

exit $(if ($passedTests -eq $totalTests) { 0 } else { 1 })