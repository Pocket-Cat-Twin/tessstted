# 🎀 YuYu Lolita Shopping - Полная инструкция по запуску с нуля на Windows

Полное руководство по установке и запуску проекта YuYu Lolita Shopping на Windows 10/11 с самого начала.

## 📋 Системные требования

### Минимальные требования
- **ОС**: Windows 10 (версия 1903+) или Windows 11
- **Архитектура**: x64 (64-битная)
- **ОЗУ**: минимум 8 ГБ (рекомендуется 16 ГБ)
- **Свободное место**: минимум 5 ГБ
- **Интернет**: стабильное соединение для загрузки зависимостей

### Предустановленные компоненты Windows
- **PowerShell 5.1+** (встроен в Windows)
- **Windows Terminal** (рекомендуется, но не обязательно)
- **Git for Windows** (для клонирования репозитория)

---

## 🛠️ ЭТАП 1: Установка базового ПО

### 1.1 Установка Git (если не установлен)

**Скачайте и установите Git:**
```powershell
# Скачать с официального сайта
# https://git-scm.com/download/win

# Или через winget (если доступен)
winget install Git.Git
```

**Проверка установки:**
```powershell
git --version
```

### 1.2 Установка Node.js (базовая зависимость)

**Вариант 1: С официального сайта**
1. Перейдите на https://nodejs.org/
2. Скачайте LTS версию
3. Запустите установщик и следуйте инструкциям

**Вариант 2: Через winget**
```powershell
winget install OpenJS.NodeJS
```

**Проверка установки:**
```powershell
node --version
npm --version
```

### 1.3 Установка Bun Runtime

**Автоматическая установка (рекомендуется):**
```powershell
# Запустите PowerShell от имени Администратора
irm bun.sh/install.ps1 | iex
```

**Ручная установка:**
1. Скачайте с https://bun.sh/
2. Распакуйте в папку (например, `C:\bun`)
3. Добавьте в переменную PATH

**Проверка установки:**
```powershell
# Перезапустите PowerShell
bun --version
```

### 1.4 Установка MySQL 8.0

**Вариант 1: Официальный установщик (рекомендуется)**
1. Скачайте MySQL Installer с https://dev.mysql.com/downloads/installer/
2. Запустите `mysql-installer-web-community-*.msi`
3. Выберите "Developer Default" или "Custom"
4. Установите MySQL Server 8.0
5. Настройте root пользователя (запомните пароль!)

**Вариант 2: Через Chocolatey**
```powershell
# Установите Chocolatey сначала (если нет)
Set-ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Установите MySQL
choco install mysql
```

**Вариант 3: Через winget**
```powershell
winget install Oracle.MySQL
```

**Проверка установки MySQL:**
```powershell
# Проверить службу
Get-Service -Name "MySQL*"

# Проверить команду
mysql --version

# Запустить службу (если не запущена)
net start MySQL80
```

---

## 🚀 ЭТАП 2: Получение и подготовка проекта

### 2.1 Клонирование репозитория

```powershell
# Перейдите в папку для проектов (например, C:\Projects)
cd C:\
mkdir Projects
cd Projects

# Клонируйте репозиторий
git clone https://github.com/your-username/yuyu-lolita-shopping.git
cd yuyu-lolita-shopping

# Или если репозиторий локальный
git clone <URL_вашего_репозитория> yuyu-lolita-shopping
cd yuyu-lolita-shopping
```

### 2.2 Первичный осмотр проекта

```powershell
# Просмотр структуры проекта
ls
cat README.md
cat package.json
```

---

## ⚙️ ЭТАП 3: Настройка окружения

### 3.1 Настройка политики выполнения PowerShell

```powershell
# Проверить текущую политику
Get-ExecutionPolicy

# Установить политику для текущего пользователя (безопасно)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Или для всей системы (требует права Администратора)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
```

### 3.2 Автоматическая настройка (быстрый способ)

```powershell
# Убедитесь, что находитесь в корне проекта
pwd

# Запустите автоматическую настройку
bun run setup:windows
```

**Что делает команда setup:windows:**
- ✅ Проверяет наличие Bun и MySQL
- ✅ Устанавливает зависимости проекта
- ✅ Создает файл конфигурации (.env)
- ✅ Настраивает базу данных
- ✅ Запускает миграции
- ✅ Собирает пакеты

### 3.3 Ручная настройка (если автоматическая не сработала)

#### 3.3.1 Установка зависимостей

```powershell
# Установить зависимости проекта
bun install

# Если bun не работает, используйте npm
npm install
```

#### 3.3.2 Создание файла конфигурации

```powershell
# Создайте файл .env в корне проекта
New-Item -Path ".env" -ItemType File

# Откройте файл для редактирования
notepad .env
```

**Содержимое файла .env:**
```env
# Конфигурация API
API_HOST=localhost
API_PORT=3001
CORS_ORIGIN=http://localhost:5173

# Конфигурация веб-приложения
WEB_PORT=5173
HOST=0.0.0.0
PUBLIC_API_URL=http://localhost:3001

# Конфигурация базы данных MySQL8
DB_HOST=localhost
DB_PORT=3306
DB_NAME=yuyu_lolita
DB_USER=root
DB_PASSWORD=ваш_пароль_mysql

# Конфигурация JWT
JWT_SECRET=super-secret-jwt-key-change-in-production

# Окружение
NODE_ENV=development
SKIP_SEED=false

# Конфигурация электронной почты (опционально)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yuyulolita.com

# Конфигурация SMS (опционально)
SMS_PROVIDER=mock
SMS_RU_API_ID=your-sms-ru-api-id
SMS_RU_API_KEY=your-sms-ru-api-key
```

#### 3.3.3 Настройка базы данных MySQL

**Создание базы данных:**
```powershell
# Подключитесь к MySQL
mysql -u root -p

# В консоли MySQL выполните:
CREATE DATABASE yuyu_lolita CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit
```

**Запуск миграций:**
```powershell
# Настройка базы данных
bun run db:setup:mysql

# Или по отдельности:
bun run db:migrate:mysql
```

#### 3.3.4 Сборка пакетов

```powershell
# Сборка всех пакетов
bun run build:windows

# Или по отдельности:
cd packages/shared
bun run build
cd ../db
bun run build
cd ../..
```

---

## 🎯 ЭТАП 4: Запуск проекта

### 4.1 Режим разработки (Development)

**Автоматический запуск (рекомендуется):**
```powershell
# Запуск обеих служб в отдельных окнах
.\scripts\start-dev.ps1

# Или через bun скрипт
bun run dev:windows
```

**Ручной запуск:**

**Терминал 1 - API сервер:**
```powershell
cd apps/api
bun run dev:windows
```

**Терминал 2 - Веб-приложение:**
```powershell
cd apps/web
bun run dev:windows
```

### 4.2 Режим продакшен (Production)

```powershell
# Сборка проекта
bun run build:windows

# Запуск продакшен серверов
.\scripts\start-prod.ps1

# Или через bun скрипт
bun run start:windows
```

---

## 🌐 ЭТАП 5: Проверка работоспособности

### 5.1 URL для доступа

После успешного запуска будут доступны:

- **🎀 Веб-приложение**: http://localhost:5173
- **🔌 API сервер**: http://localhost:3001
- **📚 API документация**: http://localhost:3001/swagger

### 5.2 Тестирование API

```powershell
# Проверка здоровья API
curl http://localhost:3001/health

# Или через браузер
start http://localhost:3001/health
```

### 5.3 Тестирование веб-приложения

```powershell
# Открыть веб-приложение в браузере
start http://localhost:5173
```

---

## 🛠️ ЭТАП 6: Полезные команды для разработки

### 6.1 Управление базой данных

```powershell
# Создание новых миграций
bun run db:generate

# Применение миграций
bun run db:migrate:mysql

# Заполнение тестовыми данными
bun run db:seed:mysql

# Подключение к базе данных напрямую
mysql -u root -p yuyu_lolita
```

### 6.2 Управление службой MySQL

```powershell
# Запуск службы MySQL
net start MySQL80

# Остановка службы MySQL
net stop MySQL80

# Проверка статуса службы
sc query MySQL80

# Перезапуск службы
net stop MySQL80 && net start MySQL80
```

### 6.3 Разработка и отладка

```powershell
# Проверка качества кода
bun run lint

# Форматирование кода
bun run format

# Проверка типов TypeScript
bun run type-check

# Валидация всего проекта
bun run validate
```

---

## 🚨 УСТРАНЕНИЕ ПРОБЛЕМ

### 7.1 Проблемы с MySQL

**Проблема**: "MySQL service not found"
**Решение**:
```powershell
# Поиск всех служб MySQL
Get-Service -Name "*MySQL*"

# Проверка установки MySQL
Get-WmiObject -Class Win32_Product | Where-Object {$_.Name -like "*MySQL*"}

# Переустановка, если необходимо
winget install Oracle.MySQL
```

**Проблема**: "Access denied for user 'root'@'localhost'"
**Решение**:
```powershell
# Сброс пароля MySQL root
net stop MySQL80
mysqld --skip-grant-tables --skip-networking

# В новом терминале
mysql -u root
UPDATE mysql.user SET authentication_string=PASSWORD('новый_пароль') WHERE User='root';
FLUSH PRIVILEGES;
exit

# Перезапуск MySQL
net start MySQL80
```

### 7.2 Проблемы с портами

**Проблема**: "Port 3001/5173 already in use"
**Решение**:
```powershell
# Найти процессы, использующие порты
netstat -ano | findstr :3001
netstat -ano | findstr :5173

# Завершить процесс (замените PID на реальный номер)
taskkill /PID <номер_процесса> /F
```

### 7.3 Проблемы с Bun

**Проблема**: "bun command not found"
**Решение**:
```powershell
# Перезапуск PowerShell
exit

# Проверка переменной PATH
$env:PATH -split ";"

# Переустановка Bun
irm bun.sh/install.ps1 | iex
```

### 7.4 Проблемы с PowerShell

**Проблема**: "Execution Policy Error"
**Решение**:
```powershell
# Временное изменение политики
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# Или запуск конкретного скрипта
powershell -ExecutionPolicy Bypass -File "scripts\start-dev.ps1"
```

### 7.5 Проблемы с производительностью

**Решение**: Исключения Windows Defender
1. Откройте "Безопасность Windows"
2. Перейдите в "Защита от вирусов и угроз"
3. Управление параметрами в разделе "Параметры защиты от вирусов и других угроз"
4. Добавить исключение → Папка
5. Добавьте папки:
   - Корневая папка проекта
   - `node_modules/`
   - `apps/api/dist/`
   - `apps/web/build/`
   - `.bun/`

---

## 🔧 ДОПОЛНИТЕЛЬНАЯ НАСТРОЙКА

### 8.1 Настройка брандмауэра Windows

```powershell
# Разрешить порты через брандмауэр (запустите от имени Администратора)
netsh advfirewall firewall add rule name="YuYu API Port" dir=in action=allow protocol=TCP localport=3001
netsh advfirewall firewall add rule name="YuYu Web Port" dir=in action=allow protocol=TCP localport=5173
```

### 8.2 Создание ярлыков для быстрого запуска

**Создание bat-файлов для быстрого запуска:**

**start-dev.bat:**
```batch
@echo off
cd /d "C:\Projects\yuyu-lolita-shopping"
powershell -ExecutionPolicy Bypass -File "scripts\start-dev.ps1"
pause
```

**start-prod.bat:**
```batch
@echo off
cd /d "C:\Projects\yuyu-lolita-shopping"
powershell -ExecutionPolicy Bypass -File "scripts\start-prod.ps1"
pause
```

### 8.3 Автозапуск служб (опционально)

```powershell
# Настройка автозапуска MySQL
sc config MySQL80 start=auto

# Проверка настроек автозапуска
sc qc MySQL80
```

---

## 📊 МОНИТОРИНГ И ЛОГИ

### 9.1 Просмотр логов приложения

```powershell
# Логи находятся в папке logs/
ls logs/
Get-Content logs/api.log -Tail 50
Get-Content logs/web.log -Tail 50
```

### 9.2 Мониторинг процессов

```powershell
# Проверка запущенных процессов Bun и Node
Get-Process bun
Get-Process node

# Мониторинг использования портов
netstat -ano | findstr LISTEN

# Информация о системе
systeminfo | findstr /C:"Total Physical Memory"
```

### 9.3 Логи MySQL

```powershell
# Местоположение логов MySQL (обычно)
dir "C:\ProgramData\MySQL\MySQL Server 8.0\Data\*.err"

# Просмотр последних ошибок
Get-Content "C:\ProgramData\MySQL\MySQL Server 8.0\Data\*.err" -Tail 20
```

---

## 🔒 БЕЗОПАСНОСТЬ

### 10.1 Рекомендации для продакшена

**Изменить пароли и секреты в .env:**
```env
DB_PASSWORD=secure_mysql_password_here
JWT_SECRET=ultra-secure-jwt-secret-256-bit-minimum
SESSION_SECRET=ultra-secure-session-secret
```

**Настройки MySQL для продакшена:**
```sql
-- Создание отдельного пользователя для приложения
CREATE USER 'yuyu_app'@'localhost' IDENTIFIED BY 'secure_app_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON yuyu_lolita.* TO 'yuyu_app'@'localhost';
FLUSH PRIVILEGES;
```

### 10.2 Настройка HTTPS (для продакшена)

```powershell
# Создание самоподписанного сертификата для тестирования
New-SelfSignedCertificate -DnsName "localhost" -CertStoreLocation "cert:\LocalMachine\My"
```

---

## 🆘 ПОДДЕРЖКА И ДИАГНОСТИКА

### 11.1 Сбор информации для поддержки

```powershell
# Создание папки для диагностики
mkdir support-info
cd support-info

# Сбор информации о системе
systeminfo > system-info.txt
winver
$PSVersionTable > powershell-info.txt

# Сбор информации о проекте
bun --version > bun-info.txt 2>&1
node --version > node-info.txt 2>&1
mysql --version > mysql-info.txt 2>&1

# Сбор логов
copy ..\logs\*.log .

# Информация о службах
sc query MySQL80 > service-info.txt

# Информация о портах
netstat -ano > network-info.txt
```

### 11.2 Полезные команды диагностики

```powershell
# Проверка версии Windows
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion

# Проверка доступного места на диске
Get-PSDrive -PSProvider FileSystem

# Проверка настроек PowerShell
Get-ExecutionPolicy -List

# Проверка переменных окружения
Get-ChildItem Env: | Sort-Object Name
```

---

## 📞 КОНТАКТЫ И РЕСУРСЫ

### Официальные документации:
- **Bun**: https://bun.sh/docs
- **MySQL**: https://dev.mysql.com/doc/
- **SvelteKit**: https://kit.svelte.dev/docs
- **Elysia**: https://elysiajs.com/

### Полезные ссылки:
- **PowerShell документация**: https://docs.microsoft.com/en-us/powershell/
- **Windows Terminal**: https://github.com/microsoft/terminal
- **Git for Windows**: https://git-scm.com/download/win

---

## ✅ ФИНАЛЬНЫЙ ЧЕКЛИСТ

После завершения установки убедитесь:

- [ ] MySQL служба запущена (`net start MySQL80`)
- [ ] База данных `yuyu_lolita` создана
- [ ] Файл `.env` настроен с правильными паролями
- [ ] Все зависимости установлены (`bun install`)
- [ ] Миграции применены (`bun run db:migrate:mysql`)
- [ ] API сервер запускается (`cd apps/api && bun run dev`)
- [ ] Веб-приложение запускается (`cd apps/web && bun run dev`)
- [ ] Порты 3001 и 5173 доступны
- [ ] API отвечает на http://localhost:3001/health
- [ ] Веб-приложение открывается на http://localhost:5173

**🎉 Поздравляем! YuYu Lolita Shopping успешно установлен и готов к работе на Windows!**

---

*Создано с ❤️ для разработчиков на Windows*
*Версия инструкции: 1.0*
*Дата: 2025*