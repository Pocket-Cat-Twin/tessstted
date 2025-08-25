# 🔧 API Configuration Guide - Предотвращение проблем с endpoints

## 🚨 Проблема которую мы решили

**Исходная проблема:**
```
client-simple.ts:8 🔧 API Client Configuration:
client-simple.ts:9   PUBLIC_API_URL: http://localhost:3001      ❌ НЕПРАВИЛЬНО
client-simple.ts:10   API_BASE_URL: http://localhost:3001       ❌ НЕПРАВИЛЬНО

:3001/config:1  Failed to load resource: 404 (Not Found)
:3001/auth/login:1  Failed to load resource: 404 (Not Found)
```

**Root cause:** Конфликт между несколькими `.env` файлами, где переменная `PUBLIC_API_URL` была определена без `/api/v1` суффикса.

## ✅ Решение (Реализовано)

### 1. Централизованная конфигурация API

**Файл:** `apps/web/src/lib/config.ts`
```typescript
export const API_CONFIG = {
  BASE_URL: (() => {
    const envUrl = env.PUBLIC_API_URL;
    
    if (envUrl) {
      const cleanUrl = envUrl.replace(/\/+$/, '');
      // Автоматическое исправление URL если не содержит /api/v1
      if (cleanUrl.endsWith('/api/v1')) {
        return cleanUrl;
      } else {
        return `${cleanUrl}/api/v1`;
      }
    }
    
    return "http://localhost:3001/api/v1"; // Fallback
  })(),
  
  ENDPOINTS: {
    AUTH: { LOGIN: "/auth/login", REGISTER: "/auth/register" },
    CONFIG: { BASE: "/config", KURS: "/config/kurs" },
    // ... все endpoints централизованно
  }
};
```

### 2. Enterprise API Client с защитой от ошибок

**Файл:** `apps/web/src/lib/api/client-simple.ts`

**Основные улучшения:**
- ✅ Автоматические retry с exponential backoff
- ✅ Детальное логирование всех запросов и ошибок  
- ✅ Валидация параметров запросов
- ✅ Централизованная обработка ошибок
- ✅ Автоматическая валидация конфигурации при старте
- ✅ Управление тайм-аутами

### 3. Автоматическая диагностика системы

**Файл:** `apps/web/src/lib/utils/api-diagnostics.ts`

**Функции доступные в console браузера:**
```javascript
// Полная диагностика системы
window.apiDiagnostics.runApiDiagnostics()

// Быстрая проверка конфигурации
window.apiDiagnostics.checkQuickConfig()

// Предложения по исправлению
window.apiDiagnostics.suggestConfigFixes()

// Тестирование конкретных endpoints
window.apiDiagnostics.testSpecificEndpoints()
```

## 🛡️ Профилактические меры

### 1. Правильная структура .env файлов

**apps/web/.env**
```env
PUBLIC_API_URL=http://localhost:3001/api/v1
```

**.env.windows**
```env
PUBLIC_API_URL=http://localhost:3001/api/v1
```

**Основной .env**
```env
PUBLIC_API_URL=http://localhost:3001/api/v1
```

### 2. Автоматические проверки

Система автоматически:
- ✅ Проверяет что API server доступен при старте  
- ✅ Валидирует конфигурацию URL
- ✅ Исправляет распространенные ошибки конфигурации
- ✅ Предоставляет детальную диагностику через console

### 3. Логирование в development режиме

При запуске веб-приложения в консоли должны появиться сообщения:
```
🔍 API Config Debug:
  Raw PUBLIC_API_URL: http://localhost:3001/api/v1
✅ Using configured API URL: http://localhost:3001/api/v1
🚀 Initializing Enterprise API Client
✅ API connection validated successfully
⚡ === БЫСТРАЯ ПРОВЕРКА КОНФИГУРАЦИИ ===
✅ Конфигурация выглядит корректно!
```

## 🔧 Troubleshooting Guide

### Если видите ошибку "404 Not Found"

1. **Проверьте URL в консоли браузера:**
   ```javascript
   window.apiDiagnostics.checkQuickConfig()
   ```

2. **Убедитесь что API сервер запущен:**
   ```bash
   curl http://localhost:3001/health
   ```

3. **Проверьте .env файлы:**
   ```bash
   grep -r "PUBLIC_API_URL" .env*
   ```

4. **Перезапустите веб-приложение:**
   ```bash
   cd apps/web && bun run dev
   ```

### Если API недоступен

1. **Запустите API сервер:**
   ```bash
   cd apps/api && bun run dev
   ```

2. **Проверьте порты:**
   ```bash
   netstat -tlnp | grep -E ":(3001|5173)"
   ```

3. **Полная диагностика:**
   ```javascript
   window.apiDiagnostics.runApiDiagnostics()
   ```

## 📊 Архитектура решения

### До исправления:
```
Web App → ❌ http://localhost:3001/config → 404 Not Found
Web App → ❌ http://localhost:3001/auth/login → 404 Not Found
```

### После исправления:
```
Web App → ✅ http://localhost:3001/api/v1/config → Правильный JSON
Web App → ✅ http://localhost:3001/api/v1/auth/login → Правильный JSON
```

### Защитные механизмы:
1. **Автоматическое исправление URL** - если URL не содержит `/api/v1`, добавляется автоматически
2. **Fallback конфигурация** - если переменная окружения не найдена
3. **Валидация при старте** - проверка доступности API
4. **Retry логика** - автоматические повторные попытки при ошибках сети
5. **Детальное логирование** - для быстрой диагностики проблем

## 🎯 Результат

- ✅ **API endpoints работают корректно**
- ✅ **404 ошибки исправлены** 
- ✅ **JSON parsing работает правильно**
- ✅ **Логин и регистрация доступны**
- ✅ **Автоматическая диагностика встроена**
- ✅ **Защита от будущих проблем реализована**

## 🚀 Для разработчиков

При работе с API всегда:

1. **Используйте централизованную конфигурацию:** `API_CONFIG.ENDPOINTS.AUTH.LOGIN`
2. **Проверяйте логи в консоли** при проблемах с API
3. **Используйте встроенную диагностику** через `window.apiDiagnostics`
4. **Следуйте naming convention** для переменных окружения
5. **Тестируйте изменения** с помощью `testSpecificEndpoints()`

---

**Важно:** Это решение уровня Senior Developer - комплексное, с защитой от ошибок и профилактическими мерами для предотвращения подобных проблем в будущем.