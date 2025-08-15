# 🚀 Руководство по запуску YuYu Lolita v2 на Windows

Пошаговая инструкция для запуска проекта YuYu Lolita Shopping v2 на Windows 10/11.

## 📋 Предварительные требования

### 1. Git для Windows
- Скачайте и установите [Git for Windows](https://git-scm.com/download/win)
- ✅ Проверка: `git --version` в PowerShell

### 2. Docker Desktop для Windows
- Скачайте и установите [Docker Desktop](https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe)
- Запустите Docker Desktop и дождитесь полной загрузки
- ✅ Проверка: `docker --version` в PowerShell

### 3. Bun (JavaScript Runtime)
**Вариант A: Через PowerShell (Рекомендуется)**
```powershell
# Запустите PowerShell от имени администратора
irm bun.sh/install.ps1 | iex
```

**Вариант B: Скачать установщик**
- Перейдите на [bun.sh](https://bun.sh/) 
- Скачайте Windows installer (.exe)
- Запустите установщик

**Вариант C: Через npm (если у вас есть Node.js)**
```powershell
npm install -g bun
```

✅ **Проверка установки:** `bun --version`

### 4. Visual Studio Code (Опционально, но рекомендуется)
- Скачайте [VS Code](https://code.visualstudio.com/)
- Установите расширения: TypeScript, Svelte, Tailwind CSS

---

## 🛠️ Настройка проекта

### Шаг 1: Клонирование репозитория
```powershell
# Создайте папку для проектов (если нет)
mkdir C:\Projects
cd C:\Projects

# Клонируйте репозиторий
git clone <YOUR_REPOSITORY_URL> yuyu-lolita-v2
cd yuyu-lolita-v2
```

### Шаг 2: Настройка переменных окружения
```powershell
# Скопируйте файл конфигурации
copy .env.example .env

# Отредактируйте .env файл в блокноте или VS Code
notepad .env
# ИЛИ
code .env
```

**🔧 Важные настройки в .env файле:**
```env
# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/yuyu_lolita

# Redis Configuration  
REDIS_URL=redis://localhost:6379

# JWT Configuration
JWT_SECRET=ваш-секретный-ключ-измените-это

# API Configuration
API_PORT=3001
API_HOST=localhost

# Web App Configuration
PUBLIC_API_URL=http://localhost:3001
```

### Шаг 3: Установка зависимостей
```powershell
# Установите зависимости для всего проекта
bun install
```

---

## 🐳 Запуск базы данных

### Шаг 1: Проверка Docker
```powershell
# Убедитесь что Docker Desktop запущен
docker --version
docker ps
```

### Шаг 2: Запуск PostgreSQL и Redis
```powershell
# Запустите базы данных в фоновом режиме
docker-compose up -d postgres redis

# Проверьте что контейнеры работают
docker ps
```

**Ожидаемый результат:**
```
CONTAINER ID   IMAGE                COMMAND                  CREATED         STATUS          PORTS                    NAMES
xxxxxxxxxx     postgres:15-alpine   "docker-entrypoint.s…"   2 minutes ago   Up 2 minutes   0.0.0.0:5432->5432/tcp   yuyu-postgres  
xxxxxxxxxx     redis:7-alpine       "docker-entrypoint.s…"   2 minutes ago   Up 2 minutes   0.0.0.0:6379->6379/tcp   yuyu-redis
```

### Шаг 3: Проверка здоровья PostgreSQL
```powershell
# Дождитесь пока PostgreSQL станет здоровым (healthy)
docker ps | findstr postgres
```

---

## 📦 Сборка пакетов

### Шаг 1: Сборка shared пакета
```powershell
cd packages\shared
bun run build
cd ..\..
```

### Шаг 2: Сборка db пакета  
```powershell
cd packages\db
bun run build
cd ..\..
```

### Шаг 3: Запуск миграций базы данных
```powershell
# Применить миграции к базе данных
bun --filter=@yuyu/db run migrate
```

**Ожидаемый результат:**
```
@yuyu/db migrate: 🔄 Running database migrations...
@yuyu/db migrate: ✅ Migrations completed successfully
```

---

## 🚀 Запуск приложения

### Вариант 1: Запуск всех сервисов сразу
```powershell
# Запустите API и Web одновременно
bun run dev
```

### Вариант 2: Запуск сервисов отдельно

**В первом окне PowerShell (API Server):**
```powershell
cd apps\api
bun run dev
```

**Во втором окне PowerShell (Web App):**
```powershell
cd apps\web  
bun run dev
```

---

## ✅ Проверка работы

Если все настроено правильно, вы увидите:

**🔥 API Server (Terminal 1):**
```
🔄 Initializing database connection...
🚀 YuYu Lolita Shopping API (DB) is running on http://localhost:3001
📚 Swagger documentation: http://localhost:3001/swagger
✅ Database connection successful
```

**🌐 Web App (Terminal 2):**
```
VITE v5.4.19  ready in 1540 ms

➜  Local:   http://localhost:5173/
➜  Network: http://10.0.0.226:5173/
```

### Откройте в браузере:
- **📱 Веб-приложение**: http://localhost:5173
- **🔌 API**: http://localhost:3001  
- **📚 API Документация**: http://localhost:3001/swagger
- **🗄️ Adminer (Database UI)**: http://localhost:8080

---

## 🐛 Решение проблем

### Проблема: "bun: command not found"
**Решение:**
1. Перезапустите PowerShell
2. Проверьте PATH: `$env:PATH`
3. Переустановите Bun от имени администратора

### Проблема: "Docker is not running"
**Решение:**
1. Запустите Docker Desktop
2. Дождитесь полной загрузки (иконка Docker в трее)
3. Попробуйте снова: `docker ps`

### Проблема: "Port already in use"
**Решение:**
```powershell
# Найти процессы на портах 3001, 5173
netstat -ano | findstr :3001
netstat -ano | findstr :5173

# Завершить процесс (замените PID на реальный номер)
taskkill /PID <номер_процесса> /F
```

### Проблема: "Cannot connect to database"
**Решения:**
1. Убедитесь что PostgreSQL контейнер запущен: `docker ps`
2. Проверьте логи: `docker logs yuyu-postgres`
3. Перезапустите контейнер: 
   ```powershell
   docker-compose down
   docker-compose up -d postgres redis
   ```

### Проблема: Workspace packages не найдены
**Решение:**
```powershell
# Пересоберите пакеты
cd packages\shared && bun run build && cd ..\..
cd packages\db && bun run build && cd ..\..

# Переустановите зависимости
bun install
```

---

## 🔧 Полезные команды

### Управление Docker контейнерами
```powershell
# Запуск всех сервисов
docker-compose up -d

# Остановка всех сервисов  
docker-compose down

# Просмотр логов
docker-compose logs postgres
docker-compose logs redis

# Перезапуск сервиса
docker-compose restart postgres
```

### Управление базой данных
```powershell
# Миграции
bun --filter=@yuyu/db run migrate

# Заполнение тестовыми данными
bun --filter=@yuyu/db run seed

# Drizzle Studio (Database UI)
bun --filter=@yuyu/db run studio
```

### Сборка для продакшна
```powershell
# Сборка всех приложений
bun run build

# Запуск продакшн версии
bun run start
```

---

## 🚨 Важные замечания

1. **Антивирус**: Добавьте папку проекта в исключения антивируса
2. **Firewall**: Разрешите порты 3001, 5173, 5432, 6379 в брандмауэре Windows
3. **WSL2**: Если используете WSL2, убедитесь что Docker Desktop настроен для WSL2
4. **PowerShell Execution Policy**: Если скрипты не выполняются:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

---

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте все предварительные требования  
2. Перезапустите PowerShell от имени администратора
3. Проверьте логи Docker: `docker-compose logs`
4. Создайте issue с подробным описанием ошибки

**Сделано с ❤️ для YuYu Lolita Shopping**