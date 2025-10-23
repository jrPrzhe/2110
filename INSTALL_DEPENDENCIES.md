# 📦 Установка зависимостей

## Быстрая установка

```bash
# 1. Перейдите в папку проекта
cd auto-poster-bot

# 2. Активируйте виртуальное окружение (если есть)
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Установите все зависимости
pip install -r requirements.txt
```

---

## Список зависимостей

### Основные (обязательные):

| Пакет | Версия | Назначение |
|-------|--------|------------|
| `python-telegram-bot` | 20.8 | Telegram Bot API |
| `instagrapi` | 1.19.8 | Instagram API |
| `Pillow` | 10.3.0 | Обработка изображений |
| `python-dotenv` | 1.0.1 | Загрузка .env файла |
| `requests` | 2.32.5 | HTTP запросы |
| `httpx` | ~0.26.0 | Async HTTP клиент |

### Дополнительные (для расширенных функций):

| Пакет | Версия | Назначение | Обязательно? |
|-------|--------|------------|--------------|
| `moviepy` | >=1.0.3 | **Публикация видео в Instagram** | ✅ **ДА** |
| `google-generativeai` | 0.3.1 | AI улучшение подписей | Нет |
| `pytesseract` | 0.3.10 | OCR распознавание артикулов | Нет |
| `opencv-python` | 4.12.0.88 | Расширенная обработка изображений | Нет |
| `vk-api` | 11.9.9 | VK API | Нет |
| `aiohttp` | 3.9.1 | Async HTTP | Нет |

---

## ⚠️ Критическая зависимость: moviepy

### Для чего нужна?

`moviepy` **обязательна** для:
- ✅ Публикации видео в Instagram
- ✅ Публикации рилсов в Instagram
- ✅ Обработки видео файлов

### Ошибка при отсутствии:

```
ERROR - Error posting video to Instagram: Please install moviepy>=1.0.3 and retry
```

### Установка:

```bash
pip install moviepy>=1.0.3
```

### Если не устанавливается:

```bash
# Windows: может потребоваться Visual C++
# Установите Build Tools: https://visualstudio.microsoft.com/downloads/

# Linux: установите зависимости
sudo apt-get install ffmpeg

# Mac:
brew install ffmpeg

# Затем снова:
pip install moviepy
```

---

## Опциональные зависимости

### Google AI (для улучшения подписей)

Если не установлена, бот будет работать без AI улучшения подписей.

```bash
pip install google-generativeai==0.3.1
```

Не забудьте добавить в `.env`:
```
GOOGLE_API_KEY=your_api_key_here
```

### Tesseract OCR (для распознавания артикулов)

Если не установлена, распознавание артикулов с фото не будет работать.

**Windows:**
1. Скачайте: https://github.com/UB-Mannheim/tesseract/wiki
2. Установите (например, в `C:\Program Files\Tesseract-OCR`)
3. Добавьте в PATH или укажите путь в коде

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

**Mac:**
```bash
brew install tesseract
```

Затем:
```bash
pip install pytesseract==0.3.10
```

---

## Проверка установки

### 1. Проверить все пакеты:

```bash
pip list
```

Убедитесь, что все пакеты из `requirements.txt` установлены.

### 2. Проверить moviepy:

```python
python -c "import moviepy; print('moviepy OK')"
```

Если выводит `moviepy OK` - всё работает.

### 3. Проверить tesseract (опционально):

```python
python -c "import pytesseract; print('pytesseract OK')"
```

### 4. Проверить Google AI (опционально):

```python
python -c "import google.generativeai; print('Google AI OK')"
```

---

## Обновление зависимостей

### Обновить все пакеты:

```bash
pip install --upgrade -r requirements.txt
```

### Обновить конкретный пакет:

```bash
pip install --upgrade instagrapi
pip install --upgrade python-telegram-bot
```

---

## Решение проблем

### Ошибка: "No module named 'moviepy'"

```bash
pip install moviepy>=1.0.3
```

### Ошибка: "Could not find a version that satisfies the requirement"

```bash
# Обновите pip
python -m pip install --upgrade pip

# Попробуйте снова
pip install -r requirements.txt
```

### Ошибка: "Permission denied" (Linux/Mac)

```bash
pip install --user -r requirements.txt
# или с sudo (не рекомендуется)
sudo pip install -r requirements.txt
```

### Конфликты версий

```bash
# Переустановите всё с нуля
pip uninstall -y -r requirements.txt
pip install -r requirements.txt
```

---

## Виртуальное окружение (рекомендуется)

### Создать новое:

```bash
# Windows:
python -m venv venv
venv\Scripts\activate

# Linux/Mac:
python3 -m venv venv
source venv/bin/activate
```

### После активации:

```bash
pip install -r requirements.txt
```

### Деактивировать:

```bash
deactivate
```

---

## После установки

1. **Проверьте `.env` файл:**
   ```bash
   # Скопируйте example
   cp env.example .env
   
   # Заполните все значения
   nano .env  # или notepad .env на Windows
   ```

2. **Запустите бота:**
   ```bash
   python main.py
   ```

3. **Проверьте логи:**
   - Должны быть успешные подключения к Telegram, Instagram, VK
   - Не должно быть ошибок об отсутствующих модулях

---

## Минимальная конфигурация (без опций)

Если хотите работать только с базовыми функциями:

```txt
python-telegram-bot==20.8
instagrapi==1.19.8
Pillow==10.3.0
python-dotenv==1.0.1
requests==2.32.5
httpx~=0.26.0
moviepy>=1.0.3
```

Это позволит:
- ✅ Публиковать фото и видео
- ✅ Работать с Telegram и Instagram
- ❌ Не будет AI улучшения
- ❌ Не будет OCR артикулов
- ❌ Не будет VK

---

**Итого: moviepy обязательна для видео!**

```bash
pip install moviepy>=1.0.3
```

---

_Последнее обновление: 24 октября 2025_

