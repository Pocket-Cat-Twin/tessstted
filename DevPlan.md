# Комплексный план создания приложения для мониторинга игровых предметов

## 1. Архитектура системы

### Основные компоненты:
- **Главный контроллер** (Python) - управляет всем процессом
- **Модуль компьютерного зрения** - OCR и анализ изображений
- **База данных** - хранение информации о торговцах и предметах
- **Система логирования** - отслеживание работы и ошибок
- **GUI интерфейс** - управление и мониторинг

## 2. Технический стек

### Python (основной язык):
- `pyautogui` - скриншоты и координаты
- `opencv-python` - обработка изображений
- `pytesseract` - OCR для распознавания текста
- `sqlite3` / `postgresql` - база данных
- `tkinter` / `PyQt5` - GUI интерфейс
- `pillow` - работа с изображениями
- `numpy` - математические операции
- `logging` - логирование
- `time` / `threading` - таймеры и многопоточность

### Arduino:
- Библиотеки `Keyboard.h` и `Mouse.h` для эмуляции HID

## 3. Структура базы данных

### Таблица `trades`:
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    trader_nickname TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_id TEXT,
    previous_quantity INTEGER,
    current_quantity INTEGER,
    quantity_change INTEGER, -- положительное = пополнение, отрицательное = покупка
    price_per_unit REAL,
    total_value REAL, -- стоимость изменения (quantity_change * price_per_unit)
    trade_type TEXT CHECK(trade_type IN ('purchase', 'restock', 'sold_out')),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    screenshot_path TEXT
);
```

### Таблица `current_inventory`:
```sql
CREATE TABLE current_inventory (
    id INTEGER PRIMARY KEY,
    trader_nickname TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_id TEXT,
    quantity INTEGER,
    price_per_unit REAL,
    total_price REAL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(trader_nickname, item_name, item_id)
);
```

### Таблица `search_queue`:
```sql
CREATE TABLE search_queue (
    id INTEGER PRIMARY KEY,
    item_name TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 0
);
```

## 4. Детальная архитектура модулей

### 4.1 Главный контроллер (`main_controller.py`)
```python
class GameMonitor:
    def __init__(self):
        self.item_list = []  # Изначальный массив предметов
        self.arduino_controller = ArduinoController()
        self.vision_system = VisionSystem()
        self.database = DatabaseManager()
        self.return_coordinates = [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
        
    def start_monitoring_cycle(self)
    def process_item(self, item_name)
    def handle_trader_interaction(self, traders_list)
    def execute_return_script(self)
```

### 4.2 Arduino контроллер (`arduino_controller.py`)
```python
class ArduinoController:
    def __init__(self, port='COM3'):
        self.serial_connection = serial.Serial(port, 9600)
    
    def send_hotkey(self, key)
    def click_coordinates(self, x, y)
    def double_click(self, x, y)
    def type_text(self, text)
    def move_mouse_pattern(self, pattern_type)
```

### 4.3 Система компьютерного зрения (`vision_system.py`)
```python
class VisionSystem:
    def __init__(self):
        self.tesseract_config = '--psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    
    def take_screenshot(self, region=None)
    def find_item_on_screen(self, item_name)
    def scan_trader_window(self)
    def detect_trader_nickname(self, scan_area)
    def parse_coordinates_from_chat(self, chat_area)
    def extract_item_data(self, screenshot)
```

### 4.4 Менеджер базы данных (`database_manager.py`)
```python
class DatabaseManager:
    def __init__(self, db_path='game_monitor.db'):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
    
    def update_inventory_and_track_trades(self, trader_data):
        """
        Обновляет текущий инвентарь и отслеживает все изменения
        trader_data: список словарей с данными торговца
        """
        for item_data in trader_data:
            nickname = item_data['trader_nickname']
            item_name = item_data['item_name'] 
            item_id = item_data['item_id']
            current_qty = item_data['quantity']
            price = item_data['price_per_unit']
            
            # Получаем предыдущее состояние
            previous_data = self.get_previous_inventory(nickname, item_name, item_id)
            
            if previous_data:
                previous_qty = previous_data['quantity']
                previous_price = previous_data['price_per_unit']
                
                # Если количество изменилось
                if current_qty != previous_qty:
                    quantity_change = current_qty - previous_qty
                    
                    if quantity_change > 0:
                        trade_type = 'restock'
                    else:
                        trade_type = 'purchase' 
                        
                    # Используем последнюю известную цену для расчета сделки
                    used_price = previous_price if previous_price else price
                    total_value = abs(quantity_change) * used_price
                    
                    self.record_trade(
                        nickname, item_name, item_id, 
                        previous_qty, current_qty, quantity_change,
                        used_price, total_value, trade_type
                    )
            
            # Обновляем текущий инвентарь
            self.update_current_inventory(item_data)
    
    def check_disappeared_traders(self, current_traders_list, item_name):
        """
        Проверяет исчезнувших торговцев и записывает sold_out сделки
        """
        # Получаем всех торговцев, которые были в предыдущем сканировании
        previous_traders = self.get_traders_for_item(item_name)
        current_nicknames = [t['trader_nickname'] for t in current_traders_list]
        
        for prev_trader in previous_traders:
            if prev_trader['trader_nickname'] not in current_nicknames:
                # Торговец исчез - записываем sold_out
                self.record_trade(
                    prev_trader['trader_nickname'],
                    prev_trader['item_name'],
                    prev_trader['item_id'],
                    prev_trader['quantity'],
                    0,  # текущее количество = 0
                    -prev_trader['quantity'],  # весь товар продан
                    prev_trader['price_per_unit'],
                    prev_trader['quantity'] * prev_trader['price_per_unit'],
                    'sold_out'
                )
                
                # Удаляем из текущего инвентаря
                self.remove_from_inventory(prev_trader['trader_nickname'], 
                                         prev_trader['item_name'], 
                                         prev_trader['item_id'])
    
    def record_trade(self, nickname, item_name, item_id, prev_qty, 
                    curr_qty, change, price, total_value, trade_type):
        """Записывает сделку в таблицу trades"""
        query = """
        INSERT INTO trades (trader_nickname, item_name, item_id, 
                          previous_quantity, current_quantity, quantity_change,
                          price_per_unit, total_value, trade_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(query, (nickname, item_name, item_id, prev_qty,
                                curr_qty, change, price, total_value, trade_type))
        self.conn.commit()
    
    def get_previous_inventory(self, nickname, item_name, item_id):
        """Получает предыдущие данные инвентаря"""
        query = """
        SELECT * FROM current_inventory 
        WHERE trader_nickname=? AND item_name=? AND item_id=?
        """
        return self.conn.execute(query, (nickname, item_name, item_id)).fetchone()
    
    def update_current_inventory(self, item_data):
        """Обновляет текущий инвентарь"""
        query = """
        INSERT OR REPLACE INTO current_inventory 
        (trader_nickname, item_name, item_id, quantity, price_per_unit, total_price)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(query, (
            item_data['trader_nickname'], item_data['item_name'],
            item_data['item_id'], item_data['quantity'],
            item_data['price_per_unit'], item_data['total_price']
        ))
        self.conn.commit()
    
    def get_traders_for_item(self, item_name):
        """Получает всех торговцев для конкретного предмета"""
        query = "SELECT * FROM current_inventory WHERE item_name=?"
        return self.conn.execute(query, (item_name,)).fetchall()
    
    def get_trade_statistics(self, item_name=None, time_period=24):
        """Получает статистику сделок за период"""
        base_query = """
        SELECT trade_type, COUNT(*) as count, SUM(total_value) as total_value,
               AVG(price_per_unit) as avg_price, SUM(ABS(quantity_change)) as total_quantity
        FROM trades 
        WHERE timestamp >= datetime('now', '-{} hours')
        """.format(time_period)
        
        if item_name:
            base_query += " AND item_name=?"
            params = (item_name,)
        else:
            params = ()
            
        base_query += " GROUP BY trade_type"
        
        return self.conn.execute(base_query, params).fetchall()
    
    def get_item_queue(self):
        """Получает очередь предметов для обработки"""
        query = "SELECT * FROM search_queue WHERE status='pending' ORDER BY priority DESC"
        return self.conn.execute(query).fetchall()
```

## 5. Алгоритм работы (пошаговый)

### Фаза 1: Инициализация
1. Загрузка списка предметов из файла/БД
2. Калибровка координат экрана
3. Проверка работы OCR системы

### Фаза 2: Основной цикл
```
ДЛЯ КАЖДОГО предмета ИЗ списка:
    4. Найти предмет на экране (OCR сканирование)
    6. Сканировать окно торговцев
    7. Извлечь список торговцев
    
    8. **АНАЛИЗ ИЗМЕНЕНИЙ**:
       - Сравнить с предыдущим состоянием инвентаря
       - Выявить исчезнувших торговцев (sold_out сделки)
       - Записать все изменения в таблицу trades
    
    ДЛЯ КАЖДОГО торговца ИЗ списка:
        10. Запустить таймер ожидания (60 сек)
        11. Сканировать область никнейма каждую секунду
        
        ЕСЛИ торговец найден:
            12. Запустить алгоритм сбора данных
            14. Скриншот 9 раз, после каждого движения мышкой
            15. OCR обработка данных о предметах
            16. **ОБНОВЛЕНИЕ ДАННЫХ**:
                - Сравнить с текущим инвентарем
                - Зафиксировать изменения количества
                - Определить тип сделки (покупка/пополнение)
                - Рассчитать стоимость по последней цене
                - Обновить current_inventory
            
        ИНАЧЕ:
            18. Определить ближайшие координаты  
            20. Ожидание 30 сек
```

### Алгоритм отслеживания сделок:
```
ПРИ СКАНИРОВАНИИ торговца:
    1. Получить текущие данные (количество, цена)
    2. Найти предыдущую запись в current_inventory
    3. ЕСЛИ предыдущая запись существует:
        - ЕСЛИ количество уменьшилось:
            * trade_type = 'purchase'
            * quantity_change = отрицательное значение
            * total_value = |изменение| × предыдущая_цена
        - ЕСЛИ количество увеличилось:
            * trade_type = 'restock' 
            * quantity_change = положительное значение
            * total_value = изменение × текущая_цена
    4. Записать в таблицу trades
    5. Обновить current_inventory

ПРИ ИСЧЕЗНОВЕНИИ торговца:
    1. trade_type = 'sold_out'
    2. current_quantity = 0
    3. quantity_change = -предыдущее_количество
    4. total_value = предыдущее_количество × предыдущая_цена
    5. Записать в trades
    6. Удалить из current_inventory
```



## 7. Конфигурационные файлы

### `config.yaml`
```yaml
  
# Настройки экрана
screen:
  search_hotkey: "F"
  search_box_coords: [100, 200]
  trader_window_area: [300, 400, 800, 900]
  nickname_scan_area: [50, 50, 200, 100]
  
# Координаты возврата
return_coordinates:
  - [1000, 1000]
  - [2000, 1500] 
  - [500, 2000]
  - [1500, 500]
  
# Настройки таймеров
timers:
  trader_wait: 60
  return_wait: 30
  scan_interval: 1
  
# OCR настройки
ocr:
  language: "eng+rus"
  confidence_threshold: 70
```

### `items_list.txt`
```
Меч огня
Щит льда
Зелье лечения
Кольцо силы
Амулет защиты
```

## 8. Обработка ошибок и исключений

### Основные сценарии ошибок:
2. **Некорректное распознавание OCR** - повторное сканирование с другими параметрами
3. **Таймаут ожидания торговца** - переход к скрипту возвращения
4. **Ошибки базы данных** - логирование и попытка восстановления
5. **Изменение интерфейса игры** - адаптивные координаты

### Система логирования:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game_monitor.log'),
        logging.StreamHandler()
    ]
)
```

## 9. GUI интерфейс

### Основные элементы:
- **Панель управления**: старт/стоп, пауза
- **Мониторинг статуса**: текущий предмет, торговец
- **Логи в реальном времени**
- **Настройки координат и таймеров**
- **Аналитика сделок**: статистика покупок, пополнений, sold_out
- **Мониторинг рынка**: топ торговцев, популярные товары, ценовые тренды
- **История сделок**: фильтрация по товарам, торговцам, типу сделок

## 10. Тестирование и отладка

### Этапы тестирования:
1. **Модульное тестирование** каждого компонента
2. **Интеграционное тестирование** связки модулей
3. **Тестирование на реальных данных игры**
4. **Стресс-тестирование** длительной работы
5. **Тестирование обработки ошибок**

### Инструменты отладки:
- Визуализация области сканирования
- Пошаговый режим выполнения
- Сохранение скриншотов для анализа
- Детальное логирование всех операций

## 11. Оптимизация производительности

### Возможные улучшения:
- **Кэширование** результатов OCR
- **Многопоточность** для параллельной обработки
- **Оптимизация областей сканирования**
- **Сжатие и оптимизация скриншотов**

## 12. Развертывание и поддержка

### Требования к системе:
- Windows 10/11
- Python 3.8+
- Tesseract OCR
- Минимум 4GB RAM
- Разрешение экрана 1920x1080

### Установка:
1. Установка Python и зависимостей
3. Настройка Tesseract OCR
4. Калибровка координат под конкретную игру
5. Тестовый запуск

Этот план обеспечивает создание надежной и масштабируемой системы мониторинга игровых предметов с возможностью дальнейшего развития и оптимизации.