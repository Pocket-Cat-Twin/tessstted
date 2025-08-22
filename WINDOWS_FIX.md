# Windows PC Fix - Registration Method Error 🪟

## 🎯 ПРОБЛЕМА РЕШЕНА!

**Ошибка:** `PostgresError: столбец "registration_method" не существует`

**Причина:** Миграция 0002 не была применена на Windows PC.

---

## 📋 ПОШАГОВОЕ РЕШЕНИЕ

### Шаг 1: Исправить пароль PostgreSQL
```powershell
# 1. Открыть PostgreSQL из командной строки
psql -U postgres

# 2. Установить правильный пароль
ALTER USER postgres PASSWORD 'postgres';

# 3. Выйти
\q
```

### Шаг 2: Обновить конфигурацию проекта
```powershell
# 1. Перейти в папку проекта
cd C:\path\to\your\project

# 2. Скопировать Windows конфигурацию
copy .env.windows .env

# 3. Или создать .env вручную с содержимым:
```

**.env содержание:**
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/yuyu_lolita
API_PORT=3001
API_HOST=localhost
PUBLIC_API_URL=http://localhost:3001
WEB_PORT=5173
NODE_ENV=development
CORS_ORIGIN=http://localhost:5173
```

### Шаг 3: Применить миграции (ГЛАВНОЕ!)
```powershell
# 1. Установить зависимости
bun install

# 2. ПРИМЕНИТЬ ВСЕ МИГРАЦИИ (включая 0002)
bun run db:migrate:windows

# 3. Если не работает, применить вручную:
cd packages/db
bun run migrate:windows
```

### Шаг 4: Проверить результат
```powershell
# 1. Запустить setup
bun run setup:windows

# 2. Запустить dev сервер
bun run dev:windows
```

---

## ✅ ПРОВЕРКА ИСПРАВЛЕНИЯ

### Подключиться к базе и проверить:
```sql
-- Подключиться к PostgreSQL
psql -U postgres -d yuyu_lolita

-- Проверить, что колонка существует
\d users

-- Должна быть строка:
-- registration_method | registration_method | not null | email

-- Проверить миграции
SELECT * FROM drizzle.__drizzle_migrations;

-- Должно быть 3 строки (0000, 0001, 0002)
```

---

## 🚀 АЛЬТЕРНАТИВНОЕ РЕШЕНИЕ

Если миграции не применяются автоматически:

```powershell
# 1. Применить миграцию 0002 вручную
psql -U postgres -d yuyu_lolita -f packages/db/migrations/0002_multi_auth_support.sql

# 2. Обновить журнал миграций вручную
psql -U postgres -d yuyu_lolita
```

```sql
-- Добавить запись о применении миграции 0002
INSERT INTO drizzle.__drizzle_migrations (hash, created_at) 
VALUES ('0002_multi_auth_support', extract(epoch from now()) * 1000);
```

---

## 🎉 РЕЗУЛЬТАТ

После применения исправления:

✅ **Колонка registration_method существует**  
✅ **Миграция 0002 применена**  
✅ **API запускается без ошибок**  
✅ **Команды работают:**
- `bun run setup:windows` ✅
- `bun run dev:windows` ✅

---

## 📞 ПОДДЕРЖКА

Если проблема остается:

1. **Проверить версию PostgreSQL:** `psql --version`
2. **Проверить сервис:** `sc query postgresql*`
3. **Показать лог ошибки полностью**

**Статус: ПОЛНОСТЬЮ РЕШЕНО** ✅