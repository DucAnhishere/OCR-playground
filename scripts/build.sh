#!/bin/bash

# Color codes for pretty terminal logs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Get the script directory, then cd to project root (one level up from scripts/)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/.."

echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}⚙️  Building OCR Playground Microservices Architecture${NC}"
echo -e "${BLUE}=======================================================${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running. Please start Docker Desktop first.${NC}"
    exit 1
fi



echo -e "${YELLOW}🐳 Starting build via Docker Compose...${NC}\n"

# Run docker compose build (context is project root, compose file in docker/)
docker compose --project-directory . -f docker/docker-compose.yml build

if [ $? -eq 0 ]; then
    echo -e "\n${YELLOW}🧹 Cleaning up dangling Docker images...${NC}"
    docker image prune -f

    echo -e "\n${GREEN}=======================================================${NC}"
    echo -e "${GREEN}🎉 All microservices built successfully!${NC}"
    echo -e "   - ${BLUE}frontend${NC} (React/Vite)"
    echo -e "   - ${BLUE}backend${NC} (API Gateway)"
    echo -e "   - ${BLUE}ocr-pytorch${NC} (EasyOCR & VietOCR)"
    echo -e "   - ${BLUE}ocr-paddle${NC} (PaddleOCR & PP-Structure)"
    echo -e "\n👉 Run the following command to start the application:"
    echo -e "   ${GREEN}./scripts/deploy.sh${NC}"
    echo -e "${GREEN}=======================================================${NC}"
else
    echo -e "\n${RED}❌ Error: Docker Compose build failed. Please check the logs above.${NC}"
    exit 1
fi
