#!/bin/bash

# Auto-Poster Bot - Monitoring Script
# Скрипт для мониторинга состояния бота

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🤖 Auto-Poster Bot - Monitoring Dashboard${NC}"
echo "=========================================="
echo ""

# Bot service status
echo -e "${BLUE}📊 Service Status:${NC}"
if systemctl is-active --quiet auto-poster-bot; then
    echo -e "  Status: ${GREEN}✅ Running${NC}"
    UPTIME=$(systemctl show auto-poster-bot --property=ActiveEnterTimestamp --value)
    echo -e "  Started: $UPTIME"
else
    echo -e "  Status: ${RED}❌ Stopped${NC}"
fi

if systemctl is-enabled --quiet auto-poster-bot; then
    echo -e "  Autostart: ${GREEN}✅ Enabled${NC}"
else
    echo -e "  Autostart: ${YELLOW}⚠️ Disabled${NC}"
fi

echo ""

# System resources
echo -e "${BLUE}💻 System Resources:${NC}"
echo -e "  CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
MEM_TOTAL=$(free -h | grep Mem | awk '{print $2}')
MEM_USED=$(free -h | grep Mem | awk '{print $3}')
MEM_PERCENT=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
echo -e "  Memory: $MEM_USED / $MEM_TOTAL (${MEM_PERCENT}%)"

SWAP_TOTAL=$(free -h | grep Swap | awk '{print $2}')
SWAP_USED=$(free -h | grep Swap | awk '{print $3}')
if [ "$SWAP_TOTAL" != "0B" ]; then
    SWAP_PERCENT=$(free | grep Swap | awk '{if($2>0) printf("%.1f", $3/$2 * 100.0); else print "0"}')
    echo -e "  Swap: $SWAP_USED / $SWAP_TOTAL (${SWAP_PERCENT}%)"
else
    echo -e "  Swap: ${RED}Not configured${NC}"
fi

DISK_AVAIL=$(df -h / | tail -1 | awk '{print $4}')
DISK_PERCENT=$(df / | tail -1 | awk '{print $5}')
echo -e "  Disk: $DISK_AVAIL available ($DISK_PERCENT used)"

echo ""

# Bot process info
echo -e "${BLUE}🔧 Bot Process:${NC}"
BOT_PID=$(systemctl show auto-poster-bot --property=MainPID --value)
if [ "$BOT_PID" != "0" ] && [ -n "$BOT_PID" ]; then
    echo -e "  PID: $BOT_PID"
    BOT_MEM=$(ps -o rss= -p $BOT_PID 2>/dev/null | awk '{printf "%.1f MB", $1/1024}')
    if [ -n "$BOT_MEM" ]; then
        echo -e "  Memory Usage: $BOT_MEM"
    fi
    BOT_CPU=$(ps -o %cpu= -p $BOT_PID 2>/dev/null | awk '{printf "%.1f%%", $1}')
    if [ -n "$BOT_CPU" ]; then
        echo -e "  CPU Usage: $BOT_CPU"
    fi
else
    echo -e "  ${YELLOW}Process not running${NC}"
fi

echo ""

# Recent logs
echo -e "${BLUE}📝 Recent Logs (last 10 lines):${NC}"
journalctl -u auto-poster-bot -n 10 --no-pager | tail -10

echo ""

# Error count in last hour
echo -e "${BLUE}⚠️ Errors in last hour:${NC}"
ERROR_COUNT=$(journalctl -u auto-poster-bot --since "1 hour ago" | grep -i error | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "  ${GREEN}No errors found${NC}"
else
    echo -e "  ${RED}$ERROR_COUNT errors found${NC}"
    echo -e "  ${YELLOW}View errors: journalctl -u auto-poster-bot --since '1 hour ago' | grep -i error${NC}"
fi

echo ""
echo "=========================================="
echo -e "${BLUE}📌 Quick Commands:${NC}"
echo "  Restart: systemctl restart auto-poster-bot"
echo "  Logs:    journalctl -u auto-poster-bot -f"
echo "  Stop:    systemctl stop auto-poster-bot"
echo "=========================================="


