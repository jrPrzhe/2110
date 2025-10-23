# 🔗 Настройка Git и загрузка на GitHub

## Быстрая загрузка в репозиторий

### Репозиторий
https://github.com/jrPrzhe/2110.git

---

## ⚡ Автоматическая загрузка (Windows PowerShell)

```powershell
cd C:\Users\Димааас\Documents\app-inst\auto-poster-bot

# Инициализация Git
git init

# Добавление файлов
git add .

# Первый коммит
git commit -m "Initial commit: Auto-Poster Bot"

# Подключение удаленного репозитория
git remote add origin https://github.com/jrPrzhe/2110.git

# Загрузка на GitHub
git branch -M main
git push -u origin main
```

---

## 📝 Пошаговая инструкция

### 1. Откройте PowerShell в директории проекта

```powershell
cd C:\Users\Димааас\Documents\app-inst\auto-poster-bot
```

### 2. Настройте Git (если еще не настроен)

```powershell
git config --global user.name "Ваше Имя"
git config --global user.email "ваш@email.com"
```

### 3. Инициализируйте репозиторий

```powershell
git init
```

### 4. Проверьте файлы для добавления

```powershell
# Посмотрите, какие файлы будут добавлены
git status
```

Должны быть включены:
- ✅ Все `.py` файлы
- ✅ `requirements.txt`
- ✅ `.md` файлы (документация)
- ✅ `.sh` скрипты
- ✅ `env.example`
- ✅ `.gitignore`

Должны быть исключены (автоматически через `.gitignore`):
- ❌ `.env` (содержит пароли!)
- ❌ `venv/` (виртуальное окружение)
- ❌ `__pycache__/` (кэш Python)
- ❌ `sessions/` (сессии Instagram)
- ❌ `uploads/` (временные файлы)

### 5. Добавьте файлы в Git

```powershell
git add .
```

### 6. Создайте первый коммит

```powershell
git commit -m "Initial commit: Auto-Poster Telegram Bot

- Instagram, Telegram, VK posting
- AI caption generation (Google Gemini)
- Article recognition with OCR
- Reels support
- Multi-image posts
- Deployment scripts for VDS"
```

### 7. Подключите GitHub репозиторий

```powershell
git remote add origin https://github.com/jrPrzhe/2110.git
```

### 8. Переименуйте ветку в main (если нужно)

```powershell
git branch -M main
```

### 9. Загрузите код на GitHub

```powershell
git push -u origin main
```

При первой загрузке Git может запросить авторизацию GitHub.

---

## 🔐 Авторизация на GitHub

### Вариант 1: Personal Access Token (рекомендуется)

1. Перейдите: https://github.com/settings/tokens
2. Нажмите **Generate new token** → **Generate new token (classic)**
3. Выберите разрешения:
   - ✅ `repo` (полный доступ к репозиториям)
4. Нажмите **Generate token**
5. **Скопируйте токен** (он больше не появится!)

При запросе пароля используйте токен вместо пароля:
- Username: `jrPrzhe`
- Password: `ваш_токен`

### Вариант 2: GitHub CLI

```powershell
# Установите GitHub CLI: https://cli.github.com/
winget install GitHub.cli

# Авторизуйтесь
gh auth login

# Загрузите репозиторий
gh repo clone https://github.com/jrPrzhe/2110.git
```

---

## 📤 Обновление репозитория

После изменений в коде:

```powershell
cd C:\Users\Димааас\Documents\app-inst\auto-poster-bot

# Посмотреть изменения
git status

# Добавить все изменения
git add .

# Создать коммит
git commit -m "Описание изменений"

# Загрузить на GitHub
git push
```

---

## 🌿 Работа с ветками

### Создание новой ветки для разработки

```powershell
# Создать и переключиться на новую ветку
git checkout -b develop

# Внести изменения, затем:
git add .
git commit -m "New feature"
git push -u origin develop

# Вернуться на main
git checkout main

# Слить изменения
git merge develop
git push
```

---

## 📋 Полезные команды Git

```powershell
# Посмотреть статус
git status

# Посмотреть историю коммитов
git log --oneline

# Посмотреть изменения
git diff

# Отменить изменения в файле
git checkout -- файл.py

# Удалить файл из Git
git rm файл.py

# Переименовать файл
git mv старое_имя новое_имя

# Посмотреть удаленные репозитории
git remote -v

# Получить изменения с GitHub
git pull

# Клонировать репозиторий
git clone https://github.com/jrPrzhe/2110.git
```

---

## ⚠️ Важно!

### Никогда не добавляйте в Git:

- ❌ `.env` файлы с паролями
- ❌ Приватные ключи и токены
- ❌ Файлы сессий
- ❌ Личные данные

### Если случайно добавили .env:

```powershell
# Удалить из Git (но оставить локально)
git rm --cached .env

# Добавить в .gitignore
echo ".env" >> .gitignore

# Закоммитить
git add .gitignore
git commit -m "Remove .env from Git"
git push

# ВАЖНО: Поменяйте все пароли, которые были в .env!
```

---

## 🎯 Структура проекта на GitHub

После загрузки ваш репозиторий будет содержать:

```
https://github.com/jrPrzhe/2110
├── README.md                 # Главная документация
├── DEPLOYMENT.md             # Инструкция по развертыванию
├── QUICK_DEPLOY.md           # Быстрый старт
├── main.py                   # Основной файл
├── config.py                 # Конфигурация
├── requirements.txt          # Зависимости
├── handlers/                 # Обработчики
├── services/                 # Сервисы
├── utils/                    # Утилиты
└── deploy.sh                 # Скрипт установки
```

---

## 📝 Рекомендации

### 1. Создайте хороший README.md

Должен содержать:
- Описание проекта
- Скриншоты (опционально)
- Требования
- Инструкция по установке
- Примеры использования
- Лицензия

### 2. Используйте осмысленные коммиты

**Хорошо:**
```
git commit -m "Add VK posting support"
git commit -m "Fix Instagram login issue"
git commit -m "Update deployment documentation"
```

**Плохо:**
```
git commit -m "fix"
git commit -m "update"
git commit -m "asdf"
```

### 3. Создайте релизы

После стабильной версии:
1. Перейдите: https://github.com/jrPrzhe/2110/releases
2. Нажмите **Create a new release**
3. Укажите версию: `v1.0.0`
4. Опишите изменения

---

## 🔄 Синхронизация с VDS

После загрузки на GitHub, на VDS можно использовать:

```bash
# На VDS
cd /root/app-inst

# Клонировать из GitHub
git clone https://github.com/jrPrzhe/2110.git auto-poster-bot

# Или обновить существующий
cd auto-poster-bot
git pull
```

---

## ✅ Чек-лист загрузки

- [ ] Git установлен и настроен
- [ ] `.gitignore` создан
- [ ] `.env` исключен из Git
- [ ] Файлы добавлены (`git add .`)
- [ ] Коммит создан (`git commit`)
- [ ] Репозиторий подключен (`git remote add`)
- [ ] Код загружен (`git push`)
- [ ] Репозиторий виден на GitHub
- [ ] README.md оформлен
- [ ] Конфиденциальные данные не попали в Git

---

**Готово!** 🎉

Ваш проект теперь на GitHub: https://github.com/jrPrzhe/2110


