import { exec } from "child_process";
import { promisify } from "util";
import {
  testConnection,
  createDatabaseIfNotExists,
  migrationClient,
  queryClient,
} from "./connection";

const execAsync = promisify(exec);

/**
 * Комплексный скрипт сброса и восстановления базы данных
 * Уровень Senior разработчика - максимальная надёжность и информативность
 */

export async function resetDatabase(options: {
  dropDatabase?: boolean;
  runMigrations?: boolean;
  seedData?: boolean;
  verbose?: boolean;
} = {}) {
  const {
    dropDatabase = true,
    runMigrations = true,
    seedData = true,
    verbose = true,
  } = options;

  console.log("🚀 ПОЛНЫЙ СБРОС БАЗЫ ДАННЫХ - YuYu Lolita Shopping");
  console.log("=" .repeat(60));

  try {
    // Шаг 1: Проверка подключения к PostgreSQL
    if (verbose) {
      console.log("📋 Этап 1: Проверка подключения к PostgreSQL...");
    }
    
    const connectionWorking = await testConnection();
    if (!connectionWorking) {
      throw new Error("❌ Не удалось подключиться к PostgreSQL. Проверьте настройки.");
    }
    
    if (verbose) {
      console.log("✅ Подключение к PostgreSQL работает корректно");
    }

    // Шаг 2: Удаление базы данных (если требуется)
    if (dropDatabase) {
      if (verbose) {
        console.log("📋 Этап 2: Удаление существующей базы данных...");
      }
      
      await dropDatabaseIfExists();
      
      if (verbose) {
        console.log("✅ База данных успешно удалена");
      }
    }

    // Шаг 3: Создание базы данных
    if (verbose) {
      console.log("📋 Этап 3: Создание новой базы данных...");
    }
    
    const dbCreated = await createDatabaseIfNotExists();
    if (!dbCreated) {
      throw new Error("❌ Не удалось создать базу данных");
    }
    
    if (verbose) {
      console.log("✅ База данных создана или уже существует");
    }

    // Шаг 4: Применение миграций
    if (runMigrations) {
      if (verbose) {
        console.log("📋 Этап 4: Применение миграций схемы...");
      }
      
      await runDatabaseMigrations();
      
      if (verbose) {
        console.log("✅ Миграции успешно применены");
      }
    }

    // Шаг 5: Валидация схемы
    if (verbose) {
      console.log("📋 Этап 5: Валидация целостности схемы...");
    }
    
    await validateDatabaseSchema();
    
    if (verbose) {
      console.log("✅ Схема базы данных корректна");
    }

    // Шаг 6: Заполнение тестовыми данными
    if (seedData) {
      if (verbose) {
        console.log("📋 Этап 6: Заполнение тестовыми данными...");
      }
      
      await seedDatabaseData();
      
      if (verbose) {
        console.log("✅ Тестовые данные успешно загружены");
      }
    }

    // Финальная проверка
    if (verbose) {
      console.log("📋 Этап 7: Финальная проверка системы...");
    }
    
    await performFinalValidation();
    
    console.log("=" .repeat(60));
    console.log("🎉 БАЗА ДАННЫХ ПОЛНОСТЬЮ ВОССТАНОВЛЕНА!");
    console.log("✅ Все компоненты работают корректно");
    console.log("🌐 База готова к использованию");
    console.log("=" .repeat(60));
    
    return true;
  } catch (error: any) {
    console.error("=" .repeat(60));
    console.error("❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ СБРОСЕ БАЗЫ ДАННЫХ");
    console.error("=" .repeat(60));
    console.error(`🔥 Ошибка: ${error.message}`);
    console.error(`📍 Стек: ${error.stack}`);
    console.error("=" .repeat(60));
    
    // Предложения по устранению
    console.error("🔧 РЕКОМЕНДАЦИИ ПО УСТРАНЕНИЮ:");
    console.error("1. Проверьте, что PostgreSQL запущен: net start postgresql*");
    console.error("2. Проверьте права доступа к базе данных");
    console.error("3. Убедитесь, что порт 5432 не заблокирован");
    console.error("4. Проверьте файл .env на корректность настроек");
    console.error("=" .repeat(60));
    
    return false;
  } finally {
    // Закрытие всех соединений
    try {
      await queryClient.end();
      await migrationClient.end();
    } catch (e) {
      // Игнорируем ошибки закрытия соединений
    }
  }
}

/**
 * Удаление базы данных, если она существует
 */
async function dropDatabaseIfExists(): Promise<void> {
  let adminClient: any = null;
  
  try {
    const connectionString = process.env.DATABASE_URL!;
    const dbName = new URL(connectionString).pathname.slice(1);
    const adminConnectionString = connectionString.replace(`/${dbName}`, '/postgres');
    
    // Импорт postgres
    const postgres = (await import('postgres')).default;
    adminClient = postgres(adminConnectionString, { max: 1 });
    
    console.log(`🗑️  Удаление базы данных '${dbName}'...`);
    
    // Завершаем все активные соединения с базой данных
    await adminClient.unsafe(`
      SELECT pg_terminate_backend(pg_stat_activity.pid)
      FROM pg_stat_activity
      WHERE pg_stat_activity.datname = '${dbName}' 
        AND pid <> pg_backend_pid()
    `);
    
    // Удаляем базу данных
    await adminClient.unsafe(`DROP DATABASE IF EXISTS "${dbName}"`);
    
    console.log(`✅ База данных '${dbName}' удалена`);
  } catch (error: any) {
    console.error(`❌ Ошибка удаления базы данных: ${error.message}`);
    throw error;
  } finally {
    if (adminClient) {
      try {
        await adminClient.end();
      } catch (e) {
        // Игнорируем ошибки закрытия
      }
    }
  }
}

/**
 * Применение миграций базы данных
 */
async function runDatabaseMigrations(): Promise<void> {
  try {
    console.log("📋 Применение миграций...");
    
    // Используем Bun для выполнения миграций
    const { stdout, stderr } = await execAsync(
      "bun run migrate",
      { cwd: process.cwd() }
    );
    
    if (stderr && !stderr.includes("warning")) {
      console.warn("⚠️  Предупреждения при миграции:", stderr);
    }
    
    if (stdout) {
      console.log("📄 Результат миграции:", stdout);
    }
    
    console.log("✅ Миграции применены успешно");
  } catch (error: any) {
    console.error("❌ Ошибка применения миграций:", error.message);
    throw error;
  }
}

/**
 * Валидация схемы базы данных
 */
async function validateDatabaseSchema(): Promise<void> {
  try {
    // Проверяем, что все основные таблицы созданы
    const requiredTables = [
      'users', 'customers', 'orders', 'order_goods',
      'subscription_features', 'user_subscriptions',
      'stories', 'blog_categories', 'verification_tokens',
      'config', 'email_templates', 'faqs'
    ];
    
    console.log("🔍 Проверка существования основных таблиц...");
    
    for (const table of requiredTables) {
      const result = await queryClient`
        SELECT EXISTS (
          SELECT FROM information_schema.tables 
          WHERE table_name = ${table}
        )
      `;
      
      if (!result[0]?.exists) {
        throw new Error(`❌ Таблица '${table}' не найдена`);
      }
    }
    
    // Проверяем, что в таблице users есть столбец registration_method
    console.log("🔍 Проверка структуры таблицы users...");
    
    const columnCheck = await queryClient`
      SELECT column_name 
      FROM information_schema.columns 
      WHERE table_name = 'users' AND column_name = 'registration_method'
    `;
    
    if (columnCheck.length === 0) {
      throw new Error("❌ Столбец 'registration_method' отсутствует в таблице users");
    }
    
    console.log("✅ Структура базы данных корректна");
  } catch (error: any) {
    console.error("❌ Ошибка валидации схемы:", error.message);
    throw error;
  }
}

/**
 * Заполнение базы данных тестовыми данными
 */
async function seedDatabaseData(): Promise<void> {
  try {
    console.log("🌱 Заполнение тестовыми данными...");
    
    const { stdout, stderr } = await execAsync(
      "bun run seed",
      { cwd: process.cwd() }
    );
    
    if (stderr && !stderr.includes("warning")) {
      console.warn("⚠️  Предупреждения при заполнении:", stderr);
    }
    
    if (stdout) {
      console.log("📄 Результат заполнения:", stdout);
    }
    
    console.log("✅ Тестовые данные загружены успешно");
  } catch (error: any) {
    console.error("❌ Ошибка заполнения данными:", error.message);
    throw error;
  }
}

/**
 * Финальная валидация системы
 */
async function performFinalValidation(): Promise<void> {
  try {
    console.log("🎯 Финальная проверка работоспособности...");
    
    // Проверяем количество созданных записей
    const userCount = await queryClient`SELECT COUNT(*) FROM users`;
    const orderCount = await queryClient`SELECT COUNT(*) FROM orders`;
    const configCount = await queryClient`SELECT COUNT(*) FROM config`;
    
    console.log(`👥 Пользователи: ${userCount[0]?.count || 0}`);
    console.log(`📦 Заказы: ${orderCount[0]?.count || 0}`);
    console.log(`⚙️  Настройки: ${configCount[0]?.count || 0}`);
    
    if (Number(userCount[0]?.count || 0) < 2) {
      throw new Error("❌ Недостаточно тестовых пользователей");
    }
    
    if (Number(configCount[0]?.count || 0) < 5) {
      throw new Error("❌ Недостаточно конфигурационных данных");
    }
    
    console.log("✅ Система полностью работоспособна");
  } catch (error: any) {
    console.error("❌ Ошибка финальной валидации:", error.message);
    throw error;
  }
}

// Запуск скрипта, если файл выполняется напрямую
if (import.meta.main) {
  resetDatabase({
    dropDatabase: true,
    runMigrations: true,
    seedData: true,
    verbose: true
  }).then((success) => {
    process.exit(success ? 0 : 1);
  });
}