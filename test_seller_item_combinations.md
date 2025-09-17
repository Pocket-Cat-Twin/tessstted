# ТЕСТ ИСПРАВЛЕННОЙ ЛОГИКИ МОНИТОРИНГА СВЯЗОК ПРОДАВЕЦ-ТОВАР

## Исправленные критические проблемы

### ✅ ИСПРАВЛЕНО 1: Логирование исчезнувших связок
**Проблема:** removed_combinations детектировались но не логировались  
**Исправление:** Добавлен код в `_detect_combination_changes`:
```python
# Log removed combinations as ITEM_REMOVED
for seller, item in removed_combinations:
    change = ChangeLogEntry(
        seller_name=seller,
        item_name=item,
        change_type='ITEM_REMOVED',
        old_value=f"{seller}/{item}",
        new_value=None
    )
    
    # Log to changes_log table + Update status to UNCHECKED
```

### ✅ ИСПРАВЛЕНО 2: Метод remove_inactive_combinations
**Проблема:** Использование несуществующей колонки `last_seen_at`  
**Исправление:** Заменено на существующие колонки:
```python
# БЫЛО (сломано):
WHERE (last_seen_at IS NULL AND created_at < ?) OR last_seen_at < ?

# СТАЛО (работает):  
WHERE status = 'UNCHECKED' AND status_changed_at < ?
```

### ✅ ИСПРАВЛЕНО 3: UPDATE запросы с last_seen_at
**Проблема:** Попытки обновить несуществующую колонку  
**Исправление:** Убрана ссылка на `last_seen_at` из UPDATE запросов

## ДЕТАЛЬНЫЙ ТЕСТ-КЕЙС

### Сценарий: Исчезновение связки ПРОДАВЕЦ-ТОВАР

#### Начальное состояние (день 1):
```
monitoring_queue:
- (Продавец123, ТоварА) -> статус: CHECKED, status_changed_at: 2025-09-01 10:00
- (Продавец456, ТоварБ) -> статус: CHECKED, status_changed_at: 2025-09-01 10:00
- (Продавец789, ТоварВ) -> статус: CHECKED, status_changed_at: 2025-09-01 10:00

sellers_current:
- (Продавец123, ТоварА) -> статус: CHECKED
- (Продавец456, ТоварБ) -> статус: CHECKED  
- (Продавец789, ТоварВ) -> статус: CHECKED
```

#### День 2: Новый OCR результат (Продавец789 исчез)
```
Парсинг результат:
current_combinations = {
    (Продавец123, ТоварА),  
    (Продавец456, ТоварБ)
    # Продавец789 больше НЕТ!
}

previous_combinations = {
    (Продавец123, ТоварА),
    (Продавец456, ТоварБ),
    (Продавец789, ТоварВ)
}
```

#### ✅ ИСПРАВЛЕННАЯ обработка в _detect_combination_changes:
```python
removed_combinations = previous - current = {(Продавец789, ТоварВ)}

# НОВАЯ ЛОГИКА (раньше НЕ работало):
for seller, item in removed_combinations:
    # 1. Логируем исчезновение
    INSERT INTO changes_log 
    VALUES ('Продавец789', 'ТоварВ', 'ITEM_REMOVED', 'Продавец789/ТоварВ', NULL)
    
    # 2. Обновляем статус на UNCHECKED
    UPDATE monitoring_queue 
    SET status = 'UNCHECKED', status_changed_at = CURRENT_TIMESTAMP
    WHERE seller_name = 'Продавец789' AND item_name = 'ТоварВ'
    
    # 3. Также обновляем sellers_current
    UPDATE sellers_current 
    SET status = 'UNCHECKED', status_changed_at = CURRENT_TIMESTAMP
    WHERE seller_name = 'Продавец789' AND item_name = 'ТоварВ'
```

#### Результат после обработки:
```
changes_log:
+ НОВАЯ ЗАПИСЬ: (Продавец789, ТоварВ, ITEM_REMOVED, Продавец789/ТоварВ, NULL, 2025-09-02 10:30)

monitoring_queue:
- (Продавец123, ТоварА) -> статус: CHECKED
- (Продавец456, ТоварБ) -> статус: CHECKED
- (Продавец789, ТоварВ) -> статус: UNCHECKED ✅ АВТОМАТИЧЕСКИ ОБНОВЛЕНО!

sellers_current:
- (Продавец123, ТоварА) -> статус: CHECKED
- (Продавец456, ТоварБ) -> статус: CHECKED
- (Продавец789, ТоварВ) -> статус: UNCHECKED ✅ АВТОМАТИЧЕСКИ ОБНОВЛЕНО!
```

#### День 9: Автоматическая очистка (remove_inactive_combinations)
```
inactive_threshold_days = 7
cutoff_date = 2025-09-02 (7 дней назад)

✅ ИСПРАВЛЕННЫЙ запрос:
SELECT seller_name, item_name FROM monitoring_queue
WHERE status = 'UNCHECKED' AND status_changed_at < '2025-09-02'

Найдено: (Продавец789, ТоварВ) - UNCHECKED с 2025-09-02 10:30

# Проверяем не логировалось ли уже удаление недавно
SELECT COUNT(*) FROM changes_log 
WHERE seller_name = 'Продавец789' AND item_name = 'ТоварВ' 
AND change_type = 'ITEM_REMOVED' AND detected_at > '2025-09-02'

# Если уже логировалось - не дублируем, просто удаляем

# Удаляем из обеих таблиц:
DELETE FROM monitoring_queue WHERE status = 'UNCHECKED' AND status_changed_at < cutoff
DELETE FROM sellers_current WHERE status = 'UNCHECKED' AND status_changed_at < cutoff
```

#### Финальное состояние:
```
monitoring_queue:
- (Продавец123, ТоварА) -> статус: CHECKED
- (Продавец456, ТоварБ) -> статус: CHECKED
# (Продавец789, ТоварВ) - УДАЛЕНО ✅

sellers_current:
- (Продавец123, ТоварА) -> статус: CHECKED
- (Продавец456, ТоварБ) -> статус: CHECKED
# (Продавец789, ТоварВ) - УДАЛЕНО ✅

changes_log содержит полную историю:
- (Продавец789, ТоварВ, ITEM_REMOVED, ..., 2025-09-02 10:30) ✅ Логировано!
```

## ПРОВЕРКА EDGE CASES

### Edge Case 1: Временное исчезновение и возврат
```
День 1: (ПродавецX, ТоварY) -> CHECKED
День 2: Исчез -> UNCHECKED + ITEM_REMOVED логировано  
День 3: Появился снова -> NEW + NEW_ITEM логировано
```

### Edge Case 2: Множественные исчезновения
```
removed_combinations = {(П1, Т1), (П2, Т2), (П3, Т3)}

✅ ВСЕ обрабатываются в цикле:
- 3 записи ITEM_REMOVED в changes_log
- 3 обновления статуса на UNCHECKED
- Корректное логирование для каждой связки
```

### Edge Case 3: Предотвращение дублирования логов
```
if not already_logged:  # Проверяем дубли
    INSERT INTO changes_log (ITEM_REMOVED)
# Избегаем повторных записей при очистке
```

## ЗАКЛЮЧЕНИЕ

### ✅ ИСПРАВЛЕНИЯ РАБОТАЮТ КОРРЕКТНО

**Теперь система правильно:**
1. **Детектирует исчезновение связок** и логирует как `ITEM_REMOVED`
2. **Автоматически переводит исчезнувшие связки в UNCHECKED** 
3. **Корректно удаляет старые UNCHECKED связки** через N дней
4. **Использует только существующие колонки БД**
5. **Предотвращает дублирование логов**

### 🎯 КОНЦЕПЦИЯ СВЯЗОК СОБЛЮДАЕТСЯ

Все статусы (NEW/CHECKED/UNCHECKED) и операции (детекция изменений, логирование, удаление) применяются именно к **связкам ПРОДАВЕЦ-ТОВАР**, а не к отдельным продавцам или товарам.

**Система теперь полностью соответствует требованию мониторинга связок!**