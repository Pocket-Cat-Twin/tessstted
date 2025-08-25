const fs = require('fs');
const postgres = require('postgres');

// Попробуем разные варианты подключения
let adminSql, dbSql;

// Попробуем подключиться как codespace
try {
  adminSql = postgres({
    host: 'localhost',
    port: 5432,
    database: 'template1',
    username: 'codespace',
  });
  dbSql = postgres({
    host: 'localhost',
    port: 5432,
    database: 'yuyu_lolita', 
    username: 'codespace',
  });
} catch (e) {
  // Fallback к postgres
  adminSql = postgres({
    host: 'localhost',
    port: 5432,
    database: 'template1',
    username: 'postgres',
  });
  dbSql = postgres({
    host: 'localhost',
    port: 5432,
    database: 'yuyu_lolita', 
    username: 'postgres',
  });
}

async function resetAndMigrate() {
  try {
    console.log('🚀 Начинаем полный сброс и миграцию базы данных...');
    
    // Шаг 1: Подключаемся к template1 для управления БД
    console.log('🔗 Подключение к template1...');
    await adminSql`SELECT 1`;
    console.log('✅ Подключились к template1');

    // Шаг 2: Удаляем существующую БД (если есть)
    console.log('🗑️ Удаляем существующую базу данных...');
    try {
      await adminSql`DROP DATABASE IF EXISTS yuyu_lolita`;
      console.log('✅ База данных удалена');
    } catch (error) {
      console.log('⚠️ База данных не существовала или не могла быть удалена');
    }

    // Шаг 3: Создаем новую БД
    console.log('🆕 Создаем новую базу данных...');
    await adminSql`CREATE DATABASE yuyu_lolita`;
    console.log('✅ База данных yuyu_lolita создана');

    // Закрываем админское подключение
    await adminSql.end();

    // Шаг 4: Подключаемся к новой БД
    console.log('🔗 Подключение к yuyu_lolita...');
    await dbSql`SELECT NOW()`;
    console.log('✅ Подключились к yuyu_lolita');

    // Шаг 5: Читаем и применяем миграцию
    console.log('📖 Загружаем полную консолидированную схему...');
    const migrationContent = fs.readFileSync('./migrations/0000_consolidated_schema.sql', 'utf8');
    console.log('✅ Схема загружена:', Math.round(migrationContent.length / 1024), 'KB');

    // Шаг 6: Применяем миграцию
    console.log('🚀 Применяем полную схему к базе данных...');
    await dbSql.unsafe(migrationContent);
    console.log('✅ Схема применена успешно!');

    // Шаг 7: Проверяем критически важные элементы
    console.log('🔍 Проверяем критические элементы схемы...');
    
    // Проверяем enum user_verification_status
    const enumCheck = await dbSql`
      SELECT 1 FROM pg_type WHERE typname = 'user_verification_status'
    `;
    console.log('✅ Enum user_verification_status:', enumCheck.length > 0 ? 'СОЗДАН' : '❌ НЕ НАЙДЕН');

    // Проверяем колонку overall_verification_status в таблице users
    const columnCheck = await dbSql`
      SELECT column_name, data_type, column_default 
      FROM information_schema.columns 
      WHERE table_name = 'users' AND column_name = 'overall_verification_status'
    `;
    console.log('✅ Колонка overall_verification_status:', columnCheck.length > 0 ? 'СОЗДАНА' : '❌ НЕ НАЙДЕНА');
    if (columnCheck.length > 0) {
      console.log('   Тип:', columnCheck[0].data_type);
      console.log('   По умолчанию:', columnCheck[0].column_default);
    }

    // Проверяем другие критические поля
    const criticalFields = ['failed_login_attempts', 'locked_until', 'email_verified_at', 'phone_verified_at'];
    for (const field of criticalFields) {
      const fieldCheck = await dbSql`
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = ${field}
      `;
      console.log(`✅ Поле ${field}:`, fieldCheck.length > 0 ? 'СОЗДАНО' : '❌ НЕ НАЙДЕНО');
    }

    // Проверяем таблицу faq_categories
    const faqCategoriesCheck = await dbSql`
      SELECT 1 FROM information_schema.tables WHERE table_name = 'faq_categories'
    `;
    console.log('✅ Таблица faq_categories:', faqCategoriesCheck.length > 0 ? 'СОЗДАНА' : '❌ НЕ НАЙДЕНА');

    // Подсчитываем общее количество таблиц
    const tablesCount = await dbSql`
      SELECT COUNT(*) as count FROM information_schema.tables 
      WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    `;
    console.log('📊 Всего таблиц создано:', tablesCount[0].count);

    // Подсчитываем enum'ы
    const enumsCount = await dbSql`
      SELECT COUNT(*) as count FROM pg_type WHERE typtype = 'e'
    `;
    console.log('📊 Всего enum-ов создано:', enumsCount[0].count);

    console.log('🎉 ПОЛНЫЙ СБРОС И МИГРАЦИЯ ЗАВЕРШЕНЫ УСПЕШНО!');
    console.log('✅ База данных готова к работе');

  } catch (error) {
    console.error('❌ Ошибка при сбросе и миграции:', error.message);
    console.error('Полная ошибка:', error);
    process.exit(1);
  } finally {
    try {
      await dbSql.end();
    } catch (e) {
      console.log('Соединение уже закрыто');
    }
  }
}

resetAndMigrate();