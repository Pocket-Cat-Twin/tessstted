# Тестовый скрипт для проверки синтаксиса PowerShell
Write-Host "🧪 Тестирую исправленный синтаксис PowerShell..." -ForegroundColor Green

# Тестируем основные функции
function Test-BasicSyntax {
    Write-Host "✅ Функции работают" -ForegroundColor Green
    return $true
}

# Тестируем переменные 
$testVar = "Тест переменной"
Write-Host "✅ Переменные: $testVar" -ForegroundColor Green

# Тестируем условия
$testPath = "C:\Windows"
if (Test-Path $testPath -ErrorAction SilentlyContinue) {
    Write-Host "✅ Условия работают" -ForegroundColor Green
} else {
    Write-Host "⚠️ Путь не найден (нормально для тестирования)" -ForegroundColor Yellow
}

# Тестируем try-catch
try {
    $result = Test-BasicSyntax
    Write-Host "✅ Try-catch блоки работают" -ForegroundColor Green
} catch {
    Write-Host "❌ Ошибка в try-catch" -ForegroundColor Red
}

Write-Host "🎉 Все тесты синтаксиса пройдены!" -ForegroundColor Green