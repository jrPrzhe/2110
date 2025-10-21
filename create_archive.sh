#!/bin/bash

# Script to create a deployment archive
# Создает архив проекта для загрузки на сервер

echo "📦 Creating deployment archive..."

# Archive name
ARCHIVE_NAME="auto-poster-bot-$(date +%Y%m%d-%H%M%S).tar.gz"

# Files to exclude
EXCLUDE_FILES=(
    "venv"
    "__pycache__"
    "*.pyc"
    "sessions/*"
    "uploads/*"
    ".env"
    "*.log"
    ".git"
    ".vscode"
    ".idea"
    "*.tar.gz"
)

# Build exclude parameters
EXCLUDE_PARAMS=""
for item in "${EXCLUDE_FILES[@]}"; do
    EXCLUDE_PARAMS="$EXCLUDE_PARAMS --exclude=$item"
done

# Create archive
tar -czf "$ARCHIVE_NAME" $EXCLUDE_PARAMS \
    *.py \
    *.txt \
    *.md \
    *.sh \
    *.service \
    .gitignore \
    env.example \
    handlers/ \
    services/ \
    utils/ \
    2>/dev/null

if [ -f "$ARCHIVE_NAME" ]; then
    SIZE=$(du -h "$ARCHIVE_NAME" | cut -f1)
    echo "✅ Archive created: $ARCHIVE_NAME ($SIZE)"
    echo ""
    echo "Upload to server using:"
    echo "  scp $ARCHIVE_NAME root@YOUR_SERVER_IP:/root/"
    echo ""
    echo "On server, extract using:"
    echo "  tar -xzf $ARCHIVE_NAME"
else
    echo "❌ Failed to create archive"
    exit 1
fi

