# YuYu Lolita Shopping v2 🛍️

> Современная система заказов товаров из Китая с адаптивным веб-интерфейсом и мощным API

[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![SvelteKit](https://img.shields.io/badge/SvelteKit-FF3E00?style=for-the-badge&logo=svelte&logoColor=white)](https://kit.svelte.dev/)
[![Elysia](https://img.shields.io/badge/Elysia-000000?style=for-the-badge&logo=elysia&logoColor=white)](https://elysiajs.com/)
[![Bun](https://img.shields.io/badge/Bun-000000?style=for-the-badge&logo=bun&logoColor=white)](https://bun.sh/)

## 🚀 Особенности

- ✨ **Современный стек технологий**: SvelteKit + Elysia + TypeScript + Bun
- 🎨 **Адаптивный дизайн**: Tailwind CSS с поддержкой mobile-first
- 🔐 **Система аутентификации**: JWT токены с защищенными маршрутами  
- 💰 **Расчет стоимости**: Автоматический пересчет валют и комиссий
- 📱 **Отслеживание заказов**: Поиск по номеру с детальной информацией
- 👨‍💼 **Админ панель**: Управление заказами и конфигурацией
- 📚 **API документация**: Автоматическая Swagger документация
- 🏗️ **Монорепозиторий**: Shared packages для типов и утилит

## 🛠️ Технологический стек

### Frontend
- **SvelteKit** - Полнофункциональный фреймворк
- **Tailwind CSS** - Utility-first CSS фреймворк
- **TypeScript** - Типизированный JavaScript
- **Vite** - Быстрый build tool

### Backend  
- **Elysia** - Быстрый TypeScript веб-фреймворк
- **Bun** - JavaScript runtime и менеджер пакетов
- **PostgreSQL** - Реляционная база данных
- **Drizzle ORM** - Type-safe SQL ORM

### DevTools
- **Monorepo** - Workspace-based архитектура
- **ESLint + Prettier** - Линтинг и форматирование
- **Docker** - Контейнеризация для разработки

## 📦 Структура проекта

```
yuyu-lolita-v2/
├── apps/
│   ├── api/                 # Elysia API сервер
│   │   ├── src/
│   │   │   ├── routes/      # API маршруты
│   │   │   ├── middleware/  # Middleware (auth, error, rate limiting)
│   │   │   ├── services/    # Бизнес-логика
│   │   │   └── index.ts     # Главный файл сервера
│   │   └── package.json
│   └── web/                 # SvelteKit веб-приложение
│       ├── src/
│       │   ├── routes/      # Страницы приложения
│       │   ├── lib/         # Компоненты и утилиты
│       │   │   ├── components/ui/  # UI компоненты
│       │   │   ├── stores/  # Svelte stores
│       │   │   └── api/     # API клиент
│       │   └── app.html
│       └── package.json
├── packages/
│   ├── shared/              # Общие типы и утилиты
│   │   ├── src/
│   │   │   ├── types/       # TypeScript типы
│   │   │   └── utils/       # Утилитарные функции
│   │   └── package.json
│   └── db/                  # Схема базы данных
│       ├── src/
│       │   ├── schema/      # Drizzle схемы
│       │   ├── migrations/  # Миграции БД
│       │   └── seeds/       # Данные для наполнения
│       └── package.json
├── docker-compose.yml       # PostgreSQL для разработки
├── package.json             # Корневой package.json
└── README.md
```

## 🚀 Быстрый старт

### Предварительные требования

- [Bun](https://bun.sh/) >= 1.2.0
- [Docker](https://docker.com/) для PostgreSQL
- [Node.js](https://nodejs.org/) >= 18 (fallback)

### 1. Клонирование и установка

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd yuyu-lolita-v2

# Установите зависимости
bun install
```

### 2. Настройка базы данных

```bash
# Запустите PostgreSQL в Docker
docker-compose up -d

# Примените миграции
bun run db:migrate

# Наполните тестовыми данными (опционально)
bun run db:seed
```

### 3. Настройка переменных окружения

```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Отредактируйте .env файл с вашими настройками
```

### 4. Запуск в режиме разработки

```bash
# Терминал 1 - API сервер
cd apps/api
bun run dev

# Терминал 2 - Веб-приложение  
cd apps/web
bun run dev
```

Приложение будет доступно по адресам:
- **Веб-интерфейс**: http://localhost:5173
- **API сервер**: http://localhost:3001
- **API документация**: http://localhost:3001/swagger

## 🔧 Доступные команды

### Корневые команды
```bash
bun run dev          # Запуск всех сервисов
bun run build        # Сборка всех приложений
bun run type-check   # Проверка типов
bun run lint         # Линтинг кода
bun run format       # Форматирование кода
```

### База данных
```bash
bun run db:generate  # Генерация миграций
bun run db:migrate   # Применение миграций
bun run db:seed      # Наполнение данными
bun run db:studio    # Drizzle Studio UI
```

### Отдельные приложения
```bash
# API сервер
cd apps/api
bun run dev         # Разработка с hot reload
bun run build       # Сборка для продакшна
bun run start       # Запуск продакшн версии

# Веб-приложение
cd apps/web
bun run dev         # Разработка с hot reload
bun run build       # Сборка для продакшна
bun run preview     # Превью продакшн сборки
```

## 📚 API документация

### Основные эндпоинты

#### Аутентификация
- `POST /api/v1/auth/register` - Регистрация пользователя
- `POST /api/v1/auth/login` - Вход в систему
- `GET /api/v1/auth/me` - Получение профиля
- `POST /api/v1/auth/logout` - Выход из системы

#### Заказы
- `POST /api/v1/orders` - Создание заказа
- `GET /api/v1/orders/lookup/:nomerok` - Поиск заказа по номеру
- `GET /api/v1/orders` - Список заказов пользователя
- `PUT /api/v1/orders/:id` - Обновление заказа

#### Конфигурация
- `GET /api/v1/config` - Публичная конфигурация
- `GET /api/v1/config/kurs` - Текущий курс валют

#### Истории
- `GET /api/v1/stories` - Список историй
- `GET /api/v1/stories/:link` - Конкретная история

Полная документация доступна в Swagger UI: http://localhost:3001/swagger

## 🎨 UI компоненты

Проект включает готовые UI компоненты:

- **Button** - Кнопки с различными вариантами
- **Input** - Поля ввода с валидацией  
- **Modal** - Модальные окна
- **Badge** - Бейджи для статусов
- **Card** - Карточки контента
- **Toast** - Уведомления
- **Spinner** - Индикаторы загрузки

Пример использования:
```svelte
<script>
  import { Button, Input, Modal } from '$lib/components/ui';
</script>

<Button variant="primary" size="lg">Создать заказ</Button>
<Input label="Email" type="email" required />
<Modal title="Подтверждение" bind:open={showModal}>
  Содержимое модального окна
</Modal>
```

## 🔒 Аутентификация

Система использует JWT токены для аутентификации:

```typescript
// Вход в систему
const result = await authStore.login(email, password);
if (result.success) {
  // Пользователь авторизован
}

// Проверка авторизации
if ($authStore.user) {
  // Пользователь вошел в систему
}

// Выход
await authStore.logout();
```

## 🛍️ Система заказов

### Создание заказа
```typescript
const orderData = {
  customerName: 'Иван Иванов',
  customerPhone: '+7 (999) 123-45-67',
  deliveryAddress: 'Москва, ул. Тестовая, 1',
  goods: [
    {
      name: 'Товар 1',
      quantity: 2,
      priceYuan: 100
    }
  ]
};

const result = await ordersStore.create(orderData);
```

### Отслеживание заказа
```typescript
const order = await ordersStore.lookup('YL123456');
if (order.success) {
  console.log(order.data.status); // Статус заказа
}
```

## 👨‍💼 Админ панель

Административная панель доступна по адресу `/admin` для пользователей с ролью `ADMIN`.

Возможности:
- 📋 Управление всеми заказами
- 💱 Настройка курса валют
- 📊 Просмотр статистики
- 👥 Управление пользователями
- ⚙️ Конфигурация системы

## 🧪 Тестирование

```bash
# Запуск тестов
bun test

# Тесты с покрытием
bun test --coverage

# E2E тесты (если настроены)
bun run test:e2e
```

## 📦 Сборка для продакшна

```bash
# Сборка всех приложений
bun run build

# Запуск продакшн версии
bun run start
```

## 🐳 Docker

```bash
# Запуск в Docker (если настроен)
docker-compose up --build

# Только база данных для разработки
docker-compose up postgres
```

## 🛠️ Разработка

### Добавление новой страницы

1. Создайте файл в `apps/web/src/routes/`
2. Добавьте маршрут в навигацию
3. Создайте необходимые API endpoints
4. Обновите типы в `packages/shared/`

### Добавление API endpoint

1. Создайте маршрут в `apps/api/src/routes/`
2. Добавьте схему валидации
3. Обновите API клиент
4. Добавьте типы

### Работа с базой данных

```bash
# Создание новой миграции
bun run db:generate

# Откат миграции
bun run db:rollback

# Просмотр схемы в UI
bun run db:studio
```

## 🤝 Внесение изменений

1. Форкните репозиторий
2. Создайте ветку для функции (`git checkout -b feature/amazing-feature`)
3. Сделайте коммит (`git commit -m 'Add amazing feature'`)
4. Запушьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📝 Лицензия

Этот проект лицензирован под MIT License - смотрите файл [LICENSE](LICENSE) для деталей.

## 🙏 Благодарности

- [SvelteKit](https://kit.svelte.dev/) за отличный фреймворк
- [Elysia](https://elysiajs.com/) за быстрый и типизированный API
- [Tailwind CSS](https://tailwindcss.com/) за utility-first подход
- [Bun](https://bun.sh/) за молниеносную скорость

## 📞 Поддержка

Если у вас есть вопросы или проблемы:

1. Проверьте [Issues](../../issues)
2. Создайте новый Issue с подробным описанием
3. Для срочных вопросов свяжитесь с командой

---

**Сделано с ❤️ для YuYu Lolita Shopping**