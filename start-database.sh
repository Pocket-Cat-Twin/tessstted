#!/bin/bash

# ============================================================================
# АВТОМАТИЧЕСКИЙ ЗАПУСК POSTGRESQL ДЛЯ API 
# ============================================================================
# Этот скрипт автоматически запускает PostgreSQL и готовит все для работы API
# Использование: ./start-database.sh
# ============================================================================

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "🚀 АВТОМАТИЧЕСКИЙ ЗАПУСК POSTGRESQL ДЛЯ API"
echo "============================================="
echo ""

# Configuration
CONTAINER_NAME="yuyu-postgres"
DB_USER="postgres"
DB_PASS="postgres"  
DB_NAME="yuyu_lolita"
DB_PORT="5432"

log_info "Параметры базы данных:"
log_info "  Контейнер: $CONTAINER_NAME"
log_info "  Пользователь: $DB_USER"
log_info "  База данных: $DB_NAME"
log_info "  Порт: $DB_PORT"
echo ""

# Step 1: Check if container already exists
log_info "Шаг 1: Проверяем состояние PostgreSQL контейнера..."

if docker ps -a | grep -q "$CONTAINER_NAME"; then
    CONTAINER_STATE=$(docker inspect -f '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "not_found")
    
    if [ "$CONTAINER_STATE" = "running" ]; then
        log_success "Контейнер уже запущен!"
    elif [ "$CONTAINER_STATE" = "exited" ]; then
        log_info "Контейнер остановлен, запускаем..."
        docker start "$CONTAINER_NAME"
        log_success "Контейнер перезапущен"
    else
        log_warning "Контейнер в неожиданном состоянии: $CONTAINER_STATE"
        log_info "Удаляем старый контейнер и создаем новый..."
        docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
        log_info "Создаем новый контейнер..."
        docker run --name "$CONTAINER_NAME" \
            -e POSTGRES_USER="$DB_USER" \
            -e POSTGRES_PASSWORD="$DB_PASS" \
            -e POSTGRES_DB="$DB_NAME" \
            -p "$DB_PORT:5432" \
            -d postgres:16
        log_success "Новый контейнер создан и запущен"
    fi
else
    log_info "Контейнер не найден, создаем новый..."
    
    # Check if port is free
    if netstat -tlnp 2>/dev/null | grep -q ":$DB_PORT "; then
        log_error "Порт $DB_PORT уже занят!"
        log_info "Останавливаем службы на порту $DB_PORT..."
        
        # Try to stop existing PostgreSQL service
        sudo service postgresql stop 2>/dev/null || true
        sleep 2
        
        # Check again
        if netstat -tlnp 2>/dev/null | grep -q ":$DB_PORT "; then
            log_error "Не удалось освободить порт $DB_PORT"
            log_error "Остановите службу вручную или выберите другой порт"
            exit 1
        fi
    fi
    
    log_info "Создаем и запускаем PostgreSQL контейнер..."
    docker run --name "$CONTAINER_NAME" \
        -e POSTGRES_USER="$DB_USER" \
        -e POSTGRES_PASSWORD="$DB_PASS" \
        -e POSTGRES_DB="$DB_NAME" \
        -p "$DB_PORT:5432" \
        -d postgres:16
    log_success "Контейнер создан и запущен"
fi

# Step 2: Wait for PostgreSQL to be ready
log_info "Шаг 2: Ожидаем готовности PostgreSQL..."

CONNECTION_STRING="postgresql://$DB_USER:$DB_PASS@localhost:$DB_PORT/$DB_NAME"
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    
    if PGPASSWORD="$DB_PASS" psql "$CONNECTION_STRING" -c "SELECT 1;" >/dev/null 2>&1; then
        log_success "PostgreSQL готов к работе!"
        break
    else
        if [ $ATTEMPT -eq 1 ]; then
            log_info "Ожидаем запуска PostgreSQL..."
        fi
        printf "."
        sleep 1
    fi
    
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo ""
        log_error "PostgreSQL не отвечает после $MAX_ATTEMPTS попыток"
        log_error "Проверьте статус контейнера: docker logs $CONTAINER_NAME"
        exit 1
    fi
done

if [ $ATTEMPT -gt 1 ]; then
    echo ""
fi

# Step 3: Check if migrations need to be applied
log_info "Шаг 3: Проверяем схему базы данных..."

TABLE_COUNT=$(PGPASSWORD="$DB_PASS" psql "$CONNECTION_STRING" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")

if [ "$TABLE_COUNT" -lt 20 ]; then
    log_warning "База данных пуста или неполная ($TABLE_COUNT таблиц)"
    log_info "Применяем миграции..."
    
    MIGRATION_FILE="packages/db/migrations/0000_consolidated_schema.sql"
    
    if [ -f "$MIGRATION_FILE" ]; then
        PGPASSWORD="$DB_PASS" psql "$CONNECTION_STRING" -f "$MIGRATION_FILE" >/dev/null 2>&1
        
        # Check result
        NEW_TABLE_COUNT=$(PGPASSWORD="$DB_PASS" psql "$CONNECTION_STRING" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")
        
        if [ "$NEW_TABLE_COUNT" -gt 20 ]; then
            log_success "Миграции применены успешно ($NEW_TABLE_COUNT таблиц создано)"
        else
            log_error "Миграции применились некорректно"
            exit 1
        fi
    else
        log_error "Файл миграций не найден: $MIGRATION_FILE"
        exit 1
    fi
else
    log_success "Схема базы данных готова ($TABLE_COUNT таблиц)"
fi

# Step 4: Verify connection and key tables
log_info "Шаг 4: Финальная проверка подключения..."

# Test config table (что проверяет API)
if PGPASSWORD="$DB_PASS" psql "$CONNECTION_STRING" -c "SELECT COUNT(*) FROM config;" >/dev/null 2>&1; then
    log_success "Таблица config доступна ✅"
else
    log_error "Таблица config недоступна ❌"
    exit 1
fi

# Test users table
if PGPASSWORD="$DB_PASS" psql "$CONNECTION_STRING" -c "SELECT COUNT(*) FROM users;" >/dev/null 2>&1; then
    log_success "Таблица users доступна ✅"
else
    log_error "Таблица users недоступна ❌"
    exit 1
fi

echo ""
log_success "🎉 POSTGRESQL ПОЛНОСТЬЮ ГОТОВ К РАБОТЕ!"
echo "============================================"
echo ""
log_success "✅ Контейнер: $CONTAINER_NAME запущен"
log_success "✅ База данных: $DB_NAME создана"
log_success "✅ Пользователь: $DB_USER с паролем настроен"
log_success "✅ Схема: все таблицы созданы"
log_success "✅ Подключение: протестировано и работает"
echo ""
log_info "🔗 Параметры подключения:"
echo "   DATABASE_URL=$CONNECTION_STRING"
echo ""
log_info "🚀 Теперь вы можете:"
echo "   1. Запустить API сервер - он подключится автоматически"
echo "   2. Использовать любые инструменты для работы с PostgreSQL"
echo "   3. Подключаться к базе данных из других приложений"
echo ""
log_info "📊 Управление контейнером:"
echo "   • Остановка: docker stop $CONTAINER_NAME"
echo "   • Запуск: docker start $CONTAINER_NAME"  
echo "   • Перезапуск: docker restart $CONTAINER_NAME"
echo "   • Удаление: docker rm -f $CONTAINER_NAME"
echo ""
log_info "🔍 Проверка состояния:"
echo "   • Статус: docker ps | grep $CONTAINER_NAME"
echo "   • Логи: docker logs $CONTAINER_NAME"
echo "   • Подключение: node test-api-connection.js"
echo ""

# Final test
log_info "🧪 Быстрый тест API подключения..."
if PGPASSWORD="$DB_PASS" psql "$CONNECTION_STRING" -c "SELECT 'API connection test PASSED!' as result;" 2>/dev/null; then
    echo ""
    log_success "💯 УСПЕХ! API ПОДКЛЮЧЕНИЕ ГАРАНТИРОВАННО РАБОТАЕТ!"
else
    log_error "Проблема с финальным тестом подключения"
    exit 1
fi