#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting SSR Consumer Research Development Environment...${NC}"

# Check for .venv311
if [ ! -d ".venv311" ]; then
    echo "Creating virtual environment..."
    python3.11 -m venv .venv311
    source .venv311/bin/activate
    pip install -e "."
    pip install -r requirements-dev.txt
else
    source .venv311/bin/activate
fi

# Ensure frontend dependencies are installed
if [ -d "web_ui" ]; then
    echo -e "${BLUE}Checking frontend dependencies...${NC}"
    cd web_ui
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    cd ..
fi

# Kill background processes on exit
trap 'kill $(jobs -p)' EXIT

echo -e "${GREEN}Starting Backend (FastAPI)...${NC}"
uvicorn src.ssr_service.api:app --reload --port 8000 &

echo -e "${GREEN}Starting Frontend (Vite)...${NC}"
cd web_ui
npm run dev -- --open &

# Wait for user to exit
wait
