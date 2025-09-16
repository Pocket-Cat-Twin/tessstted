#!/usr/bin/env python3
"""
Скрипт для распознавания текста на изображениях через Yandex Vision OCR API
Использует API-ключ для авторизации
"""

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

# =============================================================================
# НАСТРОЙКИ
# =============================================================================

API_KEY = "your_api_key_here"
OCR_URL = "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText"

# Поддерживаемые форматы файлов
SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.pdf']
MIME_TYPES = {
    '.jpg': 'JPEG',
    '.jpeg': 'JPEG', 
    '.png': 'PNG',
    '.pdf': 'PDF'
}

# Счетчик запросов для отладки
request_count = 0

# =============================================================================
# ОСНОВНЫЕ ФУНКЦИИ
# =============================================================================

def encode_image(file_path):
    """Кодирует изображение в Base64"""
    try:
        with open(file_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"Ошибка кодирования файла {file_path}: {e}")
        return None

def get_mime_type(file_path):
    """Определяет MIME-тип по расширению файла"""
    ext = Path(file_path).suffix.lower()
    return MIME_TYPES.get(ext, 'JPEG')

def send_ocr_request(file_path):
    """Отправляет запрос в Yandex Vision OCR API"""
    global request_count
    request_count += 1
    
    print(f"\n📤 Запрос #{request_count}: {Path(file_path).name}")
    
    # Кодируем файл
    encoded_content = encode_image(file_path)
    if not encoded_content:
        return None
    
    # Подготавливаем данные
    data = {
        "mimeType": get_mime_type(file_path),
        "languageCodes": ["en"],
        "model": "page",
        "content": encoded_content
    }
    
    # Создаем запрос
    json_data = json.dumps(data).encode('utf-8')
    request = urllib.request.Request(
        OCR_URL,
        data=json_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {API_KEY}"
        }
    )
    
    try:
        print("🌐 Отправка запроса...")
        with urllib.request.urlopen(request) as response:
            if response.status == 200:
                print("✅ Запрос успешен!")
                return json.loads(response.read().decode('utf-8'))
            else:
                print(f"❌ Ошибка {response.status}")
                return None
                
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP ошибка: {e.code}")
        try:
            error_data = e.read().decode('utf-8')
            print(f"Детали ошибки: {error_data}")
        except:
            pass
        return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def extract_text(response):
    """Извлекает текст из ответа API"""
    try:
        return response['result']['textAnnotation']['fullText']
    except KeyError:
        print("❌ Не удалось извлечь текст из ответа")
        return None

def save_text(text, output_file):
    """Сохраняет текст в файл"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"💾 Сохранено: {output_file}")
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")

def find_images():
    """Находит все изображения в текущей папке"""
    current_dir = Path.cwd()
    images = []
    
    for file in current_dir.iterdir():
        if file.suffix.lower() in SUPPORTED_EXTENSIONS:
            images.append(file)
    
    return sorted(images)

def process_image(image_path):
    """Обрабатывает одно изображение"""
    print(f"\n{'='*50}")
    print(f"🖼️  Обработка: {image_path.name}")
    print(f"{'='*50}")
    
    # Отправляем запрос
    response = send_ocr_request(str(image_path))
    
    if response:
        # Извлекаем текст
        text = extract_text(response)
        
        if text:
            print(f"\n📝 Распознанный текст:")
            print("-" * 30)
            print(text.strip())
            print("-" * 30)
            
            # Сохраняем результат
            output_file = f"{image_path.stem}_text.txt"
            save_text(text, output_file)
            
            # Сохраняем JSON для отладки
            json_file = f"{image_path.stem}_response.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(response, f, ensure_ascii=False, indent=2)
            print(f"🗂️  JSON сохранен: {json_file}")
            
            return True
        else:
            print("❌ Текст не найден")
            return False
    else:
        print("❌ Запрос не выполнен")
        return False

def main():
    """Main function"""
    print("🚀 Yandex Vision OCR - Распознавание текста")
    print(f"🔑 API ключ: {API_KEY[:8]}...")
    print("-" * 50)
    
    # Определяем, что обрабатывать
    if len(sys.argv) > 1:
        # Обрабатываем конкретный файл
        file_path = Path(sys.argv[1])
        if not file_path.exists():
            print(f"❌ Файл не найден: {file_path}")
            return
        
        images = [file_path]
        print(f"📁 Режим: один файл - {file_path.name}")
        
    else:
        # Ищем все изображения в папке
        images = find_images()
        if not images:
            print("❌ Изображения не найдены в текущей папке")
            print(f"Поддерживаемые форматы: {', '.join(SUPPORTED_EXTENSIONS)}")
            return
        
        print(f"📁 Режим: все файлы в папке")
        print(f"📊 Найдено файлов: {len(images)}")
        for i, img in enumerate(images, 1):
            print(f"  {i}. {img.name}")
    
    # Обрабатываем файлы
    successful = 0
    for image in images:
        if process_image(image):
            successful += 1
    
    # Итоги
    print(f"\n🏁 ГОТОВО!")
    print(f"📊 Всего запросов: {request_count}")
    print(f"📊 Обработано файлов: {len(images)}")
    print(f"✅ Успешно: {successful}")
    print(f"❌ Ошибок: {len(images) - successful}")
    
    if request_count != len(images):
        print(f"⚠️  Внимание: количество запросов не совпадает с количеством файлов!")

if __name__ == "__main__":
    main()