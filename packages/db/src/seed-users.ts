// Автоматическое создание начальных пользователей для Windows
// YuYu Lolita Shopping System
import { getPool, initializeConnection, testConnection } from "./connection.js";
import { getUserByEmail } from "./query-builders.js";
import { ConfigurationError } from "./config.js";

async function hashPassword(password: string): Promise<string> {
  // Простой hash для demo - в продакшене используйте bcrypt
  const crypto = await import('crypto');
  return crypto.createHash('sha256').update(password + 'yuyulolita_salt').digest('hex');
}

function generateSecurePassword(): string {
  const length = 12;
  const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*';
  let password = '';
  
  // Ensure at least one character from each required type
  password += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[Math.floor(Math.random() * 26)]; // uppercase
  password += 'abcdefghijklmnopqrstuvwxyz'[Math.floor(Math.random() * 26)]; // lowercase
  password += '0123456789'[Math.floor(Math.random() * 10)]; // digit
  password += '!@#$%^&*'[Math.floor(Math.random() * 8)]; // special
  
  // Fill the rest randomly
  for (let i = 4; i < length; i++) {
    password += charset[Math.floor(Math.random() * charset.length)];
  }
  
  // Shuffle the password
  return password.split('').sort(() => Math.random() - 0.5).join('');
}

async function createUser(
  email: string, 
  password: string, 
  role: 'admin' | 'user' = 'user', 
  name: string = '',
  fullName: string = ''
): Promise<void> {
  const pool = await getPool();
  
  try {
    // Проверяем, существует ли пользователь
    const existing = await getUserByEmail(email);
    if (existing) {
      console.log(`⚠️  Пользователь ${email} уже существует, пропускаем`);
      return;
    }
    
    const hashedPassword = await hashPassword(password);
    const userName = name || email.split('@')[0];
    const userFullName = fullName || userName;
    
    await pool.execute(`
      INSERT INTO users (
        id, email, password_hash, name, full_name, registration_method, 
        role, status, email_verified, created_at, updated_at
      ) VALUES (UUID(), ?, ?, ?, ?, 'email', ?, 'active', true, NOW(), NOW())
    `, [email, hashedPassword, userName, userFullName, role]);
    
    console.log(`✅ Пользователь ${email} создан успешно (роль: ${role})`);
    
  } catch (error) {
    console.error(`❌ Ошибка создания пользователя ${email}:`, error);
    throw error;
  }
}

export async function seedUsers(): Promise<void> {
  console.log('');
  console.log('🌱 ========================================');
  console.log('🌱 СОЗДАНИЕ НАЧАЛЬНЫХ ПОЛЬЗОВАТЕЛЕЙ');
  console.log('🌱 YuYu Lolita Shopping System');
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
    
    // Создаем главного администратора с безопасным паролем
    const adminPassword = generateSecurePassword();
    await createUser(
      'admin@yuyulolita.com', 
      adminPassword, 
      'admin', 
      'admin',
      'Главный Администратор'
    );
    
    console.log('');
    console.log('🔐 ========================================');
    console.log('🔐 ВАЖНАЯ ИНФОРМАЦИЯ О ПАРОЛЕ АДМИНА');
    console.log('🔐 ========================================');
    console.log(`🔐 Email: admin@yuyulolita.com`);
    console.log(`🔐 Пароль: ${adminPassword}`);
    console.log('🔐 ========================================');
    console.log('📝 ОБЯЗАТЕЛЬНО сохраните этот пароль!');
    console.log('🔒 Используйте его для первого входа в систему');
    console.log('🔐 ========================================');
    console.log('');
    
    // Создаем тестовых пользователей (только для development)
    if (process.env.NODE_ENV !== 'production') {
      console.log('👥 Создаем тестовых пользователей...');
      
      await createUser(
        'test1@yuyulolita.com', 
        'Test123!', 
        'user', 
        'test1',
        'Тестовый Пользователь 1'
      );
      
      await createUser(
        'test2@yuyulolita.com', 
        'Test123!', 
        'user', 
        'test2',
        'Тестовый Пользователь 2'
      );
      
      await createUser(
        'test3@yuyulolita.com', 
        'Test123!', 
        'user', 
        'test3',
        'Тестовый Пользователь 3'
      );
      
      console.log('');
      console.log('👥 ========================================');
      console.log('👥 ТЕСТОВЫЕ ПОЛЬЗОВАТЕЛИ СОЗДАНЫ');
      console.log('👥 ========================================');
      console.log('👥 Email: test1@yuyulolita.com');
      console.log('👥 Email: test2@yuyulolita.com');  
      console.log('👥 Email: test3@yuyulolita.com');
      console.log('👥 Пароль для всех: Test123!');
      console.log('👥 ========================================');
      console.log('');
    }
    
    // Проверяем созданных пользователей
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
    
    console.log('');
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

export { createUser };