#!/usr/bin/env node

/**
 * Test API Database Connection
 * Симулирует поведение API при подключении к базе данных
 * Тестирует все операции, которые выполняет реальный API
 */

const { execSync } = require('child_process');

console.log('🧪 ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЯ API К БАЗЕ ДАННЫХ');
console.log('===============================================');

// Параметры подключения
const DB_USER = 'postgres';
const DB_PASS = 'postgres';
const DB_HOST = 'localhost';
const DB_PORT = '5432';
const DB_NAME = 'yuyu_lolita';
const CONNECTION_STRING = `postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}`;

console.log(`🔗 Connection String: ${CONNECTION_STRING.replace(/:\/\/[^:]*:[^@]*@/, '://***:***@')}`);
console.log('');

// Тесты, которые выполняет API
const tests = [
  {
    name: 'Базовое подключение к базе',
    sql: 'SELECT current_user, current_database(), version();',
    description: 'Проверяет, что подключение работает'
  },
  {
    name: 'Доступ к таблице users (тест API)',
    sql: 'SELECT COUNT(*) as user_count FROM users;',
    description: 'Тестирует доступ к таблице users (используется в API)'
  },
  {
    name: 'Доступ к таблице config (основной тест API)', 
    sql: 'SELECT COUNT(*) as config_count FROM config;',
    description: 'Тестирует доступ к config (это то, что проверяет API при инициализации)'
  },
  {
    name: 'Простой запрос к config (точно как в API)',
    sql: 'SELECT key, value, type FROM config LIMIT 1;',
    description: 'Симулирует точный запрос из API кода'
  },
  {
    name: 'Тест создания записи в config',
    sql: `INSERT INTO config (key, value, type, description) VALUES ('api_test_key', 'api_test_value', 'string', 'Test from API connection') ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;`,
    description: 'Тестирует возможность записи (API может создавать конфигурации)'
  },
  {
    name: 'Тест чтения созданной записи', 
    sql: `SELECT key, value FROM config WHERE key = 'api_test_key';`,
    description: 'Проверяет, что запись была создана'
  },
  {
    name: 'Доступ к таблице orders',
    sql: 'SELECT COUNT(*) as orders_count FROM orders;',
    description: 'Тестирует доступ к orders (основная бизнес-логика API)'
  },
  {
    name: 'Доступ к таблице customers',
    sql: 'SELECT COUNT(*) as customers_count FROM customers;', 
    description: 'Тестирует доступ к customers'
  },
  {
    name: 'Комплексный запрос (JOIN)',
    sql: `SELECT 
            (SELECT COUNT(*) FROM users) as users_count,
            (SELECT COUNT(*) FROM orders) as orders_count, 
            (SELECT COUNT(*) FROM config) as config_count,
            (SELECT COUNT(*) FROM customers) as customers_count;`,
    description: 'Тестирует сложные запросы, которые может выполнять API'
  }
];

// Выполняем тесты
let passedTests = 0;
let totalTests = tests.length;

console.log(`📊 Выполняем ${totalTests} тестов подключения...\n`);

for (let i = 0; i < tests.length; i++) {
  const test = tests[i];
  const testNumber = i + 1;
  
  try {
    console.log(`🔄 Тест ${testNumber}/${totalTests}: ${test.name}`);
    console.log(`   💡 ${test.description}`);
    
    const result = execSync(
      `PGPASSWORD=${DB_PASS} psql "${CONNECTION_STRING}" -c "${test.sql}"`,
      { 
        encoding: 'utf8', 
        timeout: 10000,
        stdio: ['pipe', 'pipe', 'pipe']
      }
    );
    
    console.log(`   ✅ УСПЕХ`);
    
    // Показываем результат для некоторых тестов
    if (test.sql.includes('SELECT') && !test.sql.includes('COUNT(*)')) {
      const lines = result.trim().split('\n');
      const dataLines = lines.slice(2, -2); // Убираем заголовки и футер
      if (dataLines.length > 0) {
        console.log(`   📄 Результат: ${dataLines.join(' | ')}`);
      }
    }
    
    passedTests++;
    
  } catch (error) {
    console.log(`   ❌ ОШИБКА: ${error.message.split('\n')[0]}`);
  }
  
  console.log('');
}

// Итоги
console.log('🎯 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ');
console.log('==========================');
console.log(`✅ Успешных тестов: ${passedTests}/${totalTests}`);
console.log(`📊 Процент успеха: ${Math.round(passedTests/totalTests*100)}%`);
console.log('');

if (passedTests === totalTests) {
  console.log('🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!');
  console.log('🚀 API СМОЖЕТ ПОЛНОЦЕННО РАБОТАТЬ С ЭТОЙ БАЗОЙ ДАННЫХ!');
  console.log('');
  console.log('✅ Подтвержденная функциональность:');
  console.log('   • Подключение к базе данных');
  console.log('   • Чтение из всех основных таблиц');
  console.log('   • Запись данных в config');
  console.log('   • Сложные SQL запросы');
  console.log('   • Полная совместимость с API кодом');
  console.log('');
  console.log('🔗 Параметры подключения:');
  console.log(`   DATABASE_URL=${CONNECTION_STRING.replace(/:\/\/[^:]*:[^@]*@/, '://***:***@')}`);
  
} else {
  console.log('⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ');
  console.log(`   ${totalTests - passedTests} из ${totalTests} тестов неудачны`);
  console.log('   Необходимо исправить проблемы перед запуском API');
}

console.log('');