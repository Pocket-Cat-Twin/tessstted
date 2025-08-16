bun install
```
docker-compose up -d

bun run db:migrate

bun run db:seed
```
cd apps/api
bun run dev

cd apps/web
bun run dev
```

bun run dev          # Запуск всех сервисов
bun run build        # Сборка всех приложений
bun run type-check   # Проверка типов
bun run lint         # Линтинг кода
bun run format       # Форматирование кода


bun run db:generate  # Генерация миграций
bun run db:migrate   # Применение миграций
bun run db:seed      # Наполнение данными
bun run db:studio    # Drizzle Studio UI
```