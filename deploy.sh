#!/bin/bash

# Auto-Poster Bot - Deployment Script
# Скрипт для быстрого развертывания на Ubuntu 22.04

set -e

echo "🚀 Auto-Poster Bot - Deployment Script"
echo "======================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${YELLOW}Warning: Running as root${NC}"
    USER_HOME="/root"
    SERVICE_USER="root"
else
    USER_HOME="$HOME"
    SERVICE_USER="$USER"
fi

PROJECT_DIR="$USER_HOME/app-inst/auto-poster-bot"

echo -e "${GREEN}Installing system dependencies...${NC}"
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng libgl1-mesa-glx libglib2.0-0

# Check swap
SWAP_SIZE=$(free -m | grep Swap | awk '{print $2}')
if [ "$SWAP_SIZE" -lt 512 ]; then
    echo -e "${YELLOW}Warning: Swap is less than 512MB. Creating 1GB swap file...${NC}"
    
    if [ -f /swapfile ]; then
        echo "Swap file already exists. Skipping..."
    else
        sudo fallocate -l 1G /swapfile
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
        sudo swapon /swapfile
        
        # Make it permanent
        if ! grep -q '/swapfile' /etc/fstab; then
            echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
        fi
        
        echo -e "${GREEN}Swap file created successfully${NC}"
    fi
fi

# Create project directory
echo -e "${GREEN}Creating project directory...${NC}"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}Installing Python dependencies...${NC}"
    pip install -r requirements.txt
else
    echo -e "${RED}Error: requirements.txt not found${NC}"
    exit 1
fi

# Create necessary directories
echo -e "${GREEN}Creating necessary directories...${NC}"
mkdir -p sessions uploads
chmod 755 sessions uploads

# Check if .env exists
if [ ! -f ".env" ]; then
    if [ -f "env.example" ]; then
        echo -e "${YELLOW}Warning: .env file not found. Copying from env.example...${NC}"
        cp env.example .env
        chmod 600 .env
        echo -e "${RED}Please edit .env file and fill in your credentials${NC}"
    else
        echo -e "${RED}Error: Neither .env nor env.example found${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}.env file found${NC}"
    chmod 600 .env
fi

# Create systemd service
echo -e "${GREEN}Creating systemd service...${NC}"

sudo tee /etc/systemd/system/auto-poster-bot.service > /dev/null <<EOF
[Unit]
Description=Auto-Poster Telegram Bot
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python main.py
Restart=always
RestartSec=10

# Optimization for limited RAM
MemoryLimit=400M
CPUQuota=80%

# Security
NoNewPrivileges=true
PrivateTmp=true

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=auto-poster-bot

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo -e "${GREEN}Reloading systemd...${NC}"
sudo systemctl daemon-reload

# Enable service
echo -e "${GREEN}Enabling auto-start...${NC}"
sudo systemctl enable auto-poster-bot

echo ""
echo -e "${GREEN}======================================"
echo "✅ Deployment completed successfully!"
echo "======================================${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env file: nano $PROJECT_DIR/.env"
echo "2. Start the bot: sudo systemctl start auto-poster-bot"
echo "3. Check status: sudo systemctl status auto-poster-bot"
echo "4. View logs: sudo journalctl -u auto-poster-bot -f"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "- Make sure to fill in all required variables in .env"
echo "- Check logs after starting the bot"
echo "- Test the bot by sending /start to your Telegram bot"
echo ""
echo "System info:"
echo "- RAM: $(free -h | grep Mem | awk '{print $2}')"
echo "- Swap: $(free -h | grep Swap | awk '{print $2}')"
echo "- Disk: $(df -h / | tail -1 | awk '{print $4}') available"
echo ""


