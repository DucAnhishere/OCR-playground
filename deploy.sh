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
echo -e "${YELLOW}🐳 Starting all containers in background (detached)...${NC}"
docker compose up -d

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

echo -e "\n${GREEN}=======================================================${NC}"
echo -e "${GREEN}🎉 Deployment finished successfully!${NC}"
echo -e "   - ${BLUE}Frontend UI${NC}: http://localhost:5173"
echo -e "   - ${BLUE}Gateway API${NC}: http://localhost:8000"
echo -e "   - ${BLUE}Gateway Docs${NC}: http://localhost:8000/docs"
echo -e "\n🛠️  Useful commands:"
echo -e "   - View logs:          ${YELLOW}docker compose logs -f${NC}"
echo -e "   - Stop application:   ${YELLOW}docker compose down${NC}"
echo -e "${GREEN}=======================================================${NC}"
