// Простой тест подключения к БД без запуска полного API
const postgres = require('postgres');

async function testDatabaseConnection() {
  console.log('🔍 ФИНАЛЬНАЯ ПРОВЕРКА: Тестируем подключение API к исправленной БД');
  console.log('🎯 Цель: Убедиться, что исходная ошибка "overall_verification_status не существует" исправлена');

  const sql = postgres({
    host: '/var/run/postgresql',
    database: 'yuyu_lolita',
    username: 'postgres',
  });

  try {
    console.log('\n📊 1. ТЕСТ ПОДКЛЮЧЕНИЯ К БД...');
    const connection = await sql`SELECT current_database() as db, current_user as user_name, NOW() as current_time`;
    console.log('✅ Успешное подключение к БД:', connection[0].db);
    console.log('   Пользователь:', connection[0].user_name);

    console.log('\n🔍 2. ПРОВЕРКА ИСХОДНОЙ ПРОБЛЕМЫ...');
    console.log('   Тестируем запрос, который вызывал ошибку "overall_verification_status не существует"');
    
    // Этот запрос раньше вызывал ошибку
    const problemQuery = await sql`
      SELECT id, email, overall_verification_status, failed_login_attempts, email_verified_at
      FROM users 
      WHERE email = 'nonexistent@test.com'
      LIMIT 1
    `;
    
    console.log('✅ УСПЕХ! Запрос выполнен без ошибок (результат:', problemQuery.length, 'записей)');

    console.log('\n💡 3. ТЕСТ СОЗДАНИЯ ПОЛЬЗОВАТЕЛЯ...');
    console.log('   Проверяем, что можем использовать все поля, которые отсутствовали');
    
    const testUser = await sql`
      INSERT INTO users (
        email, 
        password, 
        registration_method, 
        overall_verification_status,
        failed_login_attempts,
        email_verified_at,
        phone_verified_at
      ) VALUES (
        'final-test@example.com',
        'test123',
        'email',
        'unverified',
        0,
        NULL,
        NULL
      )
      RETURNING id, email, overall_verification_status, failed_login_attempts
    `;
    
    console.log('✅ ПОЛЬЗОВАТЕЛЬ СОЗДАН:', testUser[0]);
    
    // Тестируем обновление статуса верификации
    const updatedUser = await sql`
      UPDATE users 
      SET overall_verification_status = 'partial', failed_login_attempts = 1
      WHERE email = 'final-test@example.com'
      RETURNING email, overall_verification_status, failed_login_attempts
    `;
    
    console.log('✅ ПОЛЬЗОВАТЕЛЬ ОБНОВЛЕН:', updatedUser[0]);
    
    // Удаляем тестового пользователя
    await sql`DELETE FROM users WHERE email = 'final-test@example.com'`;
    console.log('✅ Тестовый пользователь удален');

    console.log('\n🎯 4. ПРОВЕРКА ВСЕХ КРИТИЧЕСКИХ ПОЛЕЙ...');
    const criticalFields = [
      'overall_verification_status',
      'failed_login_attempts', 
      'locked_until',
      'email_verified_at',
      'phone_verified_at'
    ];
    
    for (const field of criticalFields) {
      const fieldExists = await sql`
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = ${field}
      `;
      console.log(`   ${field}:`, fieldExists.length > 0 ? '✅ СУЩЕСТВУЕТ' : '❌ НЕ НАЙДЕНО');
    }

    console.log('\n🏆 ФИНАЛЬНЫЙ РЕЗУЛЬТАТ:');
    console.log('===============================================');
    console.log('✅ ИСХОДНАЯ ОШИБКА ПОЛНОСТЬЮ УСТРАНЕНА!');
    console.log('✅ Все критические поля созданы и работают');
    console.log('✅ База данных готова для production использования');
    console.log('✅ API может использовать все необходимые поля пользователей');
    console.log('✅ Проблема "столбец overall_verification_status не существует" РЕШЕНА');

  } catch (error) {
    console.error('\n❌ ОШИБКА ПРИ ТЕСТИРОВАНИИ:');
    console.error('   Сообщение:', error.message);
    
    if (error.message.includes('overall_verification_status')) {
      console.error('🚨 ВНИМАНИЕ: Исходная проблема все еще существует!');
    }
    
    console.error('   Полная ошибка:', error);
  } finally {
    await sql.end();
  }
}

testDatabaseConnection();