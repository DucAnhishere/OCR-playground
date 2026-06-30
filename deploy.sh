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
echo -e "${BLUE}🚀 Deploying OCR Playground Microservices Stack${NC}"
echo -e "${BLUE}=======================================================${NC}"

# 1. Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running. Please start Docker Desktop first.${NC}"
    exit 1
fi

# 2. Spin up containers in detached mode
echo -e "${CYAN}🔍 Checking for NVIDIA GPU...${NC}"
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✅ NVIDIA GPU detected! Enabling GPU support...${NC}"
    docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
else
    echo -e "${YELLOW}⚠️ No NVIDIA GPU found. Falling back to CPU...${NC}"
    docker compose up -d
fi

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error: Failed to start docker containers.${NC}"
    exit 1
fi

# 3. Wait and run health checks
echo -e "\n${YELLOW}⏳ Waiting 5 seconds for services to initialize...${NC}"
sleep 5

echo -e "${YELLOW}🔍 Running HTTP health check on Gateway...${NC}"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/status)

if [ "$HTTP_STATUS" -eq 200 ]; then
    echo -e "${GREEN}✅ Gateway backend is ONLINE (HTTP 200)${NC}"
    echo -e "${BLUE}Capabilities Status:${NC}"
    curl -s http://localhost:8000/api/status | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/api/status
else
    echo -e "${YELLOW}⚠️ Gateway status endpoint returned code: $HTTP_STATUS (it might still be starting up)${NC}"
fi

# 4. Initialize Cloudflare Quick Tunnel (Option 2 - Free & No Account Required)
TUNNEL_RUNNING=false
PUBLIC_API_URL=""

echo -e "\n${BLUE}☁️  Initializing Cloudflare Quick Tunnel...${NC}"

if ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}⚠️  Warning: cloudflared CLI is not installed. Run 'brew install cloudflared' to enable tunneling.${NC}"
else
    # 1. Kill any existing cloudflared instances to avoid port conflicts and get a fresh URL
    pkill -f cloudflared &>/dev/null
    rm -f cloudflare_tunnel.log

    # 2. Start Quick Tunnel in the background
    echo -e "${YELLOW}🚀 Starting fresh tunnel in background...${NC}"
    nohup cloudflared tunnel --url http://localhost:8000 > cloudflare_tunnel.log 2>&1 &

    # 3. Poll the log file to extract the dynamically generated URL
    echo -e "${YELLOW}⏳ Waiting for Cloudflare to assign your public URL...${NC}"
    for i in {1..10}; do
        sleep 1
        if [ -f cloudflare_tunnel.log ]; then
            # Extract the URL from the log file
            TEMP_URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.trycloudflare\.com" cloudflare_tunnel.log | head -n 1)
            if [ ! -z "$TEMP_URL" ]; then
                PUBLIC_API_URL="${TEMP_URL}/api"
                TUNNEL_RUNNING=true
                break
            fi
        fi
    done

    if [ "$TUNNEL_RUNNING" = true ]; then
        echo -e "${GREEN}✅ Cloudflare Tunnel is active!${NC}"
        echo -e "   - Public API URL:  ${GREEN}${PUBLIC_API_URL}${NC}"
    else
        echo -e "${RED}❌ Error: Failed to retrieve public URL. Check cloudflare_tunnel.log for details.${NC}"
    fi
fi

echo -e "\n${GREEN}=======================================================${NC}"
echo -e "${GREEN}🎉 Deployment finished successfully!${NC}"
echo -e "   - ${BLUE}Frontend UI${NC}: http://localhost:8000"
echo -e "   - ${BLUE}Gateway API${NC}: http://localhost:8000/api"
if [ "$TUNNEL_RUNNING" = true ]; then
    echo -e "   - ${BLUE}Public API (Tunnel)${NC}: ${GREEN}${PUBLIC_API_URL}${NC}"
    echo -e "     👉 Copy link trên dán vào ô 'API Connection' ở trang Vercel!"
fi
echo -e "   - ${BLUE}Gateway Docs${NC}: http://localhost:8000/docs"
echo -e "   - ${BLUE}Gateway Health${NC}: http://localhost:8000/api/health/ready"
echo -e "\n🛠️  Useful commands:"
echo -e "   - View docker logs:   ${YELLOW}docker compose logs -f${NC}"
echo -e "   - View tunnel logs:   ${YELLOW}tail -f cloudflare_tunnel.log${NC}"
echo -e "   - Stop application:   ${YELLOW}docker compose down && pkill -f cloudflared${NC}"
echo -e "${GREEN}=======================================================${NC}"
