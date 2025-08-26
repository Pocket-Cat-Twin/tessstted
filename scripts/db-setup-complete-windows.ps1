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
    Write-Host "🚀 =================================================" -ForegroundColor Magenta
    Write-Host "🚀 ПОЛНАЯ ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ (WINDOWS)" -ForegroundColor Magenta
    Write-Host "🚀 YuYu Lolita Shopping System" -ForegroundColor Magenta  
    Write-Host "🚀 MySQL8 + Автоматическое создание пользователей" -ForegroundColor Magenta
    Write-Host "🚀 =================================================" -ForegroundColor Magenta
    Write-Host ""
}

function Invoke-EnvironmentCheck {
    Write-Host "🔍 [PHASE 1] Проверка окружения Windows..." -ForegroundColor Cyan
    Write-Host ""
    
    $checkScript = Join-Path $PSScriptRoot "db-environment-check-windows.ps1"
    
    if (-not (Test-Path $checkScript)) {
        Write-Host "❌ [ERROR] Скрипт проверки окружения не найден!" -ForegroundColor Red
        return $false
    }
    
    try {
        $result = & powershell -ExecutionPolicy Bypass -File $checkScript -Fix
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ [SUCCESS] Проверка окружения завершена успешно!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ [ERROR] Проверка окружения не пройдена!" -ForegroundColor Red
            Write-Host "💡 [SOLUTION] Исправьте проблемы и запустите заново" -ForegroundColor Yellow
            return $false
        }
    }
    catch {
        Write-Host "❌ [ERROR] Ошибка при проверке окружения: $_" -ForegroundColor Red
        return $false
    }
}

function Invoke-DatabaseMigrations {
    Write-Host ""
    Write-Host "🔍 [PHASE 2] Запуск миграций базы данных..." -ForegroundColor Cyan
    Write-Host ""
    
    $projectRoot = Split-Path $PSScriptRoot -Parent
    $dbPackagePath = Join-Path $projectRoot "packages\db"
    
    if (-not (Test-Path $dbPackagePath)) {
        Write-Host "❌ [ERROR] Пакет базы данных не найден по пути: $dbPackagePath" -ForegroundColor Red
        return $false
    }
    
    try {
        Push-Location $dbPackagePath
        
        Write-Host "📦 [INFO] Переходим в директорию: $dbPackagePath" -ForegroundColor Blue
        Write-Host "🔧 [INFO] Запускаем миграции через bun..." -ForegroundColor Blue
        
        # Проверяем наличие bun
        $bunPath = Get-Command bun -ErrorAction SilentlyContinue
        if (-not $bunPath) {
            Write-Host "❌ [ERROR] Bun не найден в системе!" -ForegroundColor Red
            Write-Host "💡 [SOLUTION] Установите Bun: https://bun.sh/docs/installation" -ForegroundColor Yellow
            return $false
        }
        
        # Запускаем миграции
        Write-Host "▶️ [EXECUTE] bun run migrate:windows" -ForegroundColor Green
        & bun run migrate:windows
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ [SUCCESS] Миграции выполнены успешно!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ [ERROR] Ошибка при выполнении миграций!" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ [ERROR] Исключение при выполнении миграций: $_" -ForegroundColor Red
        return $false
    }
    finally {
        Pop-Location
    }
}

function Invoke-UserSeed {
    Write-Host ""
    Write-Host "🔍 [PHASE 3] Создание начальных пользователей..." -ForegroundColor Cyan
    Write-Host ""
    
    $projectRoot = Split-Path $PSScriptRoot -Parent
    $dbPackagePath = Join-Path $projectRoot "packages\db"
    
    try {
        Push-Location $dbPackagePath
        
        Write-Host "👥 [INFO] Создаем админа и тестовых пользователей..." -ForegroundColor Blue
        
        # Проверим, есть ли скрипт seed
        $seedScript = Join-Path $dbPackagePath "src\seed-users.ts"
        if (-not (Test-Path $seedScript)) {
            Write-Host "❌ [ERROR] Скрипт создания пользователей не найден по пути: $seedScript" -ForegroundColor Red
            Write-Host "💡 [SOLUTION] Убедитесь, что файл packages/db/src/seed-users.ts существует" -ForegroundColor Yellow
            return $false
        }
        
        Write-Host "▶️ [EXECUTE] bun run src/seed-users.ts" -ForegroundColor Green
        & bun run src/seed-users.ts
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ [SUCCESS] Пользователи созданы успешно!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ [ERROR] Ошибка при создании пользователей!" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ [ERROR] Исключение при создании пользователей: $_" -ForegroundColor Red
        return $false
    }
    finally {
        Pop-Location
    }
}

function Invoke-FinalHealthCheck {
    Write-Host ""
    Write-Host "🔍 [PHASE 4] Финальная проверка работоспособности..." -ForegroundColor Cyan
    Write-Host ""
    
    $projectRoot = Split-Path $PSScriptRoot -Parent
    $dbPackagePath = Join-Path $projectRoot "packages\db"
    
    try {
        Push-Location $dbPackagePath
        
        Write-Host "🏥 [INFO] Запускаем health check..." -ForegroundColor Blue
        
        Write-Host "▶️ [EXECUTE] bun run health:mysql" -ForegroundColor Green
        & bun run health:mysql
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ [SUCCESS] Health check пройден успешно!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ [ERROR] Health check не пройден!" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ [ERROR] Ошибка при health check: $_" -ForegroundColor Red
        return $false
    }
    finally {
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
    $phases += @{ Name = "Проверка окружения"; Result = (Invoke-EnvironmentCheck) }
} else {
    Write-Host "⏭️ [SKIP] Проверка окружения пропущена по запросу" -ForegroundColor Yellow
    $phases += @{ Name = "Проверка окружения"; Result = $true }
}

# Phase 2: Database Migrations
if ($phases[-1].Result -or $Force) {
    $phases += @{ Name = "Миграции БД"; Result = (Invoke-DatabaseMigrations) }
} else {
    Write-Host "⏭️ [SKIP] Миграции пропущены из-за ошибок в предыдущих этапах" -ForegroundColor Yellow
    $phases += @{ Name = "Миграции БД"; Result = $false }
}

# Phase 3: User Seed
if ($phases[-1].Result -or $Force) {
    $phases += @{ Name = "Создание пользователей"; Result = (Invoke-UserSeed) }
} else {
    Write-Host "⏭️ [SKIP] Создание пользователей пропущено из-за ошибок" -ForegroundColor Yellow
    $phases += @{ Name = "Создание пользователей"; Result = $false }
}

# Phase 4: Final Health Check
if ($phases[-1].Result -or $Force) {
    $phases += @{ Name = "Финальная проверка"; Result = (Invoke-FinalHealthCheck) }
} else {
    Write-Host "⏭️ [SKIP] Финальная проверка пропущена" -ForegroundColor Yellow
    $phases += @{ Name = "Финальная проверка"; Result = $false }
}

# Summary
Write-Host ""
Write-Host "📊 =================================================" -ForegroundColor Magenta
Write-Host "📊 ИТОГИ ПОЛНОЙ ИНИЦИАЛИЗАЦИИ БД" -ForegroundColor Magenta
Write-Host "📊 =================================================" -ForegroundColor Magenta

$successfulPhases = 0
foreach ($phase in $phases) {
    $status = if ($phase.Result) { "✅ УСПЕШНО" } else { "❌ ОШИБКА" }
    $color = if ($phase.Result) { "Green" } else { "Red" }
    Write-Host "$status - $($phase.Name)" -ForegroundColor $color
    if ($phase.Result) { $successfulPhases++ }
}

Write-Host ""
Write-Host "📈 Успешно завершено: $successfulPhases из $($phases.Count) этапов" -ForegroundColor Cyan

if ($successfulPhases -eq $phases.Count) {
    Write-Host ""
    Write-Host "🎉 [SUCCESS] Полная инициализация завершена успешно!" -ForegroundColor Green
    Write-Host "🚀 [NEXT] База данных готова к использованию!" -ForegroundColor Green
    Write-Host "💡 [INFO] Запустите: npm run dev для старта приложения" -ForegroundColor Yellow
    Write-Host ""
    exit 0
} else {
    Write-Host ""
    Write-Host "❌ [ERROR] Инициализация завершена с ошибками!" -ForegroundColor Red
    Write-Host "💡 [TIP] Проверьте логи и исправьте проблемы" -ForegroundColor Yellow
    if (-not $Force) {
        Write-Host "💡 [TIP] Используйте -Force для принудительного выполнения всех этапов" -ForegroundColor Yellow
    }
    Write-Host ""
    exit 1
}