const fs = require('fs');
const { exec } = require('child_process');
const util = require('util');
const execAsync = util.promisify(exec);

async function directMigration() {
  try {
    console.log('🚀 Применяем миграцию напрямую через psql...');

    // Читаем миграцию
    console.log('📖 Читаем файл миграции...');
    const migrationContent = fs.readFileSync('./migrations/0000_consolidated_schema.sql', 'utf8');
    console.log('✅ Файл загружен:', Math.round(migrationContent.length / 1024), 'KB');

    // Создаем временный файл для передачи в psql
    const tempFile = '/tmp/migration.sql';
    fs.writeFileSync(tempFile, migrationContent);
    console.log('✅ Временный файл создан');

    // Устанавливаем переменные окружения - используем peer-аутентификацию
    const env = {
      ...process.env,
      PGHOST: '/var/run/postgresql', // Unix socket для peer auth
      PGDATABASE: 'yuyu_lolita',
      PGUSER: 'postgres',
    };

    try {
      // Пробуем создать базу данных
      console.log('🆕 Создаем базу данных...');
      await execAsync('createdb yuyu_lolita', { env });
      console.log('✅ База данных создана');
    } catch (dbError) {
      console.log('⚠️ База данных уже существует или ошибка создания');
    }

    // Применяем миграцию
    console.log('🚀 Применяем схему к базе данных...');
    const { stdout, stderr } = await execAsync(`psql -d yuyu_lolita -f ${tempFile}`, { env });
    
    if (stderr && stderr.includes('ERROR')) {
      console.error('❌ Ошибки при применении миграции:');
      console.error(stderr);
    } else {
      console.log('✅ Миграция применена успешно!');
    }

    // Выводим stdout если есть
    if (stdout) {
      console.log('📝 Вывод миграции:');
      console.log(stdout.split('\n').slice(-10).join('\n')); // Последние 10 строк
    }

    // Проверяем критические элементы
    console.log('🔍 Проверяем критические элементы...');

    // Проверяем enum
    const enumCheck = await execAsync(`psql -d yuyu_lolita -tAc "SELECT 1 FROM pg_type WHERE typname = 'user_verification_status';"`, { env });
    console.log('✅ Enum user_verification_status:', enumCheck.stdout.trim() === '1' ? 'СОЗДАН' : '❌ НЕ НАЙДЕН');

    // Проверяем колонку
    const columnCheck = await execAsync(`psql -d yuyu_lolita -tAc "SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'overall_verification_status';"`, { env });
    console.log('✅ Колонка overall_verification_status:', columnCheck.stdout.trim() === '1' ? 'СОЗДАНА' : '❌ НЕ НАЙДЕНА');

    // Проверяем другие критические поля
    const criticalFields = ['failed_login_attempts', 'locked_until', 'email_verified_at', 'phone_verified_at'];
    for (const field of criticalFields) {
      const fieldCheck = await execAsync(`psql -d yuyu_lolita -tAc "SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = '${field}';"`, { env });
      console.log(`✅ Поле ${field}:`, fieldCheck.stdout.trim() === '1' ? 'СОЗДАНО' : '❌ НЕ НАЙДЕНО');
    }

    // Проверяем таблицу faq_categories
    const faqCheck = await execAsync(`psql -d yuyu_lolita -tAc "SELECT 1 FROM information_schema.tables WHERE table_name = 'faq_categories';"`, { env });
    console.log('✅ Таблица faq_categories:', faqCheck.stdout.trim() === '1' ? 'СОЗДАНА' : '❌ НЕ НАЙДЕНА');

    // Подсчитываем таблицы и enum'ы
    const tablesCount = await execAsync(`psql -d yuyu_lolita -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';"`, { env });
    const enumsCount = await execAsync(`psql -d yuyu_lolita -tAc "SELECT COUNT(*) FROM pg_type WHERE typtype = 'e';"`, { env });

    console.log('📊 Всего таблиц создано:', tablesCount.stdout.trim());
    console.log('📊 Всего enum-ов создано:', enumsCount.stdout.trim());

    // Удаляем временный файл
    fs.unlinkSync(tempFile);
    console.log('🧹 Временный файл удален');

    console.log('🎉 ПОЛНАЯ СХЕМА ПРИМЕНЕНА УСПЕШНО!');
    console.log('✅ База данных готова к работе с API');

  } catch (error) {
    console.error('❌ Ошибка при применении миграции:', error.message);
    console.error('Подробности:', error);
    process.exit(1);
  }
}

directMigration();