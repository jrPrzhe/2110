# 📊 Функция Прогресса Скачивания и Отмены

## 📝 Описание

Добавлена возможность отслеживать прогресс скачивания рилсов из Instagram в реальном времени с возможностью отмены процесса в любой момент.

## ✨ Возможности

### 1. **Отслеживание Прогресса**
- 📊 Визуальный прогресс-бар загрузки
- 📈 Процент выполнения
- 💾 Размер скачанных данных (МБ)
- 🕐 Обновление каждые 2 секунды

### 2. **Отмена Скачивания**
- ⏹️ Кнопка "Отменить" во время загрузки
- 🔄 Мгновенная реакция на отмену
- 🗑️ Автоматическое удаление частично скачанных файлов

### 3. **Отсутствие Таймаута**
- ⏱️ Скачивание без ограничения времени
- 📥 Полная загрузка больших файлов
- 🌐 Адаптация к медленному интернету

## 🔧 Технические Детали

### Изменения в `instagram_service.py`

```python
def download_reels(self, url: str, progress_callback=None, cancel_check=None) -> Optional[str]:
    """
    Download reels/video from Instagram URL.
    
    Args:
        url: Instagram reels/video URL
        progress_callback: Optional callback function(downloaded, total) for progress updates
        cancel_check: Optional function that returns True if download should be cancelled
        
    Returns:
        str: Path to downloaded video file or None if failed
    """
```

**Ключевые изменения:**
- ✅ `timeout=None` для requests - скачивание до конца
- ✅ Проверка `cancel_check()` в цикле загрузки
- ✅ Вызов `progress_callback(downloaded, total)` при получении данных
- ✅ Удаление частичного файла при отмене

### Изменения в `admin_handler.py`

**1. Новый метод `handle_cancel_download()`:**
```python
async def handle_cancel_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle download cancellation via callback button."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_state = self.get_user_state(user_id)
    
    # Set cancellation flag
    user_state['cancel_download'] = True
```

**2. Обновленный метод `handle_reels_url_input()`:**
- ✅ Создание inline-кнопки "Отменить"
- ✅ Progress callback для обновления UI
- ✅ Cancel check для проверки флага отмены
- ✅ Запуск в executor для неблокирующей работы
- ✅ Красивый прогресс-бар: `[████████████░░░░░░░░]`

**3. Обновление `on_callback()`:**
```python
# Handle cancel download callback
if cq.data == 'cancel_download':
    await self.handle_cancel_download(update, context)
    return
```

## 💡 Пример Использования

### 1. **Начало Скачивания**
```
⏳ Скачиваю рилс из Instagram...

📊 Подготовка к скачиванию...

[⏹️ Отменить]  ← Кнопка
```

### 2. **Во Время Скачивания**
```
⏳ Скачиваю рилс из Instagram...

📊 Прогресс: 47.3%
[█████████░░░░░░░░░░░]

💾 Скачано: 12.45 МБ / 26.32 МБ

[⏹️ Отменить]  ← Кнопка
```

### 3. **Завершение**
```
✅ Рилс успешно скачан!

Отправляю предпросмотр...
```

### 4. **При Отмене**
```
⏹️ Отмена скачивания...

Ожидайте завершения текущего блока данных.
```

Затем:
```
❌ Скачивание отменено

Вы можете начать новую публикацию.
```

## 🎯 Преимущества

### Для Пользователя
- ✅ Видимость процесса
- ✅ Контроль над операцией
- ✅ Нет зависания на больших файлах
- ✅ Можно отменить в любой момент

### Технические
- ✅ Нет таймаутов - скачивается полностью
- ✅ Асинхронная работа - не блокирует бота
- ✅ Память управляется правильно (stream=True, chunk_size)
- ✅ Автоочистка при отмене

## 📊 Обработка Состояний

```
user_state['cancel_download'] = False  # При начале
user_state['cancel_download'] = True   # При нажатии отмены
```

Проверка в цикле скачивания:
```python
if cancel_check and cancel_check():
    logger.info("Download cancelled by user")
    if os.path.exists(video_path):
        os.remove(video_path)  # Удалить частичный файл
    return None
```

## 🛡️ Обработка Ошибок

### 1. **Ошибка При Обновлении Прогресса**
```python
except Exception as e:
    logger.error(f"Error updating progress: {e}")
    # Продолжаем скачивание даже если UI не обновился
```

### 2. **Частичный Файл При Отмене**
```python
if os.path.exists(video_path):
    os.remove(video_path)  # Очистка
```

### 3. **Неизвестный Размер Файла**
```python
total_size = int(video_response.headers.get('content-length', 0))
if total_size > 0:
    # Показываем прогресс
else:
    # Скачиваем без индикатора процента
```

## 🔄 Интеграция с Существующим Кодом

### Обратная Совместимость
```python
# Старый вызов все еще работает:
video_path = download_reels(url)

# Новый вызов с callbacks:
video_path = download_reels(
    url,
    progress_callback=my_progress_func,
    cancel_check=my_cancel_func
)
```

## 📈 Производительность

### Оптимизации
- ✅ Обновление UI только раз в 2 секунды (rate limiting)
- ✅ Chunk size 8192 байт для оптимальной скорости
- ✅ Stream=True для экономии памяти
- ✅ Async executor для неблокирующей работы

### Нагрузка
- CPU: Минимальная (только проверка флага)
- RAM: Константная (streaming, не загружаем весь файл)
- Network: Оптимальная (chunk-based download)

## 🔮 Будущие Улучшения

### Возможные Доработки
1. ⚡ Показ скорости загрузки (МБ/с)
2. ⏱️ Оценка оставшегося времени (ETA)
3. 📊 История скачиваний
4. 🔄 Автопауза/возобновление при проблемах с сетью
5. 💾 Кэширование уже скачанных рилсов

## 📝 Changelog

### v1.0.0 (2025-10-21)
- ✅ Добавлен прогресс-бар скачивания
- ✅ Добавлена кнопка отмены
- ✅ Убран таймаут скачивания
- ✅ Автоудаление частичных файлов
- ✅ Асинхронная обработка через executor

## 🎓 Примеры Callback Функций

### Progress Callback
```python
async def progress_callback(downloaded: int, total: int):
    """Update progress message."""
    percent = (downloaded / total) * 100 if total > 0 else 0
    downloaded_mb = downloaded / (1024 * 1024)
    total_mb = total / (1024 * 1024)
    
    progress_bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
    
    await message.edit_text(
        f"📊 Прогресс: {percent:.1f}%\n"
        f"[{progress_bar}]\n"
        f"💾 Скачано: {downloaded_mb:.2f} МБ / {total_mb:.2f} МБ"
    )
```

### Cancel Check
```python
def cancel_check():
    """Check if download should be cancelled."""
    return user_state.get('cancel_download', False)
```

## 🚀 Использование

Функция автоматически активируется при публикации рилсов:
1. Отправить команду `/start` или "🚀 Начать публикацию"
2. Выбрать "📹 Публикация рилс"
3. Выбрать платформу
4. Отправить ссылку на рилс
5. **Наблюдать прогресс с возможностью отмены** ← Новое!

## ⚠️ Важные Замечания

1. **Rate Limiting**: UI обновляется максимум раз в 2 секунды
2. **Async Context**: Progress callback вызывается из другого потока
3. **File Cleanup**: Всегда удаляйте частичные файлы при отмене
4. **Network Resilience**: Timeout=None может зависнуть на мертвом соединении (редко)

## 🔗 Связанные Файлы

- `services/instagram_service.py` - Логика скачивания
- `handlers/admin_handler.py` - UI и callback обработка
- `main.py` - Регистрация callback handler

---

**Автор**: AI Assistant  
**Дата**: 21 октября 2025  
**Версия**: 1.0.0


