import { queryClient } from "./connection";

/**
 * Система валидации схемы базы данных
 * Senior-level подход: проверка целостности, консистентности и производительности
 */

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  summary: {
    tablesFound: number;
    columnsChecked: number;
    indexesValidated: number;
    constraintsVerified: number;
  };
}

export interface TableDefinition {
  name: string;
  requiredColumns: string[];
  requiredIndexes?: string[];
  requiredConstraints?: string[];
  customChecks?: ((tableName: string) => Promise<string[]>)[];
}

/**
 * Определение ожидаемой структуры базы данных
 */
const EXPECTED_SCHEMA: TableDefinition[] = [
  {
    name: "users",
    requiredColumns: [
      "id", "email", "phone", "password", "registration_method",
      "name", "full_name", "role", "status", "email_verified",
      "phone_verified", "created_at", "updated_at"
    ],
    requiredIndexes: [
      "users_email_unique_idx", "users_phone_unique_idx"
    ],
    requiredConstraints: [
      "users_email_or_phone_required"
    ],
    customChecks: [validateUsersLogic]
  },
  {
    name: "customers",
    requiredColumns: [
      "id", "name", "email", "phone", "created_at", "updated_at"
    ]
  },
  {
    name: "orders",
    requiredColumns: [
      "id", "nomerok", "user_id", "customer_id", "customer_name",
      "customer_phone", "delivery_address", "status", "total_yuan",
      "total_ruble", "created_at", "updated_at"
    ],
    requiredConstraints: [
      "orders_nomerok_unique"
    ]
  },
  {
    name: "order_goods",
    requiredColumns: [
      "id", "order_id", "name", "quantity", "price_yuan", 
      "commission", "total_yuan", "total_ruble"
    ]
  },
  {
    name: "subscription_features",
    requiredColumns: [
      "id", "tier", "max_storage_days", "processing_time_hours",
      "support_response_hours", "description"
    ]
  },
  {
    name: "user_subscriptions",
    requiredColumns: [
      "id", "user_id", "tier", "status", "price", "start_date",
      "end_date", "auto_renew"
    ]
  },
  {
    name: "stories",
    requiredColumns: [
      "id", "title", "link", "content", "status", "author_id", "created_at"
    ],
    requiredConstraints: [
      "stories_link_unique"
    ]
  },
  {
    name: "blog_categories",
    requiredColumns: [
      "id", "name", "slug", "description", "color", "order", "is_active"
    ]
  },
  {
    name: "verification_tokens",
    requiredColumns: [
      "id", "user_id", "type", "status", "email", "phone", "token",
      "code", "expires_at", "created_at"
    ],
    requiredIndexes: [
      "verification_tokens_token_idx", "verification_tokens_type_status_idx"
    ]
  },
  {
    name: "config",
    requiredColumns: [
      "id", "key", "value", "description", "type", "created_at", "updated_at"
    ],
    requiredConstraints: [
      "config_key_unique"
    ]
  }
];

/**
 * Главная функция валидации схемы
 */
export async function validateDatabaseSchema(): Promise<ValidationResult> {
  const result: ValidationResult = {
    valid: true,
    errors: [],
    warnings: [],
    summary: {
      tablesFound: 0,
      columnsChecked: 0,
      indexesValidated: 0,
      constraintsVerified: 0
    }
  };

  console.log("🔍 Начинаю комплексную валидацию схемы базы данных...");

  try {
    // Этап 1: Проверка существования таблиц
    console.log("📋 Этап 1: Проверка основных таблиц...");
    await validateTables(result);

    // Этап 2: Проверка структуры столбцов
    console.log("📋 Этап 2: Проверка структуры столбцов...");
    await validateColumns(result);

    // Этап 3: Проверка индексов
    console.log("📋 Этап 3: Проверка индексов производительности...");
    await validateIndexes(result);

    // Этап 4: Проверка ограничений
    console.log("📋 Этап 4: Проверка ограничений целостности...");
    await validateConstraints(result);

    // Этап 5: Проверка ENUM типов
    console.log("📋 Этап 5: Проверка ENUM типов...");
    await validateEnums(result);

    // Этап 6: Бизнес-логические проверки
    console.log("📋 Этап 6: Проверка бизнес-логики...");
    await validateBusinessLogic(result);

    // Этап 7: Проверка производительности
    console.log("📋 Этап 7: Анализ производительности...");
    await validatePerformance(result);

  } catch (error: any) {
    result.errors.push(`Критическая ошибка валидации: ${error.message}`);
    result.valid = false;
  }

  // Определение общего результата
  result.valid = result.errors.length === 0;

  // Вывод отчёта
  printValidationReport(result);

  return result;
}

/**
 * Проверка существования всех необходимых таблиц
 */
async function validateTables(result: ValidationResult): Promise<void> {
  try {
    const existingTables = await queryClient`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public'
    `;

    const existingTableNames = existingTables.map(t => t.table_name);
    result.summary.tablesFound = existingTableNames.length;

    for (const tableDef of EXPECTED_SCHEMA) {
      if (!existingTableNames.includes(tableDef.name)) {
        result.errors.push(`❌ Отсутствует таблица: ${tableDef.name}`);
      } else {
        console.log(`✅ Таблица найдена: ${tableDef.name}`);
      }
    }

    // Проверка на лишние таблицы (могут быть системные)
    const expectedTableNames = EXPECTED_SCHEMA.map(t => t.name);
    const extraTables = existingTableNames.filter(t => 
      !expectedTableNames.includes(t) && 
      !t.startsWith('drizzle') && 
      !t.startsWith('_')
    );

    if (extraTables.length > 0) {
      result.warnings.push(`⚠️  Дополнительные таблицы: ${extraTables.join(', ')}`);
    }

  } catch (error: any) {
    result.errors.push(`Ошибка проверки таблиц: ${error.message}`);
  }
}

/**
 * Проверка структуры столбцов
 */
async function validateColumns(result: ValidationResult): Promise<void> {
  try {
    for (const tableDef of EXPECTED_SCHEMA) {
      const columns = await queryClient`
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = ${tableDef.name}
        ORDER BY ordinal_position
      `;

      const existingColumns = columns.map(c => c.column_name);
      result.summary.columnsChecked += existingColumns.length;

      for (const requiredColumn of tableDef.requiredColumns) {
        if (!existingColumns.includes(requiredColumn)) {
          result.errors.push(`❌ Отсутствует столбец '${requiredColumn}' в таблице '${tableDef.name}'`);
        }
      }

      console.log(`✅ Проверены столбцы таблицы: ${tableDef.name} (${existingColumns.length} столбцов)`);
    }
  } catch (error: any) {
    result.errors.push(`Ошибка проверки столбцов: ${error.message}`);
  }
}

/**
 * Проверка индексов
 */
async function validateIndexes(result: ValidationResult): Promise<void> {
  try {
    const indexes = await queryClient`
      SELECT indexname, tablename 
      FROM pg_indexes 
      WHERE schemaname = 'public'
    `;

    const existingIndexes = indexes.map(i => i.indexname);
    result.summary.indexesValidated = existingIndexes.length;

    for (const tableDef of EXPECTED_SCHEMA) {
      if (tableDef.requiredIndexes) {
        for (const requiredIndex of tableDef.requiredIndexes) {
          if (!existingIndexes.includes(requiredIndex)) {
            result.errors.push(`❌ Отсутствует индекс: ${requiredIndex}`);
          } else {
            console.log(`✅ Найден индекс: ${requiredIndex}`);
          }
        }
      }
    }
  } catch (error: any) {
    result.errors.push(`Ошибка проверки индексов: ${error.message}`);
  }
}

/**
 * Проверка ограничений (constraints)
 */
async function validateConstraints(result: ValidationResult): Promise<void> {
  try {
    const constraints = await queryClient`
      SELECT constraint_name, table_name, constraint_type
      FROM information_schema.table_constraints
      WHERE table_schema = 'public'
    `;

    const existingConstraints = constraints.map(c => c.constraint_name);
    result.summary.constraintsVerified = existingConstraints.length;

    for (const tableDef of EXPECTED_SCHEMA) {
      if (tableDef.requiredConstraints) {
        for (const requiredConstraint of tableDef.requiredConstraints) {
          if (!existingConstraints.includes(requiredConstraint)) {
            result.errors.push(`❌ Отсутствует ограничение: ${requiredConstraint}`);
          } else {
            console.log(`✅ Найдено ограничение: ${requiredConstraint}`);
          }
        }
      }
    }
  } catch (error: any) {
    result.errors.push(`Ошибка проверки ограничений: ${error.message}`);
  }
}

/**
 * Проверка ENUM типов
 */
async function validateEnums(result: ValidationResult): Promise<void> {
  try {
    const requiredEnums = [
      'user_role', 'user_status', 'registration_method',
      'order_status', 'story_status', 'subscription_tier',
      'subscription_status', 'verification_type', 'config_type'
    ];

    const existingEnums = await queryClient`
      SELECT typname FROM pg_type WHERE typtype = 'e'
    `;

    const existingEnumNames = existingEnums.map(e => e.typname);

    for (const requiredEnum of requiredEnums) {
      if (!existingEnumNames.includes(requiredEnum)) {
        result.errors.push(`❌ Отсутствует ENUM тип: ${requiredEnum}`);
      } else {
        console.log(`✅ Найден ENUM: ${requiredEnum}`);
      }
    }
  } catch (error: any) {
    result.errors.push(`Ошибка проверки ENUM типов: ${error.message}`);
  }
}

/**
 * Проверка бизнес-логики
 */
async function validateBusinessLogic(result: ValidationResult): Promise<void> {
  try {
    for (const tableDef of EXPECTED_SCHEMA) {
      if (tableDef.customChecks) {
        for (const check of tableDef.customChecks) {
          const checkErrors = await check(tableDef.name);
          result.errors.push(...checkErrors);
        }
      }
    }
  } catch (error: any) {
    result.errors.push(`Ошибка проверки бизнес-логики: ${error.message}`);
  }
}

/**
 * Проверка производительности
 */
async function validatePerformance(result: ValidationResult): Promise<void> {
  try {
    // Проверяем размеры таблиц
    const tableSizes = await queryClient`
      SELECT 
        schemaname,
        tablename,
        attname,
        n_distinct,
        correlation
      FROM pg_stats 
      WHERE schemaname = 'public'
      LIMIT 10
    `;

    if (tableSizes.length > 0) {
      console.log(`📊 Статистика таблиц: ${tableSizes.length} записей`);
    } else {
      result.warnings.push("⚠️  Статистика таблиц недоступна, возможно база пуста");
    }

  } catch (error: any) {
    result.warnings.push(`Предупреждение при анализе производительности: ${error.message}`);
  }
}

/**
 * Кастомная проверка для таблицы users
 */
async function validateUsersLogic(tableName: string): Promise<string[]> {
  const errors: string[] = [];
  
  try {
    // Проверяем, что у всех пользователей есть email ИЛИ phone
    const invalidUsers = await queryClient.unsafe(`
      SELECT COUNT(*) 
      FROM ${tableName}
      WHERE (email IS NULL OR email = '') AND (phone IS NULL OR phone = '')
    `);

    if (Number(invalidUsers[0]?.count || 0) > 0) {
      errors.push(`❌ Найдены пользователи без email и phone: ${invalidUsers[0]?.count}`);
    }

    // Проверяем соответствие registration_method и фактических данных
    const inconsistentUsers = await queryClient.unsafe(`
      SELECT COUNT(*) 
      FROM ${tableName}
      WHERE (registration_method = 'email' AND (email IS NULL OR email = ''))
         OR (registration_method = 'phone' AND (phone IS NULL OR phone = ''))
    `);

    if (Number(inconsistentUsers[0]?.count || 0) > 0) {
      errors.push(`❌ Несоответствие registration_method данным: ${inconsistentUsers[0]?.count} пользователей`);
    }

  } catch (error: any) {
    errors.push(`Ошибка проверки логики users: ${error.message}`);
  }

  return errors;
}

/**
 * Красивый вывод отчёта валидации
 */
function printValidationReport(result: ValidationResult): void {
  console.log("=" .repeat(70));
  console.log("📊 ОТЧЁТ ВАЛИДАЦИИ СХЕМЫ БАЗЫ ДАННЫХ");
  console.log("=" .repeat(70));

  // Общий статус
  if (result.valid) {
    console.log("🎉 СТАТУС: ✅ СХЕМА КОРРЕКТНА");
  } else {
    console.log("⚠️  СТАТУС: ❌ НАЙДЕНЫ ПРОБЛЕМЫ");
  }

  console.log();

  // Сводка
  console.log("📈 СВОДКА:");
  console.log(`   📋 Таблиц найдено: ${result.summary.tablesFound}`);
  console.log(`   📋 Столбцов проверено: ${result.summary.columnsChecked}`);
  console.log(`   📋 Индексов валидировано: ${result.summary.indexesValidated}`);
  console.log(`   📋 Ограничений проверено: ${result.summary.constraintsVerified}`);

  console.log();

  // Ошибки
  if (result.errors.length > 0) {
    console.log("❌ КРИТИЧЕСКИЕ ОШИБКИ:");
    result.errors.forEach(error => console.log(`   ${error}`));
    console.log();
  }

  // Предупреждения
  if (result.warnings.length > 0) {
    console.log("⚠️  ПРЕДУПРЕЖДЕНИЯ:");
    result.warnings.forEach(warning => console.log(`   ${warning}`));
    console.log();
  }

  console.log("=" .repeat(70));
}

// Запуск валидации, если файл выполняется напрямую
if (import.meta.main) {
  validateDatabaseSchema().then(result => {
    process.exit(result.valid ? 0 : 1);
  });
}