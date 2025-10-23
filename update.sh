#!/bin/bash

# Auto-Poster Bot - Update Script
# Скрипт для обновления бота

set -e

echo "🔄 Auto-Poster Bot - Update Script"
echo "===================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    USER_HOME="/root"
else
    USER_HOME="$HOME"
fi

PROJECT_DIR="$USER_HOME/app-inst/auto-poster-bot"

# Check if project exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}Error: Project directory not found at $PROJECT_DIR${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

# Stop the bot
echo -e "${YELLOW}Stopping the bot...${NC}"
sudo systemctl stop auto-poster-bot

# Backup .env
if [ -f ".env" ]; then
    echo -e "${GREEN}Backing up .env file...${NC}"
    cp .env .env.backup
fi

# Update code (if using Git)
if [ -d ".git" ]; then
    echo -e "${GREEN}Pulling latest changes from Git...${NC}"
    git pull
else
    echo -e "${YELLOW}Not a Git repository. Please update files manually.${NC}"
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Update dependencies
echo -e "${GREEN}Updating dependencies...${NC}"
pip install -r requirements.txt --upgrade

# Restore .env if it was modified
if [ -f ".env.backup" ]; then
    if [ -f ".env" ]; then
        echo -e "${YELLOW}Comparing .env files...${NC}"
        if ! cmp -s .env .env.backup; then
            echo -e "${YELLOW}Warning: .env has changed. Check if new variables were added.${NC}"
            echo -e "${YELLOW}Backup saved as .env.backup${NC}"
        else
            rm .env.backup
        fi
    else
        mv .env.backup .env
    fi
fi

# Restart the bot
echo -e "${GREEN}Starting the bot...${NC}"
sudo systemctl start auto-poster-bot

# Wait a bit for the bot to start
sleep 3

# Check status
echo -e "${GREEN}Checking bot status...${NC}"
sudo systemctl status auto-poster-bot --no-pager

echo ""
echo -e "${GREEN}======================================"
echo "✅ Update completed!"
echo "======================================${NC}"
echo ""
echo "To view logs:"
echo "sudo journalctl -u auto-poster-bot -f"
echo ""


