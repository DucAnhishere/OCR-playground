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

# Check if weights folder exists and is not empty
if [ ! -d "weights" ] || [ -z "$(ls -A weights 2>/dev/null)" ]; then
    echo -e "${YELLOW}⚠️  Warning: Weights directory not found or empty.${NC}"
    echo -e "${YELLOW}To avoid slow builds and network timeouts inside Docker, we recommend downloading model weights natively first.${NC}"
    read -p "Do you want to download model weights now using host virtualenv? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "backend/.venv/bin/python" ]; then
            echo -e "${BLUE}📥 Downloading weights using backend virtualenv...${NC}"
            backend/.venv/bin/python download_weights.py
        else
            echo -e "${RED}❌ Error: backend virtual environment python not found at backend/.venv/bin/python. Please make sure the virtual environment exists.${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}Continuing build without pre-downloading weights. Containers might download them on first run.${NC}"
    fi
fi

echo -e "${YELLOW}🐳 Starting build via Docker Compose...${NC}\n"

# Run docker compose build
docker compose build

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}=======================================================${NC}"
    echo -e "${GREEN}🎉 All microservices built successfully!${NC}"
    echo -e "   - ${BLUE}frontend${NC} (React/Vite)"
    echo -e "   - ${BLUE}backend${NC} (API Gateway)"
    echo -e "   - ${BLUE}ocr-pytorch${NC} (EasyOCR & VietOCR)"
    echo -e "   - ${BLUE}ocr-paddle${NC} (PaddleOCR & PP-Structure)"
    echo -e "\n👉 Run the following command to start the application:"
    echo -e "   ${GREEN}./deploy.sh${NC}"
    echo -e "${GREEN}=======================================================${NC}"
else
    echo -e "\n${RED}❌ Error: Docker Compose build failed. Please check the logs above.${NC}"
    exit 1
fi
