# Исправление ошибки таймаута при скачивании рилсов

## Дата: 24 октября 2025

## Проблема

При скачивании рилсов из Instagram возникала ошибка:
```
Error during video download: HTTPSConnectionPool(host='instagram.fala5-2.fna.fbcdn.net', port=443): 
Max retries exceeded with url: /o1/v/t16/f2/m261/AQM...
(Caused by ConnectTimeoutError(..., 'Connection to instagram.fala5-2.fna.fbcdn.net timed out. (connect timeout=1)'))
```

**Альтернативный метод** также не работал:
```
Could not find video URL in embed page
```

## Причины

1. **Слишком короткий таймаут подключения** - библиотека `instagrapi` по умолчанию использовала таймаут всего 1 секунду для подключения к CDN серверам Instagram
2. **Недостаточная обработка embed страниц** - альтернативный метод использовал только один паттерн для поиска video_url

## Решение

### 1. Увеличены таймауты в instagrapi клиенте

В `instagram_service.py`:

```python
def __init__(self):
    """Initialize the Instagram service."""
    self.client = Client()
    # Set longer timeouts for better stability (especially for video downloads)
    self.client.request_timeout = 30  # 30 seconds for general requests
    self.client.private.request_timeout = 30  # 30 seconds for private API
```

Также обновлен метод `reset_session()` для применения таймаутов при пересоздании клиента.

### 2. Улучшен альтернативный метод скачивания

Добавлено несколько паттернов для поиска video_url в embed странице:

1. **Pattern 1**: `"video_url":"([^"]+)"` - JSON формат
2. **Pattern 2**: `<video[^>]*src="([^"]+)"` - прямой source тег
3. **Pattern 3**: `<meta property="og:video" content="([^"]+)"` - OpenGraph meta tag
4. **Pattern 4**: `(https://[^"\s]+\.mp4[^"\s]*)` - любой .mp4 URL

### 3. Обновлены таймауты в requests

```python
# Для embed страницы
response = requests.get(embed_url, headers=headers, timeout=30)

# Для скачивания видео (30 сек на подключение, без лимита на чтение)
video_response = requests.get(video_url, headers=headers, stream=True, timeout=(30, None))
```

## Измененные файлы

- `services/instagram_service.py`:
  - Метод `__init__()` - добавлены таймауты для клиента
  - Метод `reset_session()` - добавлены таймауты при пересоздании
  - Метод `_download_reels_alternative()` - улучшен поиск video_url и таймауты
  - Метод `get_reels_caption()` - обновлен таймаут

## Тестирование

После применения изменений:

1. Запустите бота
2. Попробуйте скачать рилс через команду или отправку URL
3. Проверьте логи на наличие успешного скачивания

Ожидаемое поведение:
- Скачивание через instagrapi API должно работать с увеличенным таймаутом
- Если первый метод не сработает, альтернативный метод попробует несколько паттернов для поиска video_url
- В логах должно быть: `Reels downloaded successfully: <path>`

## Преимущества

✅ Стабильное скачивание рилсов даже при медленном соединении  
✅ Множественные фолбэк-методы для извлечения video_url  
✅ Более детальное логирование для диагностики  
✅ Правильная обработка таймаутов для streaming загрузки

## Дополнительные улучшения

Если проблемы сохраняются:

1. Увеличьте `request_timeout` до 60 секунд для очень медленных соединений
2. Проверьте сетевое подключение к Instagram CDN
3. Попробуйте использовать прокси (если нужно)
4. Проверьте логи на детальную информацию об ошибках

