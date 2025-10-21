# 🚀 Инструкция по развертыванию на VDS

## Требования сервера

**Минимальные:**
- Ubuntu 22.04 LTS
- 1 CPU
- 512 MB RAM (минимум)
- 10 GB HDD
- Python 3.8+

⚠️ **ВАЖНО:** При 512 MB RAM рекомендуется настроить swap-файл для стабильной работы.

## 📋 Пошаговая установка

### 1. Подключение к серверу

```bash
ssh root@ВАШ_IP_АДРЕС
```

### 2. Обновление системы

```bash
apt update && apt upgrade -y
```

### 3. Установка необходимых пакетов

```bash
# Python и зависимости
apt install -y python3 python3-pip python3-venv git

# Tesseract OCR (для распознавания артикулов на изображениях)
apt install -y tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng

# Библиотеки для обработки изображений
apt install -y libgl1-mesa-glx libglib2.0-0
```

### 4. Создание swap-файла (ОБЯЗАТЕЛЬНО для 512MB RAM!)

```bash
# Создаем swap-файл на 1GB
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Делаем swap постоянным
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Проверяем
free -h
```

### 5. Создание пользователя для бота (рекомендуется)

```bash
# Создаем пользователя
adduser botuser --disabled-password --gecos ""

# Переключаемся на пользователя
su - botuser
```

### 6. Клонирование проекта

```bash
# Клонируем проект (или загружаем через SFTP/SCP)
cd ~
mkdir -p app-inst
cd app-inst

# Если используете Git:
# git clone YOUR_REPO_URL auto-poster-bot
# cd auto-poster-bot

# Если загружаете вручную, скопируйте файлы через SCP:
# На вашем компьютере выполните:
# scp -r C:\Users\Димааас\Documents\app-inst\auto-poster-bot botuser@ВАШ_IP:/home/botuser/app-inst/
```

### 7. Настройка виртуального окружения

```bash
cd ~/app-inst/auto-poster-bot

# Создаем виртуальное окружение
python3 -m venv venv

# Активируем
source venv/bin/activate

# Обновляем pip
pip install --upgrade pip

# Устанавливаем зависимости
pip install -r requirements.txt
```

### 8. Настройка переменных окружения

```bash
# Копируем пример конфигурации
cp env.example .env

# Редактируем .env
nano .env
```

**Заполните следующие параметры:**

```env
TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН_БОТА
ADMIN_USER_ID=ВАШ_TELEGRAM_ID
TELEGRAM_GROUP_ID=@ваш_канал_или_группа
INSTAGRAM_USERNAME=ваш_инста_логин
INSTAGRAM_PASSWORD=ваш_инста_пароль
VK_ACCESS_TOKEN=токен_вк (опционально)
VK_GROUP_ID=id_группы_вк (опционально)
GOOGLE_API_KEY=ваш_google_ai_ключ (опционально)
LOG_LEVEL=INFO
```

💡 **Как получить TELEGRAM_BOT_TOKEN:**
1. Напишите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям

💡 **Как узнать ADMIN_USER_ID:**
1. Напишите @userinfobot
2. Скопируйте ваш ID

### 9. Создание необходимых директорий

```bash
mkdir -p sessions uploads
chmod 755 sessions uploads
```

### 10. Тестовый запуск

```bash
# Активируем виртуальное окружение если не активировано
source venv/bin/activate

# Запускаем бота
python main.py
```

Если бот запустился без ошибок, нажмите `Ctrl+C` и переходите к следующему шагу.

### 11. Настройка автозапуска через systemd

Выходим из пользователя botuser (если работали под ним):

```bash
exit  # Возвращаемся к root
```

Создаем systemd service:

```bash
nano /etc/systemd/system/auto-poster-bot.service
```

Вставьте содержимое (замените `botuser` если используете другого пользователя):

```ini
[Unit]
Description=Auto-Poster Telegram Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/app-inst/auto-poster-bot
Environment="PATH=/home/botuser/app-inst/auto-poster-bot/venv/bin"
ExecStart=/home/botuser/app-inst/auto-poster-bot/venv/bin/python main.py
Restart=always
RestartSec=10

# Оптимизация для 512MB RAM
MemoryLimit=400M
CPUQuota=80%

[Install]
WantedBy=multi-user.target
```

**Если работаете под root**, используйте эту версию:

```ini
[Unit]
Description=Auto-Poster Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/app-inst/auto-poster-bot
Environment="PATH=/root/app-inst/auto-poster-bot/venv/bin"
ExecStart=/root/app-inst/auto-poster-bot/venv/bin/python main.py
Restart=always
RestartSec=10

# Оптимизация для 512MB RAM
MemoryLimit=400M
CPUQuota=80%

[Install]
WantedBy=multi-user.target
```

Сохраните файл (`Ctrl+X`, затем `Y`, затем `Enter`).

### 12. Запуск и включение автозапуска

```bash
# Перезагружаем systemd
systemctl daemon-reload

# Включаем автозапуск
systemctl enable auto-poster-bot

# Запускаем бота
systemctl start auto-poster-bot

# Проверяем статус
systemctl status auto-poster-bot
```

### 13. Проверка логов

```bash
# Просмотр логов в реальном времени
journalctl -u auto-poster-bot -f

# Последние 50 строк
journalctl -u auto-poster-bot -n 50

# Логи за сегодня
journalctl -u auto-poster-bot --since today
```

## 🔧 Управление ботом

### Основные команды

```bash
# Запустить бота
systemctl start auto-poster-bot

# Остановить бота
systemctl stop auto-poster-bot

# Перезапустить бота
systemctl restart auto-poster-bot

# Статус бота
systemctl status auto-poster-bot

# Просмотр логов
journalctl -u auto-poster-bot -f
```

### Обновление бота

```bash
# Останавливаем бота
systemctl stop auto-poster-bot

# Переходим в директорию проекта
cd /home/botuser/app-inst/auto-poster-bot  # или /root/app-inst/auto-poster-bot

# Обновляем код (если используете Git)
# git pull

# Или загружаем новые файлы через SCP

# Активируем виртуальное окружение
source venv/bin/activate

# Обновляем зависимости (если изменились)
pip install -r requirements.txt --upgrade

# Запускаем бота
systemctl start auto-poster-bot

# Проверяем статус
systemctl status auto-poster-bot
```

## 📊 Мониторинг ресурсов

### Проверка использования памяти и CPU

```bash
# Общая информация о системе
htop

# Или используйте top
top

# Проверка памяти
free -h

# Проверка диска
df -h

# Использование памяти процессом бота
ps aux | grep python
```

### Оптимизация для 512MB RAM

Если бот потребляет слишком много памяти:

1. **Уменьшите лимит памяти в systemd:**
   ```bash
   nano /etc/systemd/system/auto-poster-bot.service
   # Измените MemoryLimit=400M на MemoryLimit=350M
   systemctl daemon-reload
   systemctl restart auto-poster-bot
   ```

2. **Отключите неиспользуемые функции:**
   - Если не используете VK, не указывайте токены VK в .env
   - Если не нужна AI помощь, не указывайте GOOGLE_API_KEY

3. **Настройте swap swappiness:**
   ```bash
   echo "vm.swappiness=60" >> /etc/sysctl.conf
   sysctl -p
   ```

## 🔒 Безопасность

### 1. Настройка файрвола (UFW)

```bash
# Устанавливаем UFW
apt install -y ufw

# Разрешаем SSH
ufw allow 22/tcp

# Включаем файрвол
ufw enable

# Проверяем статус
ufw status
```

### 2. Защита .env файла

```bash
# Только владелец может читать
chmod 600 /home/botuser/app-inst/auto-poster-bot/.env
```

### 3. Регулярное обновление системы

```bash
# Добавьте в cron автоматическое обновление
crontab -e

# Добавьте строку (обновление раз в неделю в воскресенье в 3:00)
0 3 * * 0 apt update && apt upgrade -y
```

## 📝 Загрузка файлов на сервер через SCP

### С Windows (PowerShell):

```powershell
# Загрузка всего проекта
scp -r "C:\Users\Димааас\Documents\app-inst\auto-poster-bot" root@ВАШ_IP:/root/app-inst/

# Или конкретный файл
scp "C:\Users\Димааас\Documents\app-inst\auto-poster-bot\.env" root@ВАШ_IP:/root/app-inst/auto-poster-bot/
```

### Альтернатива: WinSCP (GUI)

1. Скачайте [WinSCP](https://winscp.net/eng/download.php)
2. Подключитесь к серверу (SFTP)
3. Перетащите файлы мышкой

## 🐛 Решение проблем

### Бот не запускается

```bash
# Проверьте логи
journalctl -u auto-poster-bot -n 100 --no-pager

# Проверьте синтаксис Python
cd /home/botuser/app-inst/auto-poster-bot
source venv/bin/activate
python -m py_compile main.py

# Проверьте .env файл
cat .env

# Проверьте права доступа
ls -la
```

### Ошибка "Out of memory"

```bash
# Проверьте swap
free -h

# Увеличьте swap до 2GB
swapoff /swapfile
rm /swapfile
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
```

### Instagram не подключается

1. Проверьте логин/пароль в .env
2. Попробуйте сбросить сессию:
   ```bash
   rm -rf sessions/*
   systemctl restart auto-poster-bot
   ```
3. Используйте команду `/reset` в боте

### Tesseract не распознает текст

```bash
# Проверьте установку языков
dpkg -l | grep tesseract

# Переустановите языковые пакеты
apt install --reinstall tesseract-ocr-rus tesseract-ocr-eng
```

## 📞 Полезные ссылки

- [Документация python-telegram-bot](https://docs.python-telegram-bot.org/)
- [Instagrapi документация](https://github.com/adw0rd/instagrapi)
- [VK API](https://dev.vk.com/)
- [Google AI Studio](https://ai.google.dev/)

## ✅ Чек-лист после установки

- [ ] Бот запущен (`systemctl status auto-poster-bot`)
- [ ] Автозапуск включен (`systemctl is-enabled auto-poster-bot`)
- [ ] Swap настроен (`free -h`)
- [ ] Файрвол настроен (`ufw status`)
- [ ] .env защищен (`ls -la .env`)
- [ ] Бот отвечает в Telegram (`/start`)
- [ ] Instagram подключен (`/status`)
- [ ] Логи без ошибок (`journalctl -u auto-poster-bot -n 50`)

---

🎉 **Готово!** Ваш бот работает на VDS!

Для проверки напишите боту `/start` в Telegram.

