# 📤 Руководство по переносу проекта на VDS

## Способ 1: SCP (рекомендуется для Windows)

### Из Windows PowerShell:

```powershell
# Перейдите в директорию с проектом
cd C:\Users\Димааас\Documents\app-inst

# Загрузите весь проект на сервер
scp -r auto-poster-bot root@ВАШ_IP:/root/app-inst/
```

Если появится предупреждение о подключении, введите `yes`.

### Если нужно загрузить только изменения:

```powershell
# Загрузить только код (без venv и временных файлов)
scp auto-poster-bot/*.py root@ВАШ_IP:/root/app-inst/auto-poster-bot/
scp auto-poster-bot/*.txt root@ВАШ_IP:/root/app-inst/auto-poster-bot/
scp auto-poster-bot/*.sh root@ВАШ_IP:/root/app-inst/auto-poster-bot/
scp auto-poster-bot/.env root@ВАШ_IP:/root/app-inst/auto-poster-bot/

# Загрузить директории
scp -r auto-poster-bot/handlers root@ВАШ_IP:/root/app-inst/auto-poster-bot/
scp -r auto-poster-bot/services root@ВАШ_IP:/root/app-inst/auto-poster-bot/
scp -r auto-poster-bot/utils root@ВАШ_IP:/root/app-inst/auto-poster-bot/
```

---

## Способ 2: WinSCP (GUI для Windows)

### Установка:

1. Скачайте [WinSCP](https://winscp.net/eng/download.php)
2. Установите программу

### Подключение:

1. Запустите WinSCP
2. Создайте новое подключение:
   - **Протокол:** SFTP
   - **Хост:** IP вашего VDS
   - **Порт:** 22
   - **Имя пользователя:** root
   - **Пароль:** ваш пароль от VDS
3. Нажмите **Войти**

### Загрузка файлов:

1. Слева (локальный компьютер): откройте `C:\Users\Димааас\Documents\app-inst\`
2. Справа (сервер): перейдите в `/root/app-inst/`
3. Перетащите папку `auto-poster-bot` слева направо

**Важно:** Не копируйте папку `venv` - она будет создана на сервере.

---

## Способ 3: Git (если используете)

### На локальном компьютере:

```bash
cd C:\Users\Димааас\Documents\app-inst\auto-poster-bot

# Инициализируйте Git (если еще не сделали)
git init
git add .
git commit -m "Initial commit"

# Добавьте удаленный репозиторий (GitHub/GitLab)
git remote add origin https://github.com/ВАШ_USERNAME/auto-poster-bot.git
git push -u origin master
```

### На сервере:

```bash
cd /root/app-inst
git clone https://github.com/ВАШ_USERNAME/auto-poster-bot.git
cd auto-poster-bot

# Создайте .env файл (не храните его в Git!)
nano .env
# Вставьте конфигурацию
```

---

## Способ 4: Создание архива

### На Windows (Git Bash или WSL):

```bash
cd C:\Users\Димааас\Documents\app-inst\auto-poster-bot

# Создайте архив (исключая ненужные файлы)
tar -czf auto-poster-bot.tar.gz \
    --exclude=venv \
    --exclude=__pycache__ \
    --exclude=sessions \
    --exclude=uploads \
    --exclude=.env \
    *.py *.txt *.md *.sh .gitignore env.example \
    handlers/ services/ utils/

# Загрузите архив на сервер
scp auto-poster-bot.tar.gz root@ВАШ_IP:/root/
```

### На сервере:

```bash
cd /root
mkdir -p app-inst
cd app-inst

# Распакуйте архив
tar -xzf ../auto-poster-bot.tar.gz
mv auto-poster-bot-* auto-poster-bot  # если создалась папка с датой

cd auto-poster-bot
```

---

## Способ 5: Rsync (для опытных)

```bash
# С Windows через WSL или Git Bash
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude 'sessions' --exclude '.env' \
    C:/Users/Димааас/Documents/app-inst/auto-poster-bot/ \
    root@ВАШ_IP:/root/app-inst/auto-poster-bot/
```

---

## После загрузки на сервер

```bash
# Подключитесь к серверу
ssh root@ВАШ_IP

# Перейдите в директорию проекта
cd /root/app-inst/auto-poster-bot

# Дайте права на выполнение скриптам
chmod +x *.sh

# Запустите автоматическую установку
./deploy.sh

# Или выполните вручную по инструкции DEPLOYMENT.md
```

---

## Проверка загрузки

### На сервере выполните:

```bash
cd /root/app-inst/auto-poster-bot
ls -la
```

Должны быть следующие файлы:
- `main.py`
- `config.py`
- `requirements.txt`
- `env.example`
- `deploy.sh`
- `update.sh`
- `monitor.sh`
- папки: `handlers/`, `services/`, `utils/`

---

## Частые ошибки

### 1. Permission denied (publickey)

```bash
# На Windows используйте пароль вместо ключа
# Или добавьте -o PreferredAuthentications=password
scp -o PreferredAuthentications=password -r auto-poster-bot root@ВАШ_IP:/root/app-inst/
```

### 2. Connection timeout

Проверьте:
- Правильность IP адреса
- Доступность сервера: `ping ВАШ_IP`
- Открыт ли порт 22 (SSH)

### 3. Directory not found

```bash
# На сервере создайте директорию
ssh root@ВАШ_IP
mkdir -p /root/app-inst
```

---

## Рекомендации

1. ✅ **Используйте SCP или WinSCP** - самый простой способ для Windows
2. ✅ **Не загружайте `venv`** - будет создана на сервере
3. ✅ **Не загружайте `.env`** - создайте на сервере с актуальными данными
4. ✅ **Проверьте размер файлов** - проект должен быть ~1-5 MB без venv
5. ⚠️ **Сохраните `.env` в безопасном месте** - он содержит пароли

---

## Готово!

После загрузки переходите к [DEPLOYMENT.md](DEPLOYMENT.md) или [QUICK_DEPLOY.md](QUICK_DEPLOY.md)

