#!/bin/bash

# Color codes for pretty terminal logs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Get the script directory and cd to it
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}🛑 Stopping OCR Playground Microservices Stack${NC}"
echo -e "${BLUE}=======================================================${NC}"

# 1. Stop Docker containers
echo -e "${YELLOW}🐳 Stopping and removing docker containers...${NC}"
docker compose down

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker containers stopped successfully.${NC}"
else
    echo -e "${RED}❌ Error: Failed to stop docker containers.${NC}"
fi

# 2. Kill Cloudflare Tunnel
echo -e "\n${YELLOW}☁️  Stopping Cloudflare Tunnel...${NC}"
if pkill -f cloudflared &>/dev/null; then
    echo -e "${GREEN}✅ Cloudflare Tunnel stopped successfully.${NC}"
else
    echo -e "${YELLOW}⚠️  No active Cloudflare Tunnel found.${NC}"
fi

# 3. Clean up log files
if [ -f "cloudflare_tunnel.log" ]; then
    rm cloudflare_tunnel.log
    echo -e "${GREEN}✅ Cleaned up tunnel log file.${NC}"
fi

echo -e "\n${GREEN}=======================================================${NC}"
echo -e "${GREEN}🛑 All services have been successfully shut down!${NC}"
echo -e "${GREEN}=======================================================${NC}"
