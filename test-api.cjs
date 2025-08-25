const postgres = require('postgres');

async function testAPI() {
  console.log('🧪 Тестируем подключение API к базе данных...');

  const sql = postgres({
    host: '/var/run/postgresql',
    database: 'yuyu_lolita', 
    username: 'postgres',
  });

  try {
    // Тест 1: Базовое подключение
    console.log('🔌 Тест 1: Базовое подключение к БД...');
    const now = await sql`SELECT NOW() as current_time`;
    console.log('✅ Подключение успешно:', now[0].current_time);

    // Тест 2: Проверяем критическую колонку 
    console.log('🔍 Тест 2: Проверяем колонку overall_verification_status...');
    const columnTest = await sql`
      SELECT column_name, data_type, column_default
      FROM information_schema.columns 
      WHERE table_name = 'users' AND column_name = 'overall_verification_status'
    `;
    
    if (columnTest.length > 0) {
      console.log('✅ Колонка overall_verification_status найдена!');
      console.log('   Тип данных:', columnTest[0].data_type);
      console.log('   Значение по умолчанию:', columnTest[0].column_default);
    } else {
      console.log('❌ Колонка overall_verification_status НЕ найдена');
    }

    // Тест 3: Проверяем enum
    console.log('🔍 Тест 3: Проверяем enum user_verification_status...');
    const enumTest = await sql`
      SELECT enumlabel 
      FROM pg_enum e
      JOIN pg_type t ON e.enumtypid = t.oid
      WHERE t.typname = 'user_verification_status'
      ORDER BY e.enumsortorder
    `;
    
    if (enumTest.length > 0) {
      console.log('✅ Enum user_verification_status найден!');
      console.log('   Значения:', enumTest.map(r => r.enumlabel).join(', '));
    } else {
      console.log('❌ Enum user_verification_status НЕ найден');
    }

    // Тест 4: Попробуем вставить тестового пользователя
    console.log('🔍 Тест 4: Тестируем INSERT в таблицу users...');
    
    try {
      const insertResult = await sql`
        INSERT INTO users (email, password, registration_method, overall_verification_status)
        VALUES ('test@example.com', 'password123', 'email', 'unverified')
        RETURNING id, email, overall_verification_status
      `;
      
      console.log('✅ INSERT успешен!');
      console.log('   Создан пользователь:', insertResult[0]);
      
      // Удаляем тестового пользователя
      await sql`DELETE FROM users WHERE email = 'test@example.com'`;
      console.log('✅ Тестовый пользователь удален');
      
    } catch (insertError) {
      console.log('❌ Ошибка INSERT:', insertError.message);
    }

    // Тест 5: Проверяем общее состояние БД
    console.log('📊 Тест 5: Общая статистика БД...');
    const stats = await sql`
      SELECT 
        (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public') as tables_count,
        (SELECT COUNT(*) FROM pg_type WHERE typtype = 'e') as enums_count,
        (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'users') as users_columns_count
    `;
    
    console.log('📈 Статистика:');
    console.log('   Таблиц:', stats[0].tables_count);
    console.log('   Enum-ов:', stats[0].enums_count); 
    console.log('   Колонок в users:', stats[0].users_columns_count);

    console.log('🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! API готов к работе!');

  } catch (error) {
    console.error('❌ Ошибка при тестировании:', error.message);
    console.error('Подробности:', error);
  } finally {
    await sql.end();
  }
}

testAPI();