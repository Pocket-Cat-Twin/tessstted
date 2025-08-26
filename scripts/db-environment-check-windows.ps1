# ================================
# MySQL8 Environment Checker for Windows
# YuYu Lolita Shopping System
# ================================

[CmdletBinding()]
param(
    [switch]$Verbose = $false,
    [switch]$Fix = $false
)

# Import common functions
. "$PSScriptRoot\PowerShell-Common.ps1"

function Test-MySQLService {
    Write-Host "🔍 [CHECK] Проверяю службу MySQL80..." -ForegroundColor Cyan
    
    $mysqlService = Get-Service -Name "MySQL80" -ErrorAction SilentlyContinue
    
    if (-not $mysqlService) {
        Write-Host "❌ [ERROR] Служба MySQL80 не найдена!" -ForegroundColor Red
        Write-Host "💡 [SOLUTION] Установите MySQL 8.0 из: https://dev.mysql.com/downloads/mysql/" -ForegroundColor Yellow
        return $false
    }
    
    if ($mysqlService.Status -ne "Running") {
        Write-Host "⚠️ [WARNING] Служба MySQL80 не запущена. Статус: $($mysqlService.Status)" -ForegroundColor Yellow
        
        if ($Fix) {
            Write-Host "🔧 [FIX] Пытаюсь запустить службу MySQL80..." -ForegroundColor Green
            try {
                Start-Service -Name "MySQL80"
                Start-Sleep -Seconds 3
                $mysqlService = Get-Service -Name "MySQL80"
                if ($mysqlService.Status -eq "Running") {
                    Write-Host "✅ [SUCCESS] Служба MySQL80 успешно запущена!" -ForegroundColor Green
                    return $true
                }
            }
            catch {
                Write-Host "❌ [ERROR] Не удалось запустить службу MySQL80: $_" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "💡 [SOLUTION] Запустите: Start-Service -Name 'MySQL80'" -ForegroundColor Yellow
            return $false
        }
    }
    
    Write-Host "✅ [SUCCESS] Служба MySQL80 работает корректно" -ForegroundColor Green
    return $true
}

function Test-MySQLPort {
    Write-Host "🔍 [CHECK] Проверяю доступность порта 3306..." -ForegroundColor Cyan
    
    try {
        $connection = Test-NetConnection -ComputerName "localhost" -Port 3306 -InformationLevel Quiet
        if ($connection) {
            Write-Host "✅ [SUCCESS] Порт 3306 доступен для подключения" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ [ERROR] Порт 3306 недоступен!" -ForegroundColor Red
            Write-Host "💡 [SOLUTION] Проверьте конфигурацию MySQL и firewall" -ForegroundColor Yellow
            return $false
        }
    }
    catch {
        Write-Host "❌ [ERROR] Ошибка при проверке порта 3306: $_" -ForegroundColor Red
        return $false
    }
}

function Test-EnvFile {
    Write-Host "🔍 [CHECK] Проверяю файл .env..." -ForegroundColor Cyan
    
    $envPath = Join-Path $PSScriptRoot "..\.env"
    
    if (-not (Test-Path $envPath)) {
        Write-Host "❌ [ERROR] Файл .env не найден!" -ForegroundColor Red
        
        if ($Fix) {
            Write-Host "🔧 [FIX] Копирую .env.example в .env..." -ForegroundColor Green
            $envExamplePath = Join-Path $PSScriptRoot "..\.env.example"
            if (Test-Path $envExamplePath) {
                Copy-Item $envExamplePath $envPath
                Write-Host "✅ [SUCCESS] Файл .env создан из шаблона" -ForegroundColor Green
                Write-Host "⚠️ [WARNING] Необходимо настроить DB_PASSWORD в .env!" -ForegroundColor Yellow
            } else {
                Write-Host "❌ [ERROR] Шаблон .env.example не найден!" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "💡 [SOLUTION] Скопируйте .env.example в .env и настройте параметры БД" -ForegroundColor Yellow
            return $false
        }
    }
    
    # Проверяем ключевые параметры
    $envContent = Get-Content $envPath -Raw
    $requiredVars = @("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    $missingVars = @()
    
    foreach ($var in $requiredVars) {
        if (-not ($envContent -match "$var\s*=\s*.+")) {
            $missingVars += $var
        }
    }
    
    if ($missingVars.Count -gt 0) {
        Write-Host "❌ [ERROR] В файле .env отсутствуют или пусты параметры: $($missingVars -join ', ')" -ForegroundColor Red
        Write-Host "💡 [SOLUTION] Заполните эти параметры в файле .env" -ForegroundColor Yellow
        return $false
    }
    
    Write-Host "✅ [SUCCESS] Файл .env содержит все необходимые параметры" -ForegroundColor Green
    return $true
}

function Test-MySQLConnection {
    Write-Host "🔍 [CHECK] Проверяю подключение к MySQL..." -ForegroundColor Cyan
    
    # Загружаем переменные окружения
    $envPath = Join-Path $PSScriptRoot "..\.env"
    if (Test-Path $envPath) {
        $envVars = @{}
        Get-Content $envPath | ForEach-Object {
            if ($_ -match '^([^#][^=]+)=(.*)$') {
                $envVars[$matches[1].Trim()] = $matches[2].Trim()
            }
        }
    } else {
        Write-Host "❌ [ERROR] Файл .env не найден для проверки подключения!" -ForegroundColor Red
        return $false
    }
    
    $dbHost = $envVars["DB_HOST"] ?? "localhost"
    $dbPort = $envVars["DB_PORT"] ?? "3306"
    $dbUser = $envVars["DB_USER"] ?? "root"
    $dbPassword = $envVars["DB_PASSWORD"] ?? ""
    
    if ([string]::IsNullOrEmpty($dbPassword)) {
        Write-Host "❌ [ERROR] DB_PASSWORD не задан в .env файле!" -ForegroundColor Red
        Write-Host "💡 [SOLUTION] Установите DB_PASSWORD в файле .env" -ForegroundColor Yellow
        return $false
    }
    
    # Пытаемся подключиться через mysql.exe
    $mysqlPath = Get-Command mysql -ErrorAction SilentlyContinue
    if ($mysqlPath) {
        try {
            $testQuery = "SELECT 1;"
            $result = & mysql -h $dbHost -P $dbPort -u $dbUser -p$dbPassword -e $testQuery --silent 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ [SUCCESS] Подключение к MySQL успешно установлено" -ForegroundColor Green
                return $true
            } else {
                Write-Host "❌ [ERROR] Не удалось подключиться к MySQL" -ForegroundColor Red
                Write-Host "💡 [SOLUTION] Проверьте логин/пароль MySQL" -ForegroundColor Yellow
                return $false
            }
        }
        catch {
            Write-Host "❌ [ERROR] Ошибка подключения к MySQL: $_" -ForegroundColor Red
            return $false
        }
    } else {
        Write-Host "⚠️ [WARNING] Клиент mysql.exe не найден в PATH" -ForegroundColor Yellow
        Write-Host "💡 [INFO] Проверка подключения пропущена" -ForegroundColor Yellow
        return $true
    }
}

function Test-DatabaseExists {
    param([string]$DatabaseName = "yuyu_lolita")
    
    Write-Host "🔍 [CHECK] Проверяю существование базы данных '$DatabaseName'..." -ForegroundColor Cyan
    
    $envPath = Join-Path $PSScriptRoot "..\.env"
    if (-not (Test-Path $envPath)) {
        Write-Host "❌ [ERROR] Файл .env не найден!" -ForegroundColor Red
        return $false
    }
    
    $envVars = @{}
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $envVars[$matches[1].Trim()] = $matches[2].Trim()
        }
    }
    
    $dbHost = $envVars["DB_HOST"] ?? "localhost"
    $dbPort = $envVars["DB_PORT"] ?? "3306"
    $dbUser = $envVars["DB_USER"] ?? "root"
    $dbPassword = $envVars["DB_PASSWORD"] ?? ""
    
    $mysqlPath = Get-Command mysql -ErrorAction SilentlyContinue
    if ($mysqlPath) {
        try {
            $testQuery = "SHOW DATABASES LIKE '$DatabaseName';"
            $result = & mysql -h $dbHost -P $dbPort -u $dbUser -p$dbPassword -e $testQuery --silent 2>$null
            if ($LASTEXITCODE -eq 0 -and $result -like "*$DatabaseName*") {
                Write-Host "✅ [SUCCESS] База данных '$DatabaseName' существует" -ForegroundColor Green
                return $true
            } else {
                Write-Host "⚠️ [WARNING] База данных '$DatabaseName' не существует" -ForegroundColor Yellow
                return $false
            }
        }
        catch {
            Write-Host "❌ [ERROR] Ошибка при проверке базы данных: $_" -ForegroundColor Red
            return $false
        }
    } else {
        Write-Host "⚠️ [WARNING] Клиент mysql.exe не найден, пропускаю проверку БД" -ForegroundColor Yellow
        return $true
    }
}

# ================================
# MAIN EXECUTION
# ================================

Write-Host ""
Write-Host "🚀 =====================================" -ForegroundColor Magenta
Write-Host "🚀 MySQL8 Environment Checker (Windows)" -ForegroundColor Magenta
Write-Host "🚀 YuYu Lolita Shopping System" -ForegroundColor Magenta
Write-Host "🚀 =====================================" -ForegroundColor Magenta
Write-Host ""

$allChecks = @()

# Проверка службы MySQL
$allChecks += Test-MySQLService

# Проверка порта
$allChecks += Test-MySQLPort

# Проверка .env файла
$allChecks += Test-EnvFile

# Проверка подключения к MySQL
$allChecks += Test-MySQLConnection

# Проверка существования БД
$allChecks += Test-DatabaseExists

# Подводим итоги
Write-Host ""
Write-Host "📊 =====================================" -ForegroundColor Magenta
Write-Host "📊 ИТОГИ ПРОВЕРКИ ОКРУЖЕНИЯ" -ForegroundColor Magenta
Write-Host "📊 =====================================" -ForegroundColor Magenta

$passedChecks = ($allChecks | Where-Object { $_ -eq $true }).Count
$totalChecks = $allChecks.Count

Write-Host "✅ Пройдено проверок: $passedChecks из $totalChecks" -ForegroundColor Green

if ($passedChecks -eq $totalChecks) {
    Write-Host "🎉 [SUCCESS] Все проверки пройдены! Окружение готово к работе." -ForegroundColor Green
    Write-Host "💡 [NEXT] Запустите: npm run db:setup:windows для инициализации БД" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "❌ [ERROR] Некоторые проверки не пройдены. Исправьте проблемы." -ForegroundColor Red
    if (-not $Fix) {
        Write-Host "💡 [TIP] Запустите с параметром -Fix для автоматического исправления" -ForegroundColor Yellow
    }
    exit 1
}