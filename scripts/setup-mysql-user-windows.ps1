# ================================
# MySQL User Setup for Windows
# YuYu Lolita Shopping System
# Automated security-focused user creation
# ================================

[CmdletBinding()]
param(
    [string]$MySQLRootPassword = "",
    [string]$NewUserPassword = "",
    [string]$NewUserName = "yuyu_app",
    [string]$DatabaseName = "yuyu_lolita",
    [switch]$GeneratePassword = $false,
    [switch]$UpdateEnvFile = $true,
    [switch]$TestConnection = $true
)

# Import common functions
$commonLibPath = Join-Path $PSScriptRoot "PowerShell-Common.ps1"
if (-not (Test-Path $commonLibPath)) {
    Write-Error "Required PowerShell-Common.ps1 not found at: $commonLibPath"
    exit 1
}
. $commonLibPath

# ==============================================================================
# MYSQL USER SETUP FUNCTIONS
# ==============================================================================

function Generate-SecurePassword {
    <#
    .SYNOPSIS
    Generates a secure password for MySQL user - STANDARDIZED VERSION
    Uses the same algorithm as the centralized user-generator.ts
    #>
    param([int]$Length = 16)
    
    $charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*'
    $password = ''
    
    # Ensure at least one character from each required type (matching TypeScript version)
    $password += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[(Get-Random -Maximum 26)] # uppercase
    $password += 'abcdefghijklmnopqrstuvwxyz'[(Get-Random -Maximum 26)] # lowercase
    $password += '0123456789'[(Get-Random -Maximum 10)] # digit
    $password += '!@#$%^&*'[(Get-Random -Maximum 8)] # special
    
    # Fill the rest randomly
    for ($i = 4; $i -lt $Length; $i++) {
        $password += $charset[(Get-Random -Maximum $charset.Length)]
    }
    
    # Shuffle the password (matching TypeScript version)
    $shuffled = ($password.ToCharArray() | Sort-Object {Get-Random}) -join ''
    return $shuffled
}

function Save-DatabaseCredentials {
    <#
    .SYNOPSIS
    Saves database user credentials to credentials.txt file
    #>
    param(
        [string]$Email,
        [string]$Password,
        [string]$Role = "database",
        [string]$Method = "mysql_setup"
    )
    
    $credentialsPath = "credentials.txt"
    $timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    
    # Create header if file doesn't exist
    if (-not (Test-Path $credentialsPath)) {
        $header = @"
# YuYu Lolita Shopping System - User Credentials
# ВНИМАНИЕ: Этот файл содержит нешифрованные пароли!
# Держите его в безопасности и не коммитьте в git
# Format: TIMESTAMP | EMAIL | PASSWORD | ROLE | METHOD | NAME

"@
        $header | Out-File -FilePath $credentialsPath -Encoding UTF8
    }
    
    # Append credentials entry
    $logEntry = "$timestamp | $Email | $Password | $Role | $Method | MySQL Database User"
    $logEntry | Out-File -FilePath $credentialsPath -Encoding UTF8 -Append
    
    Write-SafeOutput "Credentials saved to $credentialsPath" -Status Success
}

function Test-MySQLConnection {
    <#
    .SYNOPSIS
    Tests MySQL connection with provided credentials
    #>
    param(
        [string]$User,
        [string]$Password,
        [string]$Database = "",
        [string]$Host = "localhost",
        [int]$Port = 3306
    )
    
    $mysqlPath = Get-Command mysql.exe -ErrorAction SilentlyContinue
    if (-not $mysqlPath) {
        Write-SafeOutput "MySQL client not found in PATH" -Status Error
        return $false
    }
    
    $connectionArgs = @(
        "--host=$Host",
        "--port=$Port", 
        "--user=$User",
        "--password=$Password"
    )
    
    if ($Database) {
        $connectionArgs += "--database=$Database"
    }
    
    $connectionArgs += @(
        "--execute=SELECT 1 as test;",
        "--batch",
        "--silent"
    )
    
    try {
        $result = & mysql.exe $connectionArgs 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $true
        } else {
            Write-SafeOutput "Connection test failed: $result" -Status Error
            return $false
        }
    } catch {
        Write-SafeOutput "Connection test error: $($_.Exception.Message)" -Status Error
        return $false
    }
}

function Create-MySQLUser {
    <#
    .SYNOPSIS
    Creates MySQL application user with proper permissions
    #>
    param(
        [string]$RootPassword,
        [string]$NewUser,
        [string]$NewPassword,
        [string]$Database
    )
    
    $mysqlPath = Get-Command mysql.exe -ErrorAction SilentlyContinue
    if (-not $mysqlPath) {
        Write-SafeOutput "MySQL client not found in PATH" -Status Error
        return $false
    }
    
    Write-SafeOutput "Creating MySQL user '$NewUser'..." -Status Processing
    
    $sqlCommands = @"
-- Drop user if exists
DROP USER IF EXISTS '$NewUser'@'localhost';

-- Create application user
CREATE USER '$NewUser'@'localhost' IDENTIFIED BY '$NewPassword';

-- Grant database privileges
GRANT SELECT, INSERT, UPDATE, DELETE ON $Database.* TO '$NewUser'@'localhost';
GRANT CREATE, ALTER, INDEX, DROP ON $Database.* TO '$NewUser'@'localhost';
GRANT EXECUTE ON $Database.* TO '$NewUser'@'localhost';
GRANT CREATE ON *.* TO '$NewUser'@'localhost';
GRANT LOCK TABLES ON $Database.* TO '$NewUser'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;

-- Verify creation
SELECT 'User created successfully' as result;
"@
    
    $tempSqlFile = [System.IO.Path]::GetTempFileName() + ".sql"
    $sqlCommands | Out-File -FilePath $tempSqlFile -Encoding UTF8
    
    try {
        $mysqlArgs = @(
            "--host=localhost",
            "--port=3306",
            "--user=root",
            "--password=$RootPassword",
            "--batch",
            "--execute=source $tempSqlFile"
        )
        
        $result = & mysql.exe $mysqlArgs 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-SafeOutput "MySQL user '$NewUser' created successfully" -Status Success
            return $true
        } else {
            Write-SafeOutput "Failed to create MySQL user: $result" -Status Error
            return $false
        }
        
    } catch {
        Write-SafeOutput "Error creating MySQL user: $($_.Exception.Message)" -Status Error
        return $false
    } finally {
        if (Test-Path $tempSqlFile) {
            Remove-Item $tempSqlFile -Force
        }
    }
}

function Update-EnvironmentFile {
    <#
    .SYNOPSIS
    Updates .env file with new database credentials
    #>
    param(
        [string]$User,
        [string]$Password
    )
    
    $envPath = ".env"
    if (-not (Test-Path $envPath)) {
        Write-SafeOutput ".env file not found, creating new one..." -Status Warning
        Copy-Item ".env.example" $envPath -ErrorAction SilentlyContinue
    }
    
    if (-not (Test-Path $envPath)) {
        Write-SafeOutput ".env file not found and .env.example not available" -Status Error
        return $false
    }
    
    Write-SafeOutput "Updating .env file with new credentials..." -Status Processing
    
    $envContent = Get-Content $envPath
    $updatedContent = @()
    $userUpdated = $false
    $passwordUpdated = $false
    
    foreach ($line in $envContent) {
        if ($line -match "^DB_USER=") {
            $updatedContent += "DB_USER=$User"
            $userUpdated = $true
        } elseif ($line -match "^DB_PASSWORD=") {
            $updatedContent += "DB_PASSWORD=$Password"
            $passwordUpdated = $true
        } else {
            $updatedContent += $line
        }
    }
    
    # Add missing entries if not found
    if (-not $userUpdated) {
        $updatedContent += "DB_USER=$User"
    }
    if (-not $passwordUpdated) {
        $updatedContent += "DB_PASSWORD=$Password"
    }
    
    try {
        $updatedContent | Out-File -FilePath $envPath -Encoding UTF8
        Write-SafeOutput ".env file updated successfully" -Status Success
        return $true
    } catch {
        Write-SafeOutput "Failed to update .env file: $($_.Exception.Message)" -Status Error
        return $false
    }
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

function Invoke-MySQLUserSetup {
    Write-SafeHeader "MySQL User Setup for Windows"
    Write-SafeOutput "YuYu Lolita Shopping System - Security Configuration" -Status Info
    Write-Host ""
    
    # Step 1: Get MySQL root password
    if (-not $MySQLRootPassword) {
        $secureRootPassword = Read-Host "Enter MySQL root password" -AsSecureString
        $MySQLRootPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureRootPassword))
    }
    
    # Step 2: Generate or get user password
    if ($GeneratePassword -or -not $NewUserPassword) {
        $NewUserPassword = Generate-SecurePassword -Length 16
        Write-SafeOutput "Generated secure password for user '$NewUserName'" -Status Success
    }
    
    # Step 3: Test root connection
    Write-SafeSectionHeader "Testing MySQL Root Connection" -Step 1
    $rootConnectionOk = Test-MySQLConnection -User "root" -Password $MySQLRootPassword
    
    if (-not $rootConnectionOk) {
        Write-SafeOutput "Cannot connect to MySQL as root" -Status Error
        Write-SafeOutput "Please verify MySQL is running and root password is correct" -Status Info
        exit 1
    }
    
    Write-SafeOutput "MySQL root connection verified" -Status Success
    
    # Step 4: Create application user
    Write-SafeSectionHeader "Creating Application User" -Step 2
    $userCreated = Create-MySQLUser -RootPassword $MySQLRootPassword -NewUser $NewUserName -NewPassword $NewUserPassword -Database $DatabaseName
    
    if (-not $userCreated) {
        Write-SafeOutput "Failed to create MySQL user" -Status Error
        exit 1
    }
    
    # Step 5: Test new user connection
    if ($TestConnection) {
        Write-SafeSectionHeader "Testing New User Connection" -Step 3
        $userConnectionOk = Test-MySQLConnection -User $NewUserName -Password $NewUserPassword
        
        if (-not $userConnectionOk) {
            Write-SafeOutput "New user connection test failed" -Status Error
            Write-SafeOutput "User was created but cannot connect" -Status Warning
        } else {
            Write-SafeOutput "New user connection verified" -Status Success
        }
    }
    
    # Step 6: Update .env file
    if ($UpdateEnvFile) {
        Write-SafeSectionHeader "Updating Environment Configuration" -Step 4
        $envUpdated = Update-EnvironmentFile -User $NewUserName -Password $NewUserPassword
        
        if ($envUpdated) {
            Write-SafeOutput "Environment file updated with new credentials" -Status Success
        }
    }
    
    # Step 7: Save credentials to credentials.txt
    Write-SafeSectionHeader "Saving Database Credentials" -Step 5
    Save-DatabaseCredentials -Email "$NewUserName@localhost" -Password $NewUserPassword -Role "database" -Method "mysql_setup"
    
    # Step 8: Display results
    Write-Host ""
    Write-SafeHeader "MySQL User Setup Complete"
    Write-SafeOutput "Username: $NewUserName" -Status Info
    Write-SafeOutput "Password: $('*' * $NewUserPassword.Length) (hidden)" -Status Info
    Write-SafeOutput "Database: $DatabaseName" -Status Info
    Write-SafeOutput "Credentials saved to: credentials.txt" -Status Success
    
    if ($GeneratePassword) {
        Write-Host ""
        Write-SafeOutput "IMPORTANT: Password saved to credentials.txt!" -Status Warning
        Write-SafeOutput "Generated Password: $NewUserPassword" -Status Complete
    }
    
    Write-Host ""
    Write-SafeOutput "Next Steps:" -Status Info
    Write-SafeOutput "1. Test database connection: npm run db:health:mysql" -Status Info
    Write-SafeOutput "2. Run database migrations: npm run db:migrate:windows" -Status Info
    Write-SafeOutput "3. Seed initial data: npm run db:seed:windows" -Status Info
}

# ==============================================================================
# SCRIPT ENTRY POINT
# ==============================================================================

try {
    Invoke-MySQLUserSetup
    exit 0
} catch {
    Write-SafeOutput "Critical error during MySQL user setup: $($_.Exception.Message)" -Status Error
    Write-SafeOutput "Please check MySQL installation and permissions" -Status Info
    exit 1
}