# 🚀 Запуск Game Monitor GUI

## Для Windows пользователей

### Способ 1: Двойной клик (Самый простой)
```
Дважды щелкните файл: start_gui.bat
```

### Способ 2: Python скрипт
```cmd
python start_gui.py
```

### Способ 3: Через модуль (если Python настроен правильно)
```cmd
python -m game_monitor --gui
```

### Способ 4: Альтернативный launcher
```cmd  
python gui_launcher.py
```

### Способ 5: Прямой запуск
```cmd
python -c "from game_monitor.gui_interface import main; main()"
```

## Устранение проблем

### Если команда "python" не работает:
```cmd
py start_gui.py
```
или
```cmd
python3 start_gui.py
```

### Если появляется ошибка импорта:
```cmd
pip install -r requirements.txt
```

### Если нужно установить Python модули:
```cmd
pip install tkinter pillow pyyaml
```

## Что должно произойти

1. ✅ Откроется окно "Game Monitor System - v1.0"
2. ✅ Появится интерфейс с кнопками Start/Stop
3. ✅ В меню Tools будет "Calibrate Coordinates" и "Test OCR"
4. ✅ В консоли появится сообщение о запуске

## Основные функции

### Настройка регионов:
- **Tools → Calibrate Coordinates**
- Выберите "Visual Select" для визуального выбора области
- Или "Manual Input" для ввода координат вручную

### Тестирование OCR:
- **Tools → Test OCR** 
- Включите "Enable Testing"
- Используйте хоткеи F1-F5 для захвата областей
- Проверьте консоль и файлы в папке `data/`

## Горячие клавиши

- **F1** - Захват списка торговцев
- **F2** - Сканирование предметов
- **F3** - Захват инвентаря торговца
- **F4** - Ручная верификация
- **F5** - Экстренная остановка

## Файлы логов

- `data/testing_output.txt` - Простой текстовый лог
- `data/testing_detailed.json` - Подробный JSON лог
- `logs/game_monitor.log` - Основной лог системы

## Если ничего не помогает

1. Убедитесь что Python установлен: `python --version`
2. Установите зависимости: `pip install tkinter pyyaml`
3. Попробуйте: `python main.py` (консольная версия)
4. Проверьте папку на права доступа