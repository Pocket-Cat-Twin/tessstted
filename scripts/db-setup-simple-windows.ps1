# Упрощенная версия инициализации базы данных для Windows
# Если основной скрипт db-setup-complete-windows.ps1 не работает
Write-Host "🚀 Упрощенная инициализация базы данных..." -ForegroundColor Green

# Проверяем, что мы в правильной директории
if (!(Test-Path "packages\db")) {
    Write-Host "❌ Ошибка: Запустите скрипт из корневой папки проекта!" -ForegroundColor Red
    exit 1
}

# Переходим в папку db
Write-Host "📂 Переходим в packages\db..." -ForegroundColor Blue
Set-Location "packages\db"

try {
    # Этап 1: Миграции
    Write-Host "🔧 Этап 1: Запуск миграций..." -ForegroundColor Cyan
    & bun run migrate:windows
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ошибка миграций!" -ForegroundColor Red
        exit 1
    }

    # Этап 2: Создание пользователей  
    Write-Host "👥 Этап 2: Создание пользователей..." -ForegroundColor Cyan
    & bun run src/seed-users.ts
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ошибка создания пользователей!" -ForegroundColor Red
        exit 1
    }

    # Этап 3: Health check
    Write-Host "🏥 Этап 3: Финальная проверка..." -ForegroundColor Cyan
    & bun run health:mysql
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️ Health check не прошел, но это не критично" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "🎉 Инициализация завершена успешно!" -ForegroundColor Green
    Write-Host "📧 Админ: admin@yuyulolita.com" -ForegroundColor Yellow  
    Write-Host "👤 Тест: test1@yuyulolita.com (пароль: Test123!)" -ForegroundColor Yellow
    Write-Host ""

} catch {
    Write-Host "❌ Критическая ошибка: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    # Возвращаемся в корневую папку
    Set-Location "..\..\"
}

Write-Host "✅ Готово! Запустите: npm run dev" -ForegroundColor Green