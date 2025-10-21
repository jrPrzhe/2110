# 🚀 Развертывание Auto-Poster Bot на VDS

Полное руководство по переносу и запуску Telegram бота на VDS сервере.

---

## 📋 Оглавление

1. [Быстрый старт](#быстрый-старт)
2. [Характеристики сервера](#характеристики-сервера)
3. [Файлы проекта](#файлы-проекта)
4. [Пошаговая инструкция](#пошаговая-инструкция)
5. [Управление ботом](#управление-ботом)

---

## ⚡ Быстрый старт

### Шаг 1: Загрузите проект на сервер

**С вашего компьютера (Windows PowerShell):**

```powershell
cd C:\Users\Димааас\Documents\app-inst
scp -r auto-poster-bot root@ВАШ_IP:/root/app-inst/
```

### Шаг 2: Установите на сервере

**Подключитесь к серверу:**

```bash
ssh root@ВАШ_IP
```

**Запустите установку:**

```bash
cd /root/app-inst/auto-poster-bot
chmod +x deploy.sh
./deploy.sh
```

### Шаг 3: Настройте конфигурацию

```bash
nano .env
```

Заполните:
- `TELEGRAM_BOT_TOKEN` - от @BotFather
- `ADMIN_USER_ID` - от @userinfobot
- `TELEGRAM_GROUP_ID` - ID канала/группы
- `INSTAGRAM_USERNAME` - логин Instagram
- `INSTAGRAM_PASSWORD` - пароль Instagram
- Остальные опционально

Сохраните: `Ctrl+X`, `Y`, `Enter`

### Шаг 4: Запустите бота

```bash
systemctl start auto-poster-bot
journalctl -u auto-poster-bot -f
```

### Готово! 🎉

Напишите `/start` вашему боту в Telegram.

---

## 💻 Характеристики сервера

**Ваш VDS:**
- OS: Ubuntu 22.04 LTS
- CPU: 1x 2.2 GHz
- RAM: 512 MB
- HDD: 10 GB

**Минимальные требования:**
- ✅ Ubuntu 22.04
- ✅ Python 3.8+
- ✅ 512 MB RAM (с swap)
- ✅ 5 GB свободного места

⚠️ **Важно:** При 512 MB RAM обязательно настройте swap (автоматически создается скриптом `deploy.sh`)

---

## 📁 Файлы проекта

### Основные файлы

```
auto-poster-bot/
├── main.py                    # Точка входа
├── config.py                  # Конфигурация
├── requirements.txt           # Зависимости Python
├── env.example               # Пример .env файла
│
├── handlers/                 # Обработчики команд
│   └── admin_handler.py
│
├── services/                 # Сервисы
│   ├── instagram_service.py  # Instagram API
│   ├── telegram_service.py   # Telegram API
│   ├── vk_service.py        # VK API
│   └── ai_service.py        # Google AI
│
└── utils/                    # Утилиты
    ├── article_extractor.py  # Распознавание артикулов
    └── image_processor.py    # Обработка изображений
```

### Файлы для развертывания

```
📄 DEPLOYMENT.md              # Полная инструкция по развертыванию
📄 QUICK_DEPLOY.md            # Краткая инструкция
📄 TRANSFER_GUIDE.md          # Способы загрузки на сервер
📄 README_DEPLOY.md           # Этот файл

🔧 deploy.sh                  # Скрипт автоустановки
🔧 update.sh                  # Скрипт обновления
🔧 monitor.sh                 # Мониторинг бота
🔧 create_archive.sh          # Создание архива

⚙️ auto-poster-bot.service    # systemd сервис
📝 .gitignore                 # Git ignore
```

---

## 📚 Пошаговая инструкция

Выберите подходящий уровень детализации:

### 1. Для опытных пользователей
→ [QUICK_DEPLOY.md](QUICK_DEPLOY.md) - быстрый старт

### 2. Для всех остальных
→ [DEPLOYMENT.md](DEPLOYMENT.md) - подробная инструкция с объяснениями

### 3. Способы загрузки на сервер
→ [TRANSFER_GUIDE.md](TRANSFER_GUIDE.md) - SCP, WinSCP, Git, архив

---

## 🎮 Управление ботом

### Основные команды

```bash
# Запуск
systemctl start auto-poster-bot

# Остановка
systemctl stop auto-poster-bot

# Перезапуск
systemctl restart auto-poster-bot

# Статус
systemctl status auto-poster-bot

# Логи в реальном времени
journalctl -u auto-poster-bot -f

# Последние 50 строк логов
journalctl -u auto-poster-bot -n 50
```

### Мониторинг

```bash
# Запустить дашборд мониторинга
cd /root/app-inst/auto-poster-bot
./monitor.sh
```

Показывает:
- ✅ Статус сервиса
- 💻 Использование ресурсов (CPU, RAM, Swap, Disk)
- 🔧 Информация о процессе
- 📝 Последние логи
- ⚠️ Количество ошибок за последний час

### Обновление

```bash
cd /root/app-inst/auto-poster-bot
./update.sh
```

---

## 🛠️ Решение проблем

### Бот не запускается

```bash
# Смотрим логи
journalctl -u auto-poster-bot -n 100

# Проверяем .env
cat .env

# Тестируем вручную
cd /root/app-inst/auto-poster-bot
source venv/bin/activate
python main.py
```

### Нехватка памяти

```bash
# Проверяем swap
free -h

# Создаем swap 2GB если нужно
./deploy.sh  # пересоздаст swap автоматически
```

### Instagram не подключается

1. Проверьте логин/пароль в `.env`
2. Используйте `/reset` в боте
3. Удалите сессии: `rm -rf sessions/*`

### Подробнее

→ См. раздел "🐛 Решение проблем" в [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 🔐 Безопасность

### Обязательно:

1. ✅ Настройте файрвол (UFW)
2. ✅ Защитите .env файл: `chmod 600 .env`
3. ✅ Используйте сложные пароли
4. ✅ Регулярно обновляйте систему

### Опционально:

- 🔒 Настройте SSH ключи вместо паролей
- 🔒 Измените стандартный порт SSH (22)
- 🔒 Установите fail2ban

---

## 📊 Мониторинг ресурсов

### Проверка нагрузки

```bash
# Интерактивный монитор
htop

# Простой монитор
top

# Использование памяти
free -h

# Использование диска
df -h

# Процессы Python
ps aux | grep python
```

### Автоматический мониторинг

```bash
# Добавьте в cron ежечасную проверку
crontab -e

# Добавьте строку:
0 * * * * /root/app-inst/auto-poster-bot/monitor.sh >> /var/log/bot-monitor.log
```

---

## 📞 Полезные ссылки

### Документация
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [python-telegram-bot](https://docs.python-telegram-bot.org/)
- [Instagrapi](https://github.com/adw0rd/instagrapi)
- [VK API](https://dev.vk.com/)
- [Google AI](https://ai.google.dev/)

### Инструменты
- [@BotFather](https://t.me/BotFather) - создание ботов
- [@userinfobot](https://t.me/userinfobot) - узнать свой ID
- [WinSCP](https://winscp.net/) - загрузка файлов (Windows)

---

## ✅ Чек-лист установки

После установки проверьте:

- [ ] Swap настроен (`free -h` показывает > 0)
- [ ] .env файл создан и заполнен
- [ ] Зависимости установлены (`pip list`)
- [ ] Бот запущен (`systemctl status auto-poster-bot`)
- [ ] Автозапуск включен (`systemctl is-enabled auto-poster-bot`)
- [ ] Бот отвечает на `/start` в Telegram
- [ ] Instagram авторизован (`/status`)
- [ ] Логи без критических ошибок
- [ ] Тестовый пост опубликован успешно

---

## 🎯 Дальнейшие шаги

1. **Настройте VK** (опционально)
   - Получите токен доступа
   - Добавьте в `.env`
   - См. [VK_SETUP.md](VK_SETUP.md)

2. **Настройте AI помощника** (опционально)
   - Получите Google API ключ
   - Добавьте в `.env`
   - См. [AI_SETUP.md](AI_SETUP.md)

3. **Настройте резервное копирование**
   ```bash
   # Создайте backup скрипт
   nano /root/backup.sh
   ```

4. **Настройте мониторинг**
   ```bash
   # Запускайте monitor.sh регулярно
   crontab -e
   ```

---

## 💡 Советы по оптимизации

### Для 512 MB RAM:

1. **Не запускайте лишние сервисы**
   ```bash
   systemctl list-unit-files --state=enabled
   ```

2. **Настройте swappiness**
   ```bash
   echo "vm.swappiness=60" >> /etc/sysctl.conf
   sysctl -p
   ```

3. **Очищайте логи**
   ```bash
   journalctl --vacuum-time=7d
   ```

4. **Ограничьте размер uploads**
   - Автоматически очищается ботом
   - Проверяйте: `du -sh uploads/`

---

## 🆘 Поддержка

Если возникли проблемы:

1. Проверьте логи: `journalctl -u auto-poster-bot -n 100`
2. Запустите мониторинг: `./monitor.sh`
3. Проверьте конфигурацию: `cat .env`
4. Посмотрите [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 📄 Лицензия

Этот проект создан для автоматизации публикаций в социальных сетях.

---

**Готово к развертыванию!** 🚀

Начните с [TRANSFER_GUIDE.md](TRANSFER_GUIDE.md) для загрузки проекта на сервер.

