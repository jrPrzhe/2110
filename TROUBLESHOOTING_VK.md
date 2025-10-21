# 🔧 Решение проблем VK

## ❌ Ошибка: "method is unavailable with service token"

### Полная ошибка в логах:
```
[28] Application authorization failed: method is unavailable with service token
```

### ❗ Причина
Вы используете **сервисный ключ** из настроек приложения VK вместо **пользовательского токена**.

Сервисный ключ **НЕ МОЖЕТ** загружать фото на стену группы!

---

## ✅ Быстрое решение (5 минут)

### Шаг 1: Найдите APP_ID

1. Откройте: https://vk.com/apps?act=manage
2. Нажмите на ваше приложение
3. Скопируйте **ID приложения** (APP_ID)
   - В URL: `https://vk.com/editapp?id=12345678`
   - Число после `id=` - это ваш APP_ID

### Шаг 2: Получите правильный токен

1. **Скопируйте эту ссылку:**
   ```
   https://oauth.vk.com/authorize?client_id=APP_ID&scope=wall,photos,groups,offline&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token
   ```

2. **Замените `APP_ID` на ваш ID**
   
   Например, если APP_ID = `12345678`:
   ```
   https://oauth.vk.com/authorize?client_id=12345678&scope=wall,photos,groups,offline&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token
   ```

3. **Откройте ссылку в браузере**

4. **Нажмите "Разрешить"** для доступа приложению

5. **Скопируйте токен** из адресной строки:
   
   Адресная строка после редиректа:
   ```
   https://oauth.vk.com/blank.html#access_token=vk1.a.aBcDeFgH...&expires_in=0&user_id=123456
   ```
   
   Скопируйте **всё** между `access_token=` и `&expires_in`:
   ```
   vk1.a.aBcDeFgHiJkLmNoPqRsTuVwXyZ123456789...
   ```

### Шаг 3: Обновите .env

Откройте файл `.env` и **замените** старый токен:

```env
VK_ACCESS_TOKEN=vk1.a.ваш_новый_длинный_токен_здесь
VK_GROUP_ID=123456789
```

**ВАЖНО:**
- Токен должен быть **длинным** (85+ символов)
- Должен начинаться с `vk1.a.`
- НЕ используйте короткий сервисный ключ!

### Шаг 4: Перезапустите бота

```bash
python main.py
```

### Шаг 5: Проверьте логи

Должно быть:
```
✅ VK service initialized successfully
✅ VK connection successful: Название вашей группы
```

### Шаг 6: Попробуйте опубликовать

Отправьте тестовый пост в бота. Должно работать!

---

## 🔍 Как отличить токены

### ❌ Сервисный ключ (НЕПРАВИЛЬНО)

**Где находится:**
- Настройки приложения VK
- "Настройки" → "Ключи доступа"
- "Сервисный ключ доступа"

**Как выглядит:**
- Короткий (30-40 символов)
- Пример: `abc123def456ghi789jkl012mno345pqr678`

**Что умеет:**
- ❌ НЕ может загружать фото
- ❌ НЕ может публиковать на стену
- ✅ Только чтение информации

---

### ✅ Пользовательский токен (ПРАВИЛЬНО)

**Где получить:**
- Только через OAuth (ссылка выше)
- НЕ в настройках приложения!

**Как выглядит:**
- Длинный (85+ символов)
- Начинается с `vk1.a.`
- Пример: `vk1.a.aBcDeFgHiJkLmNoPqRsTuVwXyZ123456789aBcDeFgHiJkLmNoPqRsTuVwXyZ123456789...`

**Что умеет:**
- ✅ Загружать фото
- ✅ Публиковать на стену
- ✅ Создавать посты и альбомы
- ✅ Всё, что нужно для бота!

---

## 📝 Пошаговый пример

### Пример получения токена:

1. **Ваш APP_ID:** `51740697`

2. **Ссылка:**
   ```
   https://oauth.vk.com/authorize?client_id=51740697&scope=wall,photos,groups,offline&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token
   ```

3. **Открываете в браузере** → Нажимаете "Разрешить"

4. **После редиректа адресная строка:**
   ```
   https://oauth.vk.com/blank.html#access_token=vk1.a.aBcDeFgHiJkLmNoPqRsTuVwXyZ123456789aBcDeFgHiJkLmNoPqRsTuVwXyZ123&expires_in=0&user_id=123456789
   ```

5. **Копируете токен:**
   ```
   vk1.a.aBcDeFgHiJkLmNoPqRsTuVwXyZ123456789aBcDeFgHiJkLmNoPqRsTuVwXyZ123
   ```

6. **В .env:**
   ```env
   VK_ACCESS_TOKEN=vk1.a.aBcDeFgHiJkLmNoPqRsTuVwXyZ123456789aBcDeFgHiJkLmNoPqRsTuVwXyZ123
   VK_GROUP_ID=123456789
   ```

---

## ⚠️ Другие частые ошибки

### "Access denied"
- Убедитесь, что вы **администратор группы**
- Проверьте права токена (должны быть: wall, photos, groups)

### "Invalid group id"
- ID должен быть числовым: `123456789` ✅
- НЕ используйте: `-123456789` ❌
- НЕ используйте: `psyqk` ❌

### "VK connection failed"
- Проверьте, что `VK_ACCESS_TOKEN` и `VK_GROUP_ID` есть в `.env`
- Убедитесь, что используете правильный токен (см. выше)

---

## 🆘 Всё ещё не работает?

### Проверьте:
1. [ ] Токен длинный (85+ символов)
2. [ ] Токен начинается с `vk1.a.`
3. [ ] Вы администратор группы VK
4. [ ] `.env` файл сохранён
5. [ ] Бот перезапущен после изменения `.env`
6. [ ] APP_ID правильный (из настроек приложения)
7. [ ] В OAuth ссылке APP_ID заменён на ваш

### Посмотрите логи:
```bash
python main.py
```

Ищите строки с `[VK]` или `vk -`:
- `✅ VK service initialized successfully` - хорошо
- `❌ Error uploading photo to VK` - ошибка

### Прочитайте документацию:
- [VK_SETUP.md](VK_SETUP.md) - Полная настройка
- [FAQ_VK.md](FAQ_VK.md) - Часто задаваемые вопросы
- [QUICK_START_VK.md](QUICK_START_VK.md) - Быстрый старт

---

## ✅ Чек-лист

Перед публикацией проверьте:

- [ ] Используете пользовательский токен (НЕ сервисный ключ)
- [ ] Токен начинается с `vk1.a.`
- [ ] Токен длинный (85+ символов)
- [ ] Вы администратор VK группы
- [ ] `VK_GROUP_ID` - числовой ID группы
- [ ] `.env` файл обновлён
- [ ] Бот перезапущен
- [ ] В логах `VK connection successful`

---

**Последнее обновление:** 21 октября 2025  
**Версия:** 1.0

