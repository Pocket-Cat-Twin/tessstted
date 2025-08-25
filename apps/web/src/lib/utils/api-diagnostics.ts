// Утилиты для диагностики API конфигурации в development режиме
import { api } from '../api/client-simple';
import { API_CONFIG } from '../config';

/**
 * Запуск полной диагностики API системы
 * Используется для отладки проблем с подключением
 */
export async function runApiDiagnostics(): Promise<void> {
  console.log("🔬 === ПОЛНАЯ ДИАГНОСТИКА API СИСТЕМЫ ===");
  
  try {
    const diagnostics = await api.runFullDiagnostics();
    
    console.log("📊 РЕЗУЛЬТАТЫ ДИАГНОСТИКИ:");
    console.log(`   Общий статус: ${getStatusEmoji(diagnostics.summary.overallStatus)} ${diagnostics.summary.overallStatus.toUpperCase()}`);
    console.log(`   Критические ошибки: ${diagnostics.summary.criticalIssues}`);
    console.log(`   Предупреждения: ${diagnostics.summary.warnings}`);
    console.log(`   API доступен: ${diagnostics.summary.uptime ? '✅ Да' : '❌ Нет'}`);
    
    if (diagnostics.configuration.issues.length > 0) {
      console.log("\n🚨 КРИТИЧЕСКИЕ ПРОБЛЕМЫ КОНФИГУРАЦИИ:");
      diagnostics.configuration.issues.forEach((issue, index) => {
        console.log(`   ${index + 1}. ${issue}`);
      });
    }
    
    if (diagnostics.configuration.recommendations.length > 0) {
      console.log("\n💡 РЕКОМЕНДАЦИИ:");
      diagnostics.configuration.recommendations.forEach((rec, index) => {
        console.log(`   ${index + 1}. ${rec}`);
      });
    }
    
    if (!diagnostics.health.success) {
      console.log("\n❌ ПРОБЛЕМЫ С API СЕРВЕРОМ:");
      console.log(`   Ошибка: ${diagnostics.health.error}`);
      console.log(`   Сообщение: ${diagnostics.health.message}`);
      console.log("\n🔧 СПОСОБЫ РЕШЕНИЯ:");
      console.log("   1. Проверьте что API сервер запущен на порту 3001");
      console.log("   2. Проверьте переменную PUBLIC_API_URL в .env файле");
      console.log("   3. Убедитесь что API_PORT=3001 в конфигурации сервера");
    }
    
  } catch (error) {
    console.error("❌ Ошибка при выполнении диагностики:", error);
  }
  
  console.log("🔬 === ДИАГНОСТИКА ЗАВЕРШЕНА ===\n");
}

/**
 * Быстрая проверка конфигурации при разработке
 */
export function checkQuickConfig(): void {
  console.log("⚡ === БЫСТРАЯ ПРОВЕРКА КОНФИГУРАЦИИ ===");
  
  console.log("🔧 Текущая конфигурация API:");
  console.log(`   Base URL: ${API_CONFIG.BASE_URL}`);
  console.log(`   Timeout: ${API_CONFIG.REQUEST_CONFIG.DEFAULT_TIMEOUT}ms`);
  console.log(`   Retries: ${API_CONFIG.REQUEST_CONFIG.DEFAULT_RETRIES}`);
  
  // Простые проверки
  const issues: string[] = [];
  
  if (!API_CONFIG.BASE_URL.includes('/api/v1')) {
    issues.push("BASE_URL не содержит '/api/v1'");
  }
  
  if (!API_CONFIG.BASE_URL.startsWith('http')) {
    issues.push("BASE_URL должен начинаться с http:// или https://");
  }
  
  if (API_CONFIG.REQUEST_CONFIG.DEFAULT_TIMEOUT < 5000) {
    issues.push("Timeout слишком короткий (< 5 секунд)");
  }
  
  if (issues.length === 0) {
    console.log("✅ Конфигурация выглядит корректно!");
  } else {
    console.log("❌ Обнаружены проблемы:");
    issues.forEach((issue, index) => {
      console.log(`   ${index + 1}. ${issue}`);
    });
  }
  
  console.log("⚡ === БЫСТРАЯ ПРОВЕРКА ЗАВЕРШЕНА ===\n");
}

/**
 * Автоматическое исправление распространенных проблем конфигурации
 */
export function suggestConfigFixes(): void {
  console.log("🔧 === ПРЕДЛОЖЕНИЯ ПО ИСПРАВЛЕНИЮ КОНФИГУРАЦИИ ===");
  
  console.log("📝 Для исправления проблем с API endpoints:");
  console.log("1. Убедитесь что файл apps/web/.env содержит:");
  console.log("   PUBLIC_API_URL=http://localhost:3001/api/v1");
  console.log("");
  console.log("2. Проверьте файл .env.windows:");
  console.log("   PUBLIC_API_URL=http://localhost:3001/api/v1");
  console.log("");
  console.log("3. Перезапустите веб-приложение после изменения .env:");
  console.log("   cd apps/web && bun run dev");
  console.log("");
  console.log("4. Проверьте что API сервер запущен:");
  console.log("   cd apps/api && bun run dev");
  console.log("");
  console.log("5. Проверьте доступность API:");
  console.log("   curl http://localhost:3001/health");
  
  console.log("🔧 === ПРЕДЛОЖЕНИЯ ЗАВЕРШЕНЫ ===\n");
}

/**
 * Получение эмодзи для статуса
 */
function getStatusEmoji(status: string): string {
  switch (status) {
    case 'healthy': return '✅';
    case 'warning': return '⚠️';
    case 'error': return '❌';
    default: return '❓';
  }
}

/**
 * Проверка конкретных endpoint'ов
 */
export async function testSpecificEndpoints(): Promise<void> {
  console.log("🎯 === ТЕСТИРОВАНИЕ КОНКРЕТНЫХ ENDPOINTS ===");
  
  const endpointsToTest = [
    { name: "Health Check", method: () => api.checkHealth() },
    { name: "Config", method: () => api.getConfig() },
    { name: "Kurs", method: () => api.getKurs() },
  ];
  
  for (const endpoint of endpointsToTest) {
    console.log(`\n🔍 Тестирование ${endpoint.name}...`);
    try {
      const result = await endpoint.method();
      if (result.success) {
        console.log(`   ✅ ${endpoint.name}: Успешно`);
      } else {
        console.log(`   ⚠️ ${endpoint.name}: Ошибка - ${result.error} - ${result.message}`);
      }
    } catch (error: any) {
      console.log(`   ❌ ${endpoint.name}: Исключение - ${error.message}`);
    }
  }
  
  console.log("🎯 === ТЕСТИРОВАНИЕ ENDPOINTS ЗАВЕРШЕНО ===\n");
}

// Автоматический запуск диагностики в development режиме
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  // Запуск диагностики через небольшую задержку чтобы не блокировать загрузку страницы
  setTimeout(() => {
    checkQuickConfig();
  }, 1000);
  
  // Экспорт в window для использования из консоли браузера
  (window as any).apiDiagnostics = {
    runApiDiagnostics,
    checkQuickConfig,
    suggestConfigFixes,
    testSpecificEndpoints,
  };
  
  console.log("🛠️ API Diagnostics доступны в window.apiDiagnostics:");
  console.log("   - window.apiDiagnostics.runApiDiagnostics()");
  console.log("   - window.apiDiagnostics.checkQuickConfig()");
  console.log("   - window.apiDiagnostics.suggestConfigFixes()");
  console.log("   - window.apiDiagnostics.testSpecificEndpoints()");
}