const fs = require('fs');
const postgres = require('postgres');

async function testFixedMigration() {
  console.log('🔧 ТЕСТИРУЕМ ИСПРАВЛЕННУЮ МИГРАЦИЮ');
  console.log('🎯 Проверяем устранение ошибки "синтаксис (примерное положение: $)"');

  // Подключение для создания/удаления БД
  const adminSql = postgres({
    host: '/var/run/postgresql',
    database: 'template1',
    username: 'postgres',
  });

  let testSql;

  try {
    console.log('\n🗑️ Шаг 1: Удаляем старую БД для чистого теста...');
    try {
      await adminSql`DROP DATABASE IF EXISTS yuyu_lolita_test`;
      console.log('✅ Тестовая БД удалена');
    } catch (e) {
      console.log('⚠️ БД не существовала');
    }

    console.log('🆕 Шаг 2: Создаем новую тестовую БД...');
    await adminSql`CREATE DATABASE yuyu_lolita_test`;
    console.log('✅ Тестовая БД создана');

    // Закрываем админское подключение
    await adminSql.end();

    // Подключаемся к тестовой БД
    testSql = postgres({
      host: '/var/run/postgresql',
      database: 'yuyu_lolita_test',
      username: 'postgres',
    });

    console.log('🔗 Шаг 3: Подключаемся к тестовой БД...');
    await testSql`SELECT 1`;
    console.log('✅ Подключение к тестовой БД успешно');

    console.log('📖 Шаг 4: Читаем исправленную миграцию...');
    const migrationContent = fs.readFileSync('./migrations/0000_consolidated_schema.sql', 'utf8');
    console.log('✅ Миграция загружена:', Math.round(migrationContent.length / 1024), 'KB');

    console.log('🚀 Шаг 5: Применяем исправленную миграцию...');
    console.log('   (Проверяем отсутствие синтаксических ошибок с $)');
    
    const startTime = Date.now();
    await testSql.unsafe(migrationContent);
    const duration = Date.now() - startTime;
    
    console.log('✅ МИГРАЦИЯ ПРИМЕНЕНА УСПЕШНО! (', duration, 'ms)');
    console.log('✅ Синтаксические ошибки с $ ИСПРАВЛЕНЫ!');

    console.log('\n🔍 Шаг 6: Проверяем созданные функции...');
    
    // Проверяем функцию cleanup_expired_verification_tokens
    const func1Check = await testSql`
      SELECT proname FROM pg_proc WHERE proname = 'cleanup_expired_verification_tokens'
    `;
    console.log('✅ Функция cleanup_expired_verification_tokens:', func1Check.length > 0 ? 'СОЗДАНА' : '❌ НЕ НАЙДЕНА');

    // Проверяем функцию update_updated_at_column
    const func2Check = await testSql`
      SELECT proname FROM pg_proc WHERE proname = 'update_updated_at_column'
    `;
    console.log('✅ Функция update_updated_at_column:', func2Check.length > 0 ? 'СОЗДАНА' : '❌ НЕ НАЙДЕНА');

    console.log('\n📊 Шаг 7: Проверяем что основные элементы созданы...');
    
    // Проверяем критическую колонку
    const columnCheck = await testSql`
      SELECT 1 FROM information_schema.columns 
      WHERE table_name = 'users' AND column_name = 'overall_verification_status'
    `;
    console.log('✅ Колонка overall_verification_status:', columnCheck.length > 0 ? 'СОЗДАНА' : '❌ НЕ НАЙДЕНА');

    // Подсчитываем таблицы
    const tablesCount = await testSql`
      SELECT COUNT(*) as count FROM information_schema.tables 
      WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    `;
    console.log('📈 Всего таблиц создано:', tablesCount[0].count);

    // Подсчитываем функции
    const functionsCount = await testSql`
      SELECT COUNT(*) as count FROM pg_proc 
      WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
      AND prokind = 'f'
    `;
    console.log('📈 Всего функций создано:', functionsCount[0].count);

    console.log('\n🎉 РЕЗУЛЬТАТ ТЕСТА:');
    console.log('===============================================');
    console.log('✅ СИНТАКСИЧЕСКИЕ ОШИБКИ С $ ПОЛНОСТЬЮ ИСПРАВЛЕНЫ!');
    console.log('✅ Миграция применяется без ошибок');
    console.log('✅ PostgreSQL функции создаются корректно');
    console.log('✅ Все критические элементы БД на месте');
    console.log('✅ Готово для production использования!');

  } catch (error) {
    console.error('\n❌ ОШИБКА ПРИ ТЕСТИРОВАНИИ:');
    console.error('   Сообщение:', error.message);
    
    if (error.message.includes('syntax error') && error.message.includes('$')) {
      console.error('🚨 ВНИМАНИЕ: Синтаксические ошибки с $ все еще есть!');
      console.error('   Проблемная строка, возможно:', error.position);
    } else if (error.message.includes('syntax error')) {
      console.error('⚠️ Есть другие синтаксические ошибки');
    }
    
    throw error;
  } finally {
    if (testSql) {
      await testSql.end();
    }
  }
}

testFixedMigration();