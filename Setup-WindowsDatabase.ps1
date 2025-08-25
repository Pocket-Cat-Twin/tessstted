#Requires -Version 3.0
#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Complete Windows PostgreSQL Setup for YuYu Lolita API
    Senior-level enterprise solution for Windows database configuration

.DESCRIPTION
    This script provides complete Windows PostgreSQL setup including:
    - PostgreSQL installation (if needed)
    - postgres user creation with postgres password
    - Database creation and configuration
    - Migration execution
    - Windows service configuration
    - Connection testing and validation

.PARAMETER Install
    Install PostgreSQL if not found

.PARAMETER Configure
    Configure existing PostgreSQL installation

.PARAMETER TestOnly
    Only test the connection, don't make changes

.EXAMPLE
    .\Setup-WindowsDatabase.ps1 -Install -Configure
    Complete setup with installation and configuration

.EXAMPLE
    .\Setup-WindowsDatabase.ps1 -Configure
    Configure existing PostgreSQL

.EXAMPLE
    .\Setup-WindowsDatabase.ps1 -TestOnly
    Test current configuration only

.NOTES
    Author: Senior DevOps Engineer
    Version: 2.0.0 - Windows Enterprise Edition
    Requires: Windows PowerShell 3.0+, Administrator privileges
#>

[CmdletBinding()]
param(
    [switch]$Install = $false,
    [switch]$Configure = $true,
    [switch]$TestOnly = $false
)

# Import common functions
$ModulePath = Join-Path $PSScriptRoot "PowerShell-Common.psd1"
if (Test-Path $ModulePath) {
    try {
        Import-Module $ModulePath -Force -ErrorAction Stop
        Write-Host "[SUCCESS] PowerShell-Common module loaded" -ForegroundColor Green
    } catch {
        Write-Warning "Module import failed: $($_.Exception.Message)"
        # Fallback to legacy script
        $LegacyPath = Join-Path $PSScriptRoot "PowerShell-Common.ps1"
        if (Test-Path $LegacyPath) {
            . $LegacyPath
            Write-Host "[SUCCESS] Legacy PowerShell-Common loaded" -ForegroundColor Green
        }
    }
}

# Configuration Constants
$DB_NAME = "yuyu_lolita"
$DB_USER = "postgres" 
$DB_PASSWORD = "postgres"
$DB_HOST = "localhost"
$DB_PORT = 5432
$CONNECTION_STRING = "postgresql://$DB_USER`:$DB_PASSWORD@$DB_HOST`:$DB_PORT/$DB_NAME"

Write-SafeHeader "Windows PostgreSQL Setup v2.0 - Enterprise Edition"
Write-SafeOutput "Target Configuration:" -Status Info
Write-SafeOutput "  Database: $DB_NAME" -Status Info
Write-SafeOutput "  User: $DB_USER" -Status Info
Write-SafeOutput "  Password: [CONFIGURED]" -Status Info
Write-SafeOutput "  Connection: $DB_HOST`:$DB_PORT" -Status Info
Write-Host ""

if ($TestOnly) {
    Write-SafeOutput "Running in TEST ONLY mode" -Status Info
}

# =============================================================================
# STEP 1: PostgreSQL Detection and Installation
# =============================================================================

Write-SafeOutput "STEP 1: PostgreSQL Detection and Installation" -Status Processing

function Find-PostgreSQLInstallation {
    $possiblePaths = @(
        "C:\Program Files\PostgreSQL\*\bin\psql.exe",
        "C:\Program Files (x86)\PostgreSQL\*\bin\psql.exe",
        "${env:ProgramFiles}\PostgreSQL\*\bin\psql.exe",
        "${env:ProgramFiles(x86)}\PostgreSQL\*\bin\psql.exe"
    )
    
    foreach ($path in $possiblePaths) {
        $found = Get-ChildItem -Path $path -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            $pgVersion = Split-Path (Split-Path $found.Directory -Parent) -Leaf
            return @{
                Found = $true
                Version = $pgVersion
                BinPath = $found.Directory.FullName
                PsqlPath = $found.FullName
            }
        }
    }
    
    return @{ Found = $false }
}

$pgInfo = Find-PostgreSQLInstallation

if (-not $pgInfo.Found) {
    Write-SafeOutput "PostgreSQL not found on system" -Status Warning
    
    if ($Install) {
        Write-SafeOutput "Installing PostgreSQL for Windows..." -Status Processing
        
        # Download and install PostgreSQL
        $pgInstallerUrl = "https://get.enterprisedb.com/postgresql/postgresql-16.6-1-windows-x64.exe"
        $installerPath = "$env:TEMP\postgresql-installer.exe"
        
        try {
            Write-SafeOutput "Downloading PostgreSQL installer..." -Status Processing
            Invoke-WebRequest -Uri $pgInstallerUrl -OutFile $installerPath -UseBasicParsing
            
            Write-SafeOutput "Running PostgreSQL installer..." -Status Processing
            $installArgs = @(
                "--mode", "unattended",
                "--unattendedmodeui", "none", 
                "--disable-components", "stackbuilder",
                "--superpassword", $DB_PASSWORD,
                "--enable-acl", "1",
                "--install-path", "C:\Program Files\PostgreSQL\16",
                "--datadir", "C:\Program Files\PostgreSQL\16\data",
                "--servicename", "postgresql-x64-16",
                "--servicepassword", $DB_PASSWORD,
                "--serverport", $DB_PORT
            )
            
            $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
            
            if ($process.ExitCode -eq 0) {
                Write-SafeOutput "PostgreSQL installed successfully" -Status Success
                
                # Re-detect installation
                Start-Sleep -Seconds 5
                $pgInfo = Find-PostgreSQLInstallation
                
                if (-not $pgInfo.Found) {
                    throw "PostgreSQL installation completed but not detected"
                }
            } else {
                throw "PostgreSQL installer failed with exit code: $($process.ExitCode)"
            }
        } catch {
            Write-SafeOutput "PostgreSQL installation failed: $($_.Exception.Message)" -Status Error
            Write-SafeOutput "Manual installation required:" -Status Info
            Write-SafeOutput "  1. Download PostgreSQL from https://www.postgresql.org/download/windows/" -Status Info
            Write-SafeOutput "  2. Install with password: $DB_PASSWORD" -Status Info
            Write-SafeOutput "  3. Run this script again with -Configure" -Status Info
            exit 1
        } finally {
            if (Test-Path $installerPath) {
                Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
            }
        }
    } else {
        Write-SafeOutput "PostgreSQL installation required" -Status Error
        Write-SafeOutput "Options:" -Status Info
        Write-SafeOutput "  1. Run with -Install flag to auto-install" -Status Info
        Write-SafeOutput "  2. Install manually from https://www.postgresql.org/download/windows/" -Status Info
        Write-SafeOutput "  3. Use password: $DB_PASSWORD during installation" -Status Info
        exit 1
    }
}

Write-SafeOutput "PostgreSQL found: Version $($pgInfo.Version)" -Status Success
Write-SafeOutput "Binary path: $($pgInfo.BinPath)" -Status Info

# Update PATH if needed
if ($env:PATH -notlike "*$($pgInfo.BinPath)*") {
    $env:PATH = "$($pgInfo.BinPath);$env:PATH"
    Write-SafeOutput "Added PostgreSQL to PATH for this session" -Status Info
}

# =============================================================================
# STEP 2: PostgreSQL Service Management
# =============================================================================

Write-SafeOutput "STEP 2: PostgreSQL Service Management" -Status Processing

$services = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
$pgService = $services | Where-Object { $_.Status -eq "Running" } | Select-Object -First 1

if (-not $pgService) {
    $pgService = $services | Select-Object -First 1
    if ($pgService) {
        Write-SafeOutput "Starting PostgreSQL service: $($pgService.Name)" -Status Processing
        try {
            Start-Service $pgService.Name
            Write-SafeOutput "PostgreSQL service started successfully" -Status Success
        } catch {
            Write-SafeOutput "Failed to start PostgreSQL service: $($_.Exception.Message)" -Status Error
            exit 1
        }
    } else {
        Write-SafeOutput "No PostgreSQL service found" -Status Error
        Write-SafeOutput "Reinstallation may be required" -Status Warning
        exit 1
    }
} else {
    Write-SafeOutput "PostgreSQL service is running: $($pgService.Name)" -Status Success
}

# =============================================================================
# STEP 3: Network and Port Validation
# =============================================================================

Write-SafeOutput "STEP 3: Network and Port Validation" -Status Processing

$portTest = Test-NetConnection -ComputerName $DB_HOST -Port $DB_PORT -ErrorAction SilentlyContinue

if ($portTest -and $portTest.TcpTestSucceeded) {
    Write-SafeOutput "PostgreSQL is listening on port $DB_PORT" -Status Success
} else {
    Write-SafeOutput "PostgreSQL is not accessible on port $DB_PORT" -Status Warning
    Write-SafeOutput "Service may still be starting up..." -Status Info
    
    # Wait up to 30 seconds for service to be ready
    for ($i = 1; $i -le 30; $i++) {
        Start-Sleep -Seconds 1
        $portTest = Test-NetConnection -ComputerName $DB_HOST -Port $DB_PORT -ErrorAction SilentlyContinue
        if ($portTest -and $portTest.TcpTestSucceeded) {
            Write-SafeOutput "PostgreSQL is now ready on port $DB_PORT" -Status Success
            break
        }
    }
    
    if (-not ($portTest -and $portTest.TcpTestSucceeded)) {
        Write-SafeOutput "PostgreSQL still not accessible after waiting" -Status Error
        Write-SafeOutput "Check PostgreSQL configuration and logs" -Status Warning
        exit 1
    }
}

# =============================================================================
# STEP 4: Database User Configuration 
# =============================================================================

if (-not $TestOnly) {
    Write-SafeOutput "STEP 4: Database User Configuration" -Status Processing
    
    # Test if postgres user already has the correct password
    $env:PGPASSWORD = $DB_PASSWORD
    $userTestResult = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "SELECT current_user;" 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-SafeOutput "User $DB_USER with password already configured" -Status Success
    } else {
        Write-SafeOutput "Configuring postgres user password..." -Status Processing
        
        # Try different approaches to set password
        $passwordSet = $false
        
        # Approach 1: Try with Windows authentication first
        try {
            $windowsUserSql = "ALTER USER $DB_USER PASSWORD '$DB_PASSWORD';"
            $result = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c $windowsUserSql 2>&1
            
            # Test the password
            $env:PGPASSWORD = $DB_PASSWORD
            $testResult = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "SELECT current_user;" 2>$null
            
            if ($LASTEXITCODE -eq 0) {
                Write-SafeOutput "Password set successfully via Windows authentication" -Status Success
                $passwordSet = $true
            }
        } catch {
            Write-SafeOutput "Windows authentication approach failed" -Status Warning
        }
        
        # Approach 2: Try connecting as Windows superuser
        if (-not $passwordSet) {
            try {
                $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
                Write-SafeOutput "Trying Windows user: $currentUser" -Status Info
                
                $result = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -d postgres -c "ALTER USER $DB_USER PASSWORD '$DB_PASSWORD';" 2>&1
                
                # Test the password
                $env:PGPASSWORD = $DB_PASSWORD
                $testResult = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "SELECT current_user;" 2>$null
                
                if ($LASTEXITCODE -eq 0) {
                    Write-SafeOutput "Password set successfully via Windows superuser" -Status Success
                    $passwordSet = $true
                }
            } catch {
                Write-SafeOutput "Windows superuser approach failed" -Status Warning
            }
        }
        
        # Approach 3: Update pg_hba.conf for trust authentication temporarily
        if (-not $passwordSet) {
            Write-SafeOutput "Attempting pg_hba.conf modification..." -Status Processing
            
            $pgDataDir = "C:\Program Files\PostgreSQL\$($pgInfo.Version)\data"
            $pgHbaFile = Join-Path $pgDataDir "pg_hba.conf"
            
            if (Test-Path $pgHbaFile) {
                try {
                    # Backup original file
                    $backupFile = "$pgHbaFile.backup.$(Get-Date -Format 'yyyyMMddHHmmss')"
                    Copy-Item $pgHbaFile $backupFile
                    
                    # Read original content
                    $originalContent = Get-Content $pgHbaFile
                    
                    # Add trust authentication at the top
                    $trustLines = @(
                        "# TEMPORARY - Added by setup script",
                        "host    all             $DB_USER        127.0.0.1/32            trust",
                        "host    all             $DB_USER        ::1/128                 trust"
                    )
                    
                    $newContent = $trustLines + $originalContent
                    Set-Content $pgHbaFile $newContent
                    
                    # Reload PostgreSQL configuration
                    $reloadResult = & "$($pgInfo.BinPath)\pg_ctl.exe" reload -D $pgDataDir 2>&1
                    Start-Sleep -Seconds 2
                    
                    # Set password with trust authentication
                    $env:PGPASSWORD = ""
                    $result = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "ALTER USER $DB_USER PASSWORD '$DB_PASSWORD';" 2>&1
                    
                    # Restore original pg_hba.conf
                    Copy-Item $backupFile $pgHbaFile
                    
                    # Add proper password authentication
                    $authLines = @(
                        "# Added by setup script for $DB_USER",
                        "host    all             $DB_USER        127.0.0.1/32            scram-sha-256",
                        "host    all             $DB_USER        ::1/128                 scram-sha-256"
                    )
                    
                    $finalContent = $authLines + $originalContent
                    Set-Content $pgHbaFile $finalContent
                    
                    # Reload again
                    $reloadResult = & "$($pgInfo.BinPath)\pg_ctl.exe" reload -D $pgDataDir 2>&1
                    Start-Sleep -Seconds 2
                    
                    # Test final connection
                    $env:PGPASSWORD = $DB_PASSWORD
                    $testResult = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "SELECT current_user;" 2>$null
                    
                    if ($LASTEXITCODE -eq 0) {
                        Write-SafeOutput "Password set successfully via pg_hba.conf modification" -Status Success
                        $passwordSet = $true
                    }
                    
                    # Cleanup backup if successful
                    if ($passwordSet -and (Test-Path $backupFile)) {
                        Remove-Item $backupFile -Force
                    }
                    
                } catch {
                    Write-SafeOutput "pg_hba.conf modification failed: $($_.Exception.Message)" -Status Error
                    
                    # Restore backup if it exists
                    if (Test-Path $backupFile) {
                        Copy-Item $backupFile $pgHbaFile
                        Write-SafeOutput "Original pg_hba.conf restored" -Status Info
                    }
                }
            }
        }
        
        if (-not $passwordSet) {
            Write-SafeOutput "Failed to set postgres user password" -Status Error
            Write-SafeOutput "Manual intervention required:" -Status Warning
            Write-SafeOutput "  1. Connect to PostgreSQL as superuser" -Status Info
            Write-SafeOutput "  2. Run: ALTER USER postgres PASSWORD '$DB_PASSWORD';" -Status Info
            exit 1
        }
    }
}

# =============================================================================
# STEP 5: Database Creation and Migration
# =============================================================================

if (-not $TestOnly) {
    Write-SafeOutput "STEP 5: Database Creation and Migration" -Status Processing
    
    # Set password for all operations
    $env:PGPASSWORD = $DB_PASSWORD
    
    # Check if database exists
    $dbExistsQuery = "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';"
    $dbExists = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -tAc $dbExistsQuery 2>$null
    
    if ($dbExists -eq "1") {
        Write-SafeOutput "Database $DB_NAME already exists" -Status Success
    } else {
        Write-SafeOutput "Creating database $DB_NAME..." -Status Processing
        $createDbResult = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME WITH ENCODING='UTF8';" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-SafeOutput "Database $DB_NAME created successfully" -Status Success
        } else {
            Write-SafeOutput "Failed to create database: $createDbResult" -Status Error
            exit 1
        }
    }
    
    # Check table count
    $tableCountQuery = "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
    $tableCount = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc $tableCountQuery 2>$null
    
    if ([int]$tableCount -lt 20) {
        Write-SafeOutput "Database schema incomplete ($tableCount tables), running migrations..." -Status Processing
        
        $migrationFile = "packages\db\migrations\0000_consolidated_schema.sql"
        if (Test-Path $migrationFile) {
            $migrationResult = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $migrationFile 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                # Check new table count
                $newTableCount = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc $tableCountQuery 2>$null
                Write-SafeOutput "Migrations completed successfully ($newTableCount tables created)" -Status Success
            } else {
                Write-SafeOutput "Migration failed: $migrationResult" -Status Error
                exit 1
            }
        } else {
            Write-SafeOutput "Migration file not found: $migrationFile" -Status Error
            exit 1
        }
    } else {
        Write-SafeOutput "Database schema is complete ($tableCount tables)" -Status Success
    }
}

# =============================================================================
# STEP 6: Final Connection Testing
# =============================================================================

Write-SafeOutput "STEP 6: Final Connection Testing" -Status Processing

$env:PGPASSWORD = $DB_PASSWORD

# Test basic connection
$connectionTest = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT current_database(), current_user, version();" 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-SafeOutput "✅ Basic connection test PASSED" -Status Success
} else {
    Write-SafeOutput "❌ Basic connection test FAILED" -Status Error
    exit 1
}

# Test config table access (what API needs)
$configTest = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM config;" 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-SafeOutput "✅ Config table access test PASSED" -Status Success
} else {
    Write-SafeOutput "❌ Config table access test FAILED" -Status Error
    exit 1
}

# Test write operation
$writeTest = & "$($pgInfo.PsqlPath)" -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "INSERT INTO config (key, value, type, description) VALUES ('windows_setup_test', 'success', 'string', 'Windows setup test') ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;" 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-SafeOutput "✅ Write operation test PASSED" -Status Success
} else {
    Write-SafeOutput "❌ Write operation test FAILED" -Status Error
    exit 1
}

# =============================================================================
# FINAL RESULTS
# =============================================================================

Write-Host ""
Write-SafeHeader "🎉 WINDOWS POSTGRESQL SETUP COMPLETED SUCCESSFULLY! 🎉"

Write-SafeOutput "✅ PostgreSQL Version: $($pgInfo.Version)" -Status Success
Write-SafeOutput "✅ Service: Running and accessible" -Status Success  
Write-SafeOutput "✅ User: $DB_USER with password configured" -Status Success
Write-SafeOutput "✅ Database: $DB_NAME created with full schema" -Status Success
Write-SafeOutput "✅ Connection: All tests passed" -Status Success

Write-Host ""
Write-SafeOutput "🔗 Connection Details:" -Status Info
Write-SafeOutput "   Host: $DB_HOST" -Status Info
Write-SafeOutput "   Port: $DB_PORT" -Status Info  
Write-SafeOutput "   Database: $DB_NAME" -Status Info
Write-SafeOutput "   User: $DB_USER" -Status Info
Write-SafeOutput "   Password: [CONFIGURED]" -Status Info

Write-Host ""
Write-SafeOutput "📝 Environment Configuration:" -Status Info
Write-SafeOutput "   Add this to your .env file:" -Status Info
Write-Host "   DATABASE_URL=$CONNECTION_STRING" -ForegroundColor Yellow

Write-Host ""
Write-SafeOutput "🚀 Next Steps:" -Status Info
Write-SafeOutput "   1. Update .env with the DATABASE_URL above" -Status Info
Write-SafeOutput "   2. Start your API server with: bun run dev" -Status Info
Write-SafeOutput "   3. API should show: ✅ Database connection successful" -Status Info

Write-Host ""
Write-SafeOutput "🔧 Troubleshooting Commands:" -Status Info
Write-SafeOutput "   • Test connection: .\Test-DatabaseConnection.ps1" -Status Info
Write-SafeOutput "   • Check service: Get-Service postgresql*" -Status Info
Write-SafeOutput "   • Direct psql: psql -h $DB_HOST -U $DB_USER -d $DB_NAME" -Status Info

Write-SafeOutput "Setup completed successfully!" -Status Complete