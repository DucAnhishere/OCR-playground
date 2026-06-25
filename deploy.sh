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

# 2. Download standalone VietOCR weights BEFORE starting Docker to avoid root permission issues
echo -e "${YELLOW}📥 Ensuring VietOCR weights are downloaded...${NC}"
mkdir -p ./weights/vietocr
if [ ! -f "./weights/vietocr/vgg_transformer.pth" ]; then
    echo -e "   ${YELLOW}Downloading VietOCR vgg_transformer.pth directly...${NC}"
    curl -s -L -o ./weights/vietocr/vgg_transformer.pth "https://vocr.vn/data/vietocr/vgg_transformer.pth"
fi

# 3. Spin up containers in detached mode
echo -e "\n${YELLOW}🐳 Starting all containers in background (detached)...${NC}"
docker compose up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error: Failed to start docker containers.${NC}"
    exit 1
fi

# 3. Wait and run health checks
echo -e "\n${YELLOW}⏳ Waiting 15 seconds for services to initialize...${NC}"
sleep 15

echo -e "${YELLOW}🔍 Running HTTP health check on Gateway...${NC}"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/status)

if [ "$HTTP_STATUS" -eq 200 ]; then
    echo -e "${GREEN}✅ Gateway backend is ONLINE (HTTP 200)${NC}"
    echo -e "${BLUE}Capabilities Status:${NC}"
    curl -s http://localhost:8000/api/status | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/api/status
else
    echo -e "${YELLOW}⚠️ Gateway status endpoint returned code: $HTTP_STATUS (it might still be starting up)${NC}"
fi

# 4. Pre-warm Models (Force download on first run)
echo -e "\n${BLUE}🔥 Pre-warming OCR Models (Downloading weights if needed)...${NC}"
echo -e "${YELLOW}This might take several minutes on the first run as models are downloaded into the weights directory.${NC}"


# 1x1 transparent dummy image
DUMMY_BASE64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

echo -e "   ${YELLOW}Warming up EasyOCR...${NC}"
docker compose exec -T orchestrator curl -s --max-time 600 --retry 5 --retry-connrefused --retry-delay 3 -X POST "http://ocr-pytorch:8002/api/ocr" -H "Content-Type: application/json" -d "{\"image\": \"$DUMMY_BASE64\", \"engine\": \"easyocr\", \"languages\": [\"en\", \"vi\"]}" > /dev/null

echo -e "   ${YELLOW}Warming up VietOCR...${NC}"
docker compose exec -T orchestrator curl -s --max-time 600 --retry 5 --retry-connrefused --retry-delay 3 -X POST "http://ocr-pytorch:8002/api/ocr" -H "Content-Type: application/json" -d "{\"image\": \"$DUMMY_BASE64\", \"engine\": \"vietocr\", \"languages\": [\"en\", \"vi\"]}" > /dev/null

echo -e "   ${YELLOW}Warming up PaddleOCR...${NC}"
docker compose exec -T orchestrator curl -s --max-time 600 --retry 5 --retry-connrefused --retry-delay 3 -X POST "http://ocr-paddle:8003/api/ocr" -H "Content-Type: application/json" -d "{\"image\": \"$DUMMY_BASE64\", \"engine\": \"paddleocr\", \"languages\": [\"en\", \"vi\"]}" > /dev/null

echo -e "   ${YELLOW}Warming up Paddle Structure...${NC}"
docker compose exec -T orchestrator curl -s --max-time 600 --retry 5 --retry-connrefused --retry-delay 3 -X POST "http://ocr-paddle:8003/api/ocr" -H "Content-Type: application/json" -d "{\"image\": \"$DUMMY_BASE64\", \"engine\": \"paddle_structure\", \"languages\": [\"en\", \"vi\"]}" > /dev/null


echo -e "${GREEN}✅ All models pre-warmed and ready!${NC}"

TUNNEL_RUNNING=false
PUBLIC_API_URL=""

echo -e "\n${BLUE}☁️  Initializing Cloudflare Quick Tunnel...${NC}"

CLOUDFLARED_BIN="cloudflared"

if ! command -v cloudflared &> /dev/null; then
    if [ -f "./cloudflared" ]; then
        CLOUDFLARED_BIN="./cloudflared"
    else
        echo -e "${YELLOW}⚠️  Warning: cloudflared CLI is not installed.${NC}"
        read -p "Do you want to automatically download cloudflared into this folder now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}📥 Downloading cloudflared...${NC}"
            if [[ "$OSTYPE" == "darwin"* ]]; then
                curl -s -L -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64
            else
                ARCH=$(uname -m)
                if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
                    curl -s -L -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
                else
                    curl -s -L -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
                fi
            fi
            chmod +x cloudflared
            CLOUDFLARED_BIN="./cloudflared"
        else
            CLOUDFLARED_BIN=""
        fi
    fi
fi

if [ -n "$CLOUDFLARED_BIN" ]; then
    # 1. Kill any existing cloudflared instances to avoid port conflicts and get a fresh URL
    pkill -f cloudflared &>/dev/null
    rm -f cloudflare_tunnel.log

    # 2. Start Quick Tunnel in the background
    echo -e "${YELLOW}🚀 Starting fresh tunnel in background...${NC}"
    nohup $CLOUDFLARED_BIN tunnel --url http://localhost:8000 > cloudflare_tunnel.log 2>&1 &

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
echo -e "   - ${BLUE}Frontend UI${NC}: http://localhost:5173"
echo -e "   - ${BLUE}Gateway API${NC}: http://localhost:8000"
if [ "$TUNNEL_RUNNING" = true ]; then
    echo -e "   - ${BLUE}Public API (Tunnel)${NC}: ${GREEN}${PUBLIC_API_URL}${NC}"
    echo -e "     👉 Copy link trên dán vào ô 'API Connection' ở trang Vercel!"
fi
echo -e "   - ${BLUE}Gateway Docs${NC}: http://localhost:8000/docs"
echo -e "\n🛠️  Useful commands:"
echo -e "   - View docker logs:   ${YELLOW}docker compose logs -f${NC}"
echo -e "   - View tunnel logs:   ${YELLOW}tail -f cloudflare_tunnel.log${NC}"
echo -e "   - Stop application:   ${YELLOW}docker compose down && pkill -f cloudflared${NC}"
echo -e "${GREEN}=======================================================${NC}"
