// Автоматическое создание начальных пользователей для Windows
// YuYu Lolita Shopping System - Обновлено для использования централизованного модуля
import { initializeConnection, testConnection } from "./connection.js";
import { ConfigurationError } from "./config.js";
import { 
  createAdminUser, 
  createTestUser, 
  displayCredentialsInfo,
  USER_GENERATION_CONSTANTS 
} from "./user-generator.js";

export async function seedUsers(): Promise<void> {
  console.log('');
  console.log('🌱 ========================================');
  console.log('🌱 СОЗДАНИЕ НАЧАЛЬНЫХ ПОЛЬЗОВАТЕЛЕЙ');
  console.log('🌱 YuYu Lolita Shopping System - СТАНДАРТИЗИРОВАННАЯ ВЕРСИЯ');
  console.log('🌱 ========================================');
  console.log('');
  
  try {
    // Initialize database connection with environment configuration
    console.log('[SEED] 🔧 Initializing database connection...');
    initializeConnection();
    
    // Test connection before proceeding
    console.log('[SEED] 🧪 Testing database connectivity...');
    await testConnection();
    console.log('[SEED] ✅ Database connection verified');
    console.log('');
    console.log('👑 Создаем главного администратора...');
    
    // Создаем главного администратора с использованием централизованного модуля
    const adminPassword = await createAdminUser('seeding');
    
    console.log('');
    console.log('🔐 ========================================');
    console.log('🔐 ВАЖНАЯ ИНФОРМАЦИЯ О ПАРОЛЕ АДМИНА');
    console.log('🔐 ========================================');
    console.log(`🔐 Email: ${USER_GENERATION_CONSTANTS.ADMIN_EMAIL}`);
    console.log(`🔐 Пароль: ${adminPassword}`);
    console.log('🔐 ========================================');
    console.log('📝 Пароль сохранен в credentials.txt');
    console.log('🔒 Используйте его для первого входа в систему');
    console.log('🔐 ========================================');
    console.log('');
    
    // Создаем тестовых пользователей (только для development)
    if (process.env.NODE_ENV !== 'production') {
      console.log('👥 Создаем тестовых пользователей...');
      
      await createTestUser('test1@yuyulolita.com', 'test1', 'Test123!', 'seeding');
      await createTestUser('test2@yuyulolita.com', 'test2', 'Test123!', 'seeding');
      await createTestUser('test3@yuyulolita.com', 'test3', 'Test123!', 'seeding');
      
      console.log('');
      console.log('👥 ========================================');
      console.log('👥 ТЕСТОВЫЕ ПОЛЬЗОВАТЕЛИ СОЗДАНЫ');
      console.log('👥 ========================================');
      console.log('👥 Email: test1@yuyulolita.com');
      console.log('👥 Email: test2@yuyulolita.com');  
      console.log('👥 Email: test3@yuyulolita.com');
      console.log('👥 Все пароли сохранены в credentials.txt');
      console.log('👥 ========================================');
      console.log('');
    }
    
    // Проверяем созданных пользователей
    const { getPool } = await import('./connection.js');
    const pool = await getPool();
    const [rows] = await pool.execute('SELECT email, role, status FROM users ORDER BY role DESC, email');
    const users = rows as any[];
    
    console.log('📊 ========================================');
    console.log('📊 СПИСОК СОЗДАННЫХ ПОЛЬЗОВАТЕЛЕЙ');
    console.log('📊 ========================================');
    users.forEach(user => {
      const roleIcon = user.role === 'admin' ? '👑' : '👤';
      const statusIcon = user.status === 'active' ? '✅' : '⏸️';
      console.log(`${roleIcon} ${user.email} (${user.role}) ${statusIcon}`);
    });
    console.log('📊 ========================================');
    
    // Показать информацию о файле с учетными данными
    displayCredentialsInfo();
    
    console.log('🎉 Создание пользователей завершено успешно!');
    console.log('🚀 База данных готова к использованию!');
    console.log('');
    
  } catch (error) {
    console.error('');
    console.error('❌ ========================================');
    console.error('❌ ОШИБКА ПРИ СОЗДАНИИ ПОЛЬЗОВАТЕЛЕЙ');
    console.error('❌ ========================================');
    
    if (error instanceof ConfigurationError) {
      console.error('❌ Ошибка конфигурации базы данных:');
      console.error('❌', error.message);
      console.error('');
      console.error('❌ Проверьте файл .env и настройки MySQL');
    } else if (error instanceof Error) {
      console.error('❌ Детали ошибки:', error.message);
      if (error.message.includes('Access denied')) {
        console.error('');
        console.error('❌ РЕШЕНИЕ:');
        console.error('❌ 1. Проверьте DB_PASSWORD в файле .env');
        console.error('❌ 2. Убедитесь что MySQL сервер запущен');
        console.error('❌ 3. Проверьте права пользователя MySQL');
      }
    } else {
      console.error('❌ Неизвестная ошибка:', error);
    }
    
    console.error('❌ ========================================');
    console.error('');
    throw error;
  }
}

// Запуск если файл вызван напрямую
if (import.meta.url.includes(process.argv[1]?.replace(/\\/g, '/') || '')) {
  seedUsers()
    .then(() => {
      console.log('✅ Процесс создания пользователей завершен');
      process.exit(0);
    })
    .catch((error) => {
      console.error('❌ Процесс создания пользователей завершен с ошибкой:', error);
      process.exit(1);
    });
}