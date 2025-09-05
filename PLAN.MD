Система автоматического мониторинга товаров и продавцов
Описание проекта
Система для автоматического мониторинга торговых площадок через скриншоты с последующим распознаванием текста и отслеживанием изменений товаров и цен.
Архитектура системы
Основные компоненты:

Модуль захвата экрана - создание скриншотов по хоткеям
Модуль обработки изображений - объединение и подготовка для OCR
OCR интеграция - распознавание текста через Yandex OCR API
Парсер данных - извлечение информации о товарах из текста
Система мониторинга - отслеживание изменений и управление статусами
База данных - хранение товаров, продавцов и истории изменений
Планировщик - автоматическое выполнение задач по расписанию

Структура проекта
market_monitoring_system/
├── src/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── hotkey_config.json
│   ├── core/
│   │   ├── __init__.py
│   │   ├── screenshot_capture.py
│   │   ├── image_processor.py
│   │   ├── ocr_client.py
│   │   ├── text_parser.py
│   │   ├── database_manager.py
│   │   └── monitoring_engine.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── scheduler.py
│   │   ├── file_utils.py
│   │   └── logger.py
│   └── main.py
├── data/
│   ├── temp/
│   │   ├── screenshots/
│   │   │   ├── F1/
│   │   │   ├── F2/
│   │   │   └── ...
│   │   └── merged/
│   └── logs/
├── database/
│   └── market_data.db
├── config.json
├── requirements.txt
└── README.md
Технологический стек

Python 3.9+
Основные библиотеки:

keyboard - глобальные хоткеи
mss - быстрые скриншоты
Pillow - обработка изображений
requests - HTTP запросы к API
sqlite3 - локальная база данных
APScheduler - планировщик задач
re - регулярные выражения для парсинга
logging - система логирования



База данных
Схема таблиц:
sql-- Основная таблица товаров (исторические данные)
CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_name TEXT NOT NULL,
    item_name TEXT NOT NULL,
    price REAL,
    quantity INTEGER,
    item_id TEXT,
    hotkey TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_seller_item_time (seller_name, item_name, created_at)
);

-- Текущее состояние продавцов
CREATE TABLE sellers_current (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_name TEXT NOT NULL,
    item_name TEXT NOT NULL,
    quantity INTEGER,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK(status IN ('NEW', 'CHECKED', 'UNCHECKED')) DEFAULT 'NEW',
    status_changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(seller_name, item_name)
);

-- Очередь мониторинга
CREATE TABLE monitoring_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_name TEXT NOT NULL,
    item_name TEXT NOT NULL,
    status TEXT CHECK(status IN ('NEW', 'CHECKED', 'UNCHECKED')) DEFAULT 'NEW',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen_at DATETIME,
    status_changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(seller_name, item_name)
);

-- Лог изменений
CREATE TABLE changes_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_name TEXT NOT NULL,
    item_name TEXT NOT NULL,
    change_type TEXT CHECK(change_type IN (
        'PRICE_INCREASE', 'PRICE_DECREASE', 
        'QUANTITY_INCREASE', 'QUANTITY_DECREASE',
        'NEW_ITEM', 'ITEM_REMOVED', 'SELLER_NEW', 'SELLER_REMOVED'
    )),
    old_value TEXT,
    new_value TEXT,
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Сессии OCR для отладки
CREATE TABLE ocr_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hotkey TEXT NOT NULL,
    processed_items INTEGER DEFAULT 0,
    processing_time REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
Конфигурация
config.json
json{
    "hotkeys": {
        "F1": {
            "area": [100, 100, 800, 600],
            "folder": "F1", 
            "merge_interval": 30,
            "enabled": true,
            "description": "Главная страница товаров"
        },
        "F2": {
            "area": [100, 100, 800, 600],
            "folder": "F2",
            "merge_interval": 60,
            "enabled": true,
            "description": "Страница продавцов"
        }
    },
    "yandex_ocr": {
        "api_key": "your_api_key",
        "api_url": "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText",
        "max_retries": 3,
        "timeout": 30
    },
    "monitoring": {
        "status_check_interval": 600,
        "cleanup_old_data_days": 30
    },
    "paths": {
        "temp_screenshots": "data/temp/screenshots",
        "temp_merged": "data/temp/merged",
        "database": "database/market_data.db",
        "logs": "data/logs"
    }
}
Модули системы
1. Модуль захвата экрана (screenshot_capture.py)
Функции:

Регистрация глобальных хоткеев
Захват заданной области экрана
Сохранение скриншотов с временными метками
Управление папками для каждого хоткея

Основные методы:
pythonclass ScreenshotCapture:
    def register_global_hotkeys()
    def capture_area(coordinates, save_path)
    def handle_hotkey_press(hotkey)
    def cleanup_old_screenshots(max_age_minutes)
2. Модуль обработки изображений (image_processor.py)
Функции:

Поиск скриншотов в папках хоткеев
Объединение изображений в вертикальные столбцы
Оптимизация размера для API
Немедленное удаление исходных файлов

Основные методы:
pythonclass ImageProcessor:
    def find_screenshots_in_folder(folder_path)
    def merge_to_vertical_column(image_paths)
    def optimize_for_ocr(image)
    def cleanup_source_files(file_paths)
3. OCR клиент (ocr_client.py)
Функции:

Отправка изображений в Yandex OCR API
Обработка ответов и ошибок
Retry логика для неудачных запросов
Извлечение только текстового контента

Основные методы:
pythonclass YandexOCRClient:
    def send_image_for_recognition(image_path)
    def extract_text_from_response(api_response)
    def handle_api_errors(response)
    def cleanup_processed_image(image_path)
4. Парсер текста (text_parser.py)
Функции:

Парсинг OCR текста в структурированные данные
Извлечение информации о продавцах и товарах
Поддержка разных паттернов для разных хоткеев
Валидация извлеченных данных

Основные методы:
pythonclass TextParser:
    def parse_items_data(text, hotkey)
    def extract_seller_info(text_block)
    def extract_item_details(text_block) 
    def validate_parsed_data(data)
    def detect_parsing_patterns(text)
Примеры паттернов парсинга:
python# Паттерны для разных форматов
PATTERNS = {
    'seller_item': r'(\w+)\s+(\w+.*?)\s+(\d+(?:\.\d+)?)\s+(\d+)',
    'price_quantity': r'Цена:\s*(\d+(?:\.\d+)?)\s*Кол-во:\s*(\d+)',
    'seller_name': r'Продавец:\s*([^\n]+)'
}
5. Менеджер базы данных (database_manager.py)
Функции:

Сохранение данных о товарах
Управление состояниями продавцов
Обновление очереди мониторинга
Отслеживание изменений

Основные методы:
pythonclass DatabaseManager:
    def save_items_data(items_data, hotkey)
    def update_sellers_status(seller_name, item_name)
    def manage_monitoring_queue()
    def detect_and_log_changes(new_data, old_data)
    def cleanup_expired_records()
6. Движок мониторинга (monitoring_engine.py)
Функции:

Управление жизненным циклом статусов
Автоматические переходы статусов
Детектирование изменений товаров
Управление очередью мониторинга

Основные методы:
pythonclass MonitoringEngine:
    def process_status_transitions()
    def check_new_combinations(seller_name, item_name)
    def update_queue_status(combination, new_status)
    def detect_price_changes(current_data, previous_data)
    def detect_quantity_changes(current_data, previous_data)
    def remove_inactive_combinations()
7. Планировщик (scheduler.py)
Функции:

Управление таймерами для каждого хоткея
Периодическая обработка скриншотов
Проверка статусов каждые 10 минут
Очистка старых данных

Основные методы:
pythonclass TaskScheduler:
    def setup_hotkey_timers()
    def process_hotkey_folder(hotkey)
    def run_status_check_cycle()
    def cleanup_old_data()
    def start_monitoring()
Логика работы системы
Жизненный цикл данных:

Захват скриншотов:

Пользователь нажимает хоткей (F1, F2, etc.)
Система делает скриншот заданной области
Файл сохраняется в соответствующую папку


Обработка по таймеру:

Каждые N секунд (настраивается для каждого хоткея)
Все скриншоты в папке объединяются в вертикальный столбец
Исходные файлы удаляются сразу после объединения


OCR распознавание:

Объединенное изображение отправляется в Yandex OCR
Получается текстовый контент
Изображение удаляется, JSON от API не сохраняется


Парсинг и сохранение:

Текст парсится для извлечения данных о товарах
Информация сохраняется в таблицу items
Обновляется таблица sellers_current


Мониторинг изменений:

Сравнение с предыдущими данными
Обновление очереди мониторинга
Логирование всех изменений



Управление статусами:
NEW → обнаружена новая связка (продавец + товар)
  ↓
CHECKED → информация найдена в таблице товаров
  ↓ (через 10 минут)
UNCHECKED → ждем повторного появления данных
  ↓
Цикл повторяется или запись удаляется, если товар больше не продается
Типы отслеживаемых изменений:

PRICE_INCREASE - цена товара выросла
PRICE_DECREASE - цена товара упала
QUANTITY_INCREASE - количество товара увеличилось
QUANTITY_DECREASE - количество товара уменьшилось
NEW_ITEM - появился новый товар
ITEM_REMOVED - товар исчез из продажи
SELLER_NEW - новый продавец
SELLER_REMOVED - продавец больше не продает товар

Алгоритм обработки
Основной цикл:
pythondef main_processing_cycle():
    for hotkey in active_hotkeys:
        # 1. Проверка наличия скриншотов
        screenshots = find_screenshots(hotkey.folder)
        
        if len(screenshots) > 0:
            # 2. Объединение изображений
            merged_image = merge_screenshots(screenshots)
            cleanup_screenshots(screenshots)
            
            # 3. OCR обработка
            ocr_text = send_to_yandex_ocr(merged_image)
            cleanup_image(merged_image)
            
            # 4. Парсинг данных
            parsed_data = parse_items_data(ocr_text, hotkey)
            
            # 5. Сохранение и мониторинг
            save_to_database(parsed_data, hotkey)
            update_monitoring_queue(parsed_data)
            detect_changes(parsed_data)

def status_management_cycle():
    # Каждые 10 минут
    update_checked_to_unchecked()
    remove_inactive_combinations()
    cleanup_old_records()