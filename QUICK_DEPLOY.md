# ⚡ Быстрое развертывание

Для опытных пользователей - краткая инструкция.

## Одной командой

### 1. Загрузите проект на сервер

```bash
# С вашего компьютера (Windows PowerShell)
scp -r "C:\Users\Димааас\Documents\app-inst\auto-poster-bot" root@ВАШ_IP:/root/app-inst/
```

### 2. На сервере выполните

```bash
cd /root/app-inst/auto-poster-bot
chmod +x deploy.sh
./deploy.sh
```

### 3. Настройте .env

```bash
nano .env
# Заполните все переменные
```

### 4. Запустите

```bash
systemctl start auto-poster-bot
journalctl -u auto-poster-bot -f
```

## Готово! 🎉

Проверьте бота командой `/start` в Telegram.

---

## Команды управления

```bash
# Статус
systemctl status auto-poster-bot

# Перезапуск
systemctl restart auto-poster-bot

# Логи
journalctl -u auto-poster-bot -f

# Остановка
systemctl stop auto-poster-bot
```

## Обновление

```bash
cd /root/app-inst/auto-poster-bot
chmod +x update.sh
./update.sh
```

---

📖 Подробная инструкция: [DEPLOYMENT.md](DEPLOYMENT.md)


