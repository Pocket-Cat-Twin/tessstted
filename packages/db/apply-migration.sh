#!/bin/bash

echo "🚀 Применяем полную консолидированную схему к базе данных..."

# Создаем базу данных (если не существует)
echo "🆕 Создание базы данных yuyu_lolita..."
createdb yuyu_lolita 2>/dev/null || echo "База данных уже существует или произошла ошибка"

# Применяем миграцию
echo "📖 Применяем полную схему..."
psql -d yuyu_lolita -f migrations/0000_consolidated_schema.sql

if [ $? -eq 0 ]; then
    echo "✅ Миграция применена успешно!"
    
    # Проверяем критические элементы
    echo "🔍 Проверяем критические элементы..."
    
    # Проверяем enum user_verification_status
    enum_exists=$(psql -d yuyu_lolita -tAc "SELECT 1 FROM pg_type WHERE typname = 'user_verification_status';" 2>/dev/null | head -1)
    if [ "$enum_exists" = "1" ]; then
        echo "✅ Enum user_verification_status: СОЗДАН"
    else
        echo "❌ Enum user_verification_status: НЕ НАЙДЕН"
    fi
    
    # Проверяем колонку overall_verification_status
    column_exists=$(psql -d yuyu_lolita -tAc "SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'overall_verification_status';" 2>/dev/null | head -1)
    if [ "$column_exists" = "1" ]; then
        echo "✅ Колонка overall_verification_status: СОЗДАНА"
    else
        echo "❌ Колонка overall_verification_status: НЕ НАЙДЕНА"
    fi
    
    # Проверяем другие критические поля
    for field in "failed_login_attempts" "locked_until" "email_verified_at" "phone_verified_at"; do
        field_exists=$(psql -d yuyu_lolita -tAc "SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = '$field';" 2>/dev/null | head -1)
        if [ "$field_exists" = "1" ]; then
            echo "✅ Поле $field: СОЗДАНО"
        else
            echo "❌ Поле $field: НЕ НАЙДЕНО"
        fi
    done
    
    # Проверяем таблицу faq_categories
    table_exists=$(psql -d yuyu_lolita -tAc "SELECT 1 FROM information_schema.tables WHERE table_name = 'faq_categories';" 2>/dev/null | head -1)
    if [ "$table_exists" = "1" ]; then
        echo "✅ Таблица faq_categories: СОЗДАНА"
    else
        echo "❌ Таблица faq_categories: НЕ НАЙДЕНА"
    fi
    
    # Подсчитываем таблицы и enum'ы
    tables_count=$(psql -d yuyu_lolita -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" 2>/dev/null)
    enums_count=$(psql -d yuyu_lolita -tAc "SELECT COUNT(*) FROM pg_type WHERE typtype = 'e';" 2>/dev/null)
    
    echo "📊 Всего таблиц создано: $tables_count"
    echo "📊 Всего enum-ов создано: $enums_count"
    
    echo "🎉 БАЗА ДАННЫХ ГОТОВА К РАБОТЕ!"
    
else
    echo "❌ Ошибка при применении миграции"
    exit 1
fi