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
echo -e "${BLUE}⚙️  Building OCR Playground Microservices Architecture${NC}"
echo -e "${BLUE}=======================================================${NC}"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running. Please start Docker Desktop first.${NC}"
    exit 1
fi

# Removed host virtualenv weight download prompt. Weights will be downloaded during deployment.

echo -e "${YELLOW}🐳 Starting build via Docker Compose...${NC}\n"

# Run docker compose build sequentially to prevent OOM/freeze
docker compose build frontend
if [ $? -ne 0 ]; then echo -e "\n${RED}❌ Error: frontend build failed.${NC}"; exit 1; fi

docker compose build orchestrator
if [ $? -ne 0 ]; then echo -e "\n${RED}❌ Error: orchestrator build failed.${NC}"; exit 1; fi

docker compose build image-processor
if [ $? -ne 0 ]; then echo -e "\n${RED}❌ Error: image-processor build failed.${NC}"; exit 1; fi

docker compose build ocr-pytorch
if [ $? -ne 0 ]; then echo -e "\n${RED}❌ Error: ocr-pytorch build failed.${NC}"; exit 1; fi

docker compose build ocr-paddle
if [ $? -ne 0 ]; then echo -e "\n${RED}❌ Error: ocr-paddle build failed.${NC}"; exit 1; fi

echo -e "\n${GREEN}=======================================================${NC}"
echo -e "${GREEN}🎉 All microservices built successfully!${NC}"
echo -e "   - ${BLUE}frontend${NC} (React/Vite)"
echo -e "   - ${BLUE}backend${NC} (API Gateway)"
echo -e "   - ${BLUE}ocr-pytorch${NC} (EasyOCR & VietOCR)"
echo -e "   - ${BLUE}ocr-paddle${NC} (PaddleOCR & PP-Structure)"
echo -e "\n👉 Run the following command to start the application:"
echo -e "   ${GREEN}./deploy.sh${NC}"
echo -e "${GREEN}=======================================================${NC}"
