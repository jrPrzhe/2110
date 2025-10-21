# Установка и запуск с поддержкой VK

## Быстрый старт

### 1. Установите зависимости

```bash
cd auto-poster-bot
pip install -r requirements.txt
```

Новая зависимость для VK:
- `vk-api==11.9.9` - библиотека для работы с VK API

### 2. Настройте переменные окружения

Скопируйте `env.example` в `.env`:
```bash
cp env.example .env
```

Отредактируйте `.env` и добавьте VK параметры:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ADMIN_USER_ID=your_admin_user_id
TELEGRAM_GROUP_ID=your_telegram_group_id

# Instagram
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password

# VK (НОВОЕ!)
VK_ACCESS_TOKEN=ваш_vk_access_token
VK_GROUP_ID=ваш_vk_group_id

# Google AI
GOOGLE_API_KEY=your_google_ai_studio_api_key
```

### 3. Получите VK токен и ID группы

Подробные инструкции см. в [VK_SETUP.md](VK_SETUP.md)

**Краткая версия:**

1. **Получите ID группы:**
   - Откройте вашу группу: https://vk.com/psyqk
   - Используйте сервис https://regvk.com/id/ для получения числового ID

2. **Получите Access Token:**
   - Создайте VK приложение: https://vk.com/apps?act=manage
   - Тип: "Standalone приложение"
   - **Базовый домен:** оставьте пустым или укажите `localhost`
   - Скопируйте APP_ID вашего приложения
   - Используйте ссылку (замените APP_ID на ваш):
     ```
     https://oauth.vk.com/authorize?client_id=APP_ID&scope=wall,photos,groups,offline&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token
     ```
   - Скопируйте токен из адресной строки после авторизации

### 4. Запустите бота

```bash
python main.py
```

Вы должны увидеть в логах:
```
INFO - Configuration validated successfully
INFO - Instagram service initialized successfully
INFO - Telegram service initialized successfully
INFO - VK service initialized successfully
INFO - VK connection successful: Название вашей группы
INFO - Auto-Poster Bot started successfully!
```

## Использование VK в боте

После запуска бота:

1. Отправьте `/start` боту в Telegram
2. Нажмите **"🚀 Начать публикацию"**
3. Выберите тип поста:
   - 📷 Одиночный пост
   - 📸 Массовый пост

4. **Выберите платформу для публикации:**
   - **📷 Instagram** - публикация только в Instagram
   - **💬 Telegram** - публикация только в Telegram
   - **🔵 VK** - публикация только в VK ✨ **НОВОЕ!**
   - **🔀 Все платформы** - публикация в Instagram, Telegram И VK одновременно ✨ **ОБНОВЛЕНО!**

5. Выберите, нужно ли искать артикулы на фото
6. Загрузите фото
7. Введите подпись к посту
8. Выберите время публикации (сейчас или запланировать)

## Что изменилось

### Новые файлы:
- `services/vk_service.py` - сервис для работы с VK API
- `VK_SETUP.md` - подробная инструкция по настройке VK
- `INSTALL_VK.md` - эта инструкция

### Обновленные файлы:
- `requirements.txt` - добавлена библиотека `vk-api`
- `config.py` - добавлены параметры `VK_ACCESS_TOKEN` и `VK_GROUP_ID`
- `env.example` - добавлены примеры VK параметров
- `handlers/admin_handler.py` - добавлена поддержка VK платформы
- `main.py` - добавлена инициализация VK сервиса

### Новые возможности:
- ✅ Публикация одиночных фото в VK
- ✅ Публикация альбомов (до 10 фото) в VK
- ✅ Автоматическое добавление артикулов в подпись VK поста
- ✅ Публикация одновременно в Instagram, Telegram и VK
- ✅ Выбор только VK для публикации
- ✅ Проверка соединения с VK при старте

## Проверка работы

### Проверьте, что VK настроен правильно:

1. Запустите бота и проверьте логи
2. Если видите "VK service initialized successfully" - всё хорошо!
3. Если видите "VK connection failed" - проверьте токен и ID группы

### Тестовая публикация:

1. Отправьте `/start` боту
2. Нажмите "🚀 Начать публикацию"
3. Выберите "📷 Одиночный пост"
4. Выберите "🔵 VK"
5. Выберите "⏭️ Нет, пропустить" (для теста без артикулов)
6. Отправьте тестовое фото
7. Введите подпись "Тест публикации в VK"
8. Нажмите "⚡ Опубликовать сейчас"

Если всё настроено правильно, пост появится в вашей группе VK!

## Troubleshooting

### VK не инициализируется
```
VK connection failed - bot will continue but VK posting may not work
```

**Решение:**
- Проверьте файл `.env` - есть ли `VK_ACCESS_TOKEN` и `VK_GROUP_ID`
- Проверьте правильность токена
- Убедитесь, что вы администратор группы

### Ошибка при публикации в VK
```
Error posting photo to VK: ...
```

**Возможные причины:**
- Токен недействителен или истёк
- Недостаточно прав у токена (нужны: wall, photos, groups)
- Неправильный ID группы
- Проблемы с размером или форматом фото

**Решение:**
- Получите новый токен (см. [VK_SETUP.md](VK_SETUP.md))
- Проверьте права токена
- Убедитесь, что ID группы числовой

### Бот запускается, но кнопка VK не работает

**Решение:**
- Перезапустите бота
- Отправьте `/start` заново
- Проверьте, что используете последнюю версию кода

## Безопасность

⚠️ **ВАЖНО:**

- Файл `.env` содержит секретные токены - НЕ публикуйте его
- Добавьте `.env` в `.gitignore`
- Регулярно обновляйте токены
- Используйте токены только для доверенных приложений

## Дополнительная информация

- [VK_SETUP.md](VK_SETUP.md) - Подробная настройка VK
- [README.md](README.md) - Общая документация бота
- [VK API Docs](https://dev.vk.com/ru) - Официальная документация VK API

## Поддержка

Если возникли проблемы:
1. Проверьте логи бота на наличие ошибок
2. Убедитесь, что все зависимости установлены
3. Проверьте правильность токенов и ID
4. Прочитайте [VK_SETUP.md](VK_SETUP.md) для детальной настройки

