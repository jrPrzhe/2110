# Исправление таймаутов и предупреждений при публикации фото

**Дата:** 24 октября 2025

---

## 🐛 Проблемы

### Проблема 1: Ложное предупреждение об артикуле
```
WARNING - No article numbers found, using original caption
```
Предупреждение показывалось **даже когда пользователь выбрал опцию "без проверки артикула"**.

### Проблема 2: Таймаут при отправке фото в Telegram
```
ERROR - Telegram error posting photo: Timed out
```
Отправка фото в Telegram группу прерывалась по таймауту (~30 секунд).

---

## ✅ Решения

### 1. Исправлено предупреждение об артикуле

**Было:**
```python
if article_numbers:
    # добавляем артикулы
else:
    enhanced_caption = caption
    logger.warning("No article numbers found, using original caption")  # ❌ Всегда
```

**Стало:**
```python
if article_numbers:
    # добавляем артикулы
else:
    enhanced_caption = caption
    # ✅ Только предупреждаем, если пользователь ОЖИДАЛ артикулы
    if user_state.get('check_articles', False):
        logger.warning("No article numbers found despite check_articles=True...")
    else:
        logger.info("Using original caption without article numbers (check_articles=False)")
```

**Где:** `handlers/admin_handler.py` - строки 820-831

---

### 2. Добавлены таймауты для отправки фото

#### 2.1. Метод `post_photo()` (одно фото)

**Было:**
```python
await self.bot.send_photo(
    chat_id=self.group_id,
    photo=photo_file,
    caption=caption,
    parse_mode='HTML'
    # ❌ Нет таймаутов
)
```

**Стало:**
```python
async def send_photo_task():
    with open(photo_path, 'rb') as photo_file:
        await self.bot.send_photo(
            chat_id=self.group_id,
            photo=photo_file,
            caption=caption,
            parse_mode='HTML',
            read_timeout=120,      # ✅ 2 минуты
            write_timeout=120,     # ✅ 2 минуты
            connect_timeout=60     # ✅ 1 минута
        )

# ✅ Общий таймаут 3 минуты
await asyncio.wait_for(send_photo_task(), timeout=180)
```

**Где:** `services/telegram_service.py` - строки 23-64

#### 2.2. Метод `post_album()` (альбом фото)

Аналогичные изменения для отправки альбома:
- `read_timeout=120`
- `write_timeout=120`
- `connect_timeout=60`
- Общий таймаут: 180 секунд (3 минуты)

**Где:** `services/telegram_service.py` - строки 66-125

---

## 📊 Таймауты

### Для фото (одно или альбом)

| Операция | Старое значение | Новое значение |
|----------|-----------------|----------------|
| Подключение | не задано | 60 сек |
| Чтение | не задано | 120 сек (2 мин) |
| Запись | не задано | 120 сек (2 мин) |
| **Общий таймаут** | **не задано** | **180 сек (3 мин)** |

### Для видео (из предыдущего фикса)

| Операция | Значение |
|----------|----------|
| Подключение | 60 сек |
| Чтение | 180 сек (3 мин) |
| Запись | 180 сек (3 мин) |
| **Общий таймаут** | **360 сек (6 мин)** |

---

## 🧪 Тестирование

### Тест 1: Публикация без артикула

1. Нажмите "🚀 Начать публикацию"
2. Выберите "📷 Обычный пост"
3. Выберите платформу (например, "📱 Telegram")
4. **Выберите "✖️ Без проверки артикулов"**
5. Отправьте фото
6. Отправьте подпись

**Ожидается:**
- ✅ Фото публикуется без артикулов
- ✅ В логах: `INFO - Using original caption without article numbers (check_articles=False)`
- ❌ НЕ должно быть: `WARNING - No article numbers found`

### Тест 2: Публикация с артикулом

1. Аналогично, но выберите "✔️ С проверкой артикулов"
2. Отправьте фото с артикулом (или без)

**Ожидается:**
- Если артикул найден: добавляется в подпись
- Если артикул НЕ найден: `WARNING - No article numbers found despite check_articles=True`

### Тест 3: Медленное соединение

1. Публикуйте фото при медленном интернете
2. Процесс может занять до 3 минут

**Ожидается:**
- ✅ Успешная отправка за 1-3 минуты
- ❌ Не должно быть таймаута через 30 секунд (как раньше)

---

## 🚀 Что делать после обновления

### 1. Установите недостающие зависимости

```bash
cd auto-poster-bot
pip install -r requirements.txt
```

Это установит **moviepy** (для публикации видео в Instagram) и другие обновленные пакеты.

### 2. Перезапустите бота

```bash
# Остановите текущий процесс (Ctrl+C)
python main.py
```

### 3. Проверьте работу

Попробуйте опубликовать:
- Одно фото с опцией "без артикула"
- Альбом фото
- Видео/рилс

---

## 📝 Измененные файлы

1. **handlers/admin_handler.py**
   - Строки 820-831: логика предупреждения об артикуле

2. **services/telegram_service.py**
   - Строки 23-64: метод `post_photo()` с таймаутами
   - Строки 66-125: метод `post_album()` с таймаутами

3. **requirements.txt**
   - Добавлены: `google-generativeai`, `moviepy>=1.0.3`

---

## ⚠️ Известные ограничения

### Telegram Bot API лимиты:
- **Фото:** до 10 МБ
- **Видео:** до 50 МБ
- **Альбом:** до 10 фото

### Если таймаут все равно происходит:

1. **Проверьте размер файла:**
   ```bash
   # Windows
   dir auto-poster-bot\uploads\*.jpg
   
   # Linux/Mac
   ls -lh auto-poster-bot/uploads/*.jpg
   ```

2. **Проверьте скорость интернета:**
   - Для загрузки 5 МБ фото нужно ~30 секунд при скорости 1 Мбит/с
   - При скорости < 0.5 Мбит/с может не хватить 3 минут

3. **Увеличьте таймауты** (если нужно):
   ```python
   # В telegram_service.py
   read_timeout=240,      # 4 минуты
   write_timeout=240,     # 4 минуты
   timeout=300            # 5 минут общий
   ```

---

## 📚 Связанные документы

- `REELS_DOWNLOAD_TIMEOUT_FIX.md` - исправление скачивания рилсов
- `REELS_PREVIEW_HANG_FIX.md` - исправление предпросмотра рилсов
- `SUMMARY_TIMEOUT_FIX.md` - общее резюме по таймаутам
- `CHANGELOG_REELS_FIXES_OCT24.md` - полный changelog

---

**Статус:** ✅ Готово к использованию  
**Тестирование:** ✅ Необходимо протестировать  
**Приоритет:** 🔥 Высокий (критические исправления)

---

_Последнее обновление: 24 октября 2025_

