#!/bin/bash

# ========================================
# AUTONOMOUS BUSINESS PLATFORM LAUNCHER
# ========================================
# This script starts both the FastAPI backend and Streamlit frontend
#
# Usage:
#   ./start_platform.sh          # Start both services
#   ./start_platform.sh backend  # Start only FastAPI backend
#   ./start_platform.sh frontend # Start only Streamlit frontend
#   ./start_platform.sh stop     # Stop all services
#
# Services:
#   - FastAPI Backend: http://localhost:8000 (API + WebSocket)
#   - Streamlit Frontend: http://localhost:8501 (UI)
#   - Ray Dashboard: http://127.0.0.1:8265 (Monitoring)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-8501}
BACKEND_HOST=${BACKEND_HOST:-0.0.0.0}
FRONTEND_HOST=${FRONTEND_HOST:-0.0.0.0}

# PID files
PID_DIR=".pids"
BACKEND_PID="$PID_DIR/fastapi.pid"
FRONTEND_PID="$PID_DIR/streamlit.pid"

# Create PID directory
mkdir -p "$PID_DIR"

# ========================================
# FUNCTIONS
# ========================================

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║     🚀 AUTONOMOUS BUSINESS PLATFORM                      ║"
    echo "║     FastAPI + Streamlit + Ray                            ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_dependencies() {
    echo -e "${YELLOW}Checking dependencies...${NC}"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 not found${NC}"
        exit 1
    fi
    
    # Check pip packages
    if ! python3 -c "import fastapi" 2>/dev/null; then
        echo -e "${YELLOW}📦 Installing FastAPI...${NC}"
        pip install fastapi uvicorn websockets python-multipart
    fi
    
    if ! python3 -c "import streamlit" 2>/dev/null; then
        echo -e "${RED}❌ Streamlit not found. Please install: pip install streamlit${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All dependencies OK${NC}"
}

start_backend() {
    echo -e "${YELLOW}Starting FastAPI backend on port $BACKEND_PORT...${NC}"
    
    # Check if already running
    if [ -f "$BACKEND_PID" ] && kill -0 $(cat "$BACKEND_PID") 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Backend already running (PID: $(cat $BACKEND_PID))${NC}"
        return 0
    fi
    
    # Start FastAPI
    nohup python3 -m uvicorn fastapi_backend:app \
        --host $BACKEND_HOST \
        --port $BACKEND_PORT \
        --log-level info \
        > logs/fastapi.log 2>&1 &
    
    echo $! > "$BACKEND_PID"
    
    # Wait for startup
    sleep 2
    
    if kill -0 $(cat "$BACKEND_PID") 2>/dev/null; then
        echo -e "${GREEN}✅ FastAPI backend started (PID: $(cat $BACKEND_PID))${NC}"
        echo -e "   📍 API: http://localhost:$BACKEND_PORT"
        echo -e "   📍 Docs: http://localhost:$BACKEND_PORT/docs"
        echo -e "   📍 WebSocket: ws://localhost:$BACKEND_PORT/ws"
    else
        echo -e "${RED}❌ Failed to start FastAPI backend. Check logs/fastapi.log${NC}"
        return 1
    fi
}

start_frontend() {
    echo -e "${YELLOW}Starting Streamlit frontend on port $FRONTEND_PORT...${NC}"
    
    # Check if already running
    if [ -f "$FRONTEND_PID" ] && kill -0 $(cat "$FRONTEND_PID") 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Frontend already running (PID: $(cat $FRONTEND_PID))${NC}"
        return 0
    fi
    
    # Start Streamlit
    nohup streamlit run autonomous_business_platform.py \
        --server.port $FRONTEND_PORT \
        --server.address $FRONTEND_HOST \
        --server.headless true \
        > logs/streamlit.log 2>&1 &
    
    echo $! > "$FRONTEND_PID"
    
    # Wait for startup
    sleep 3
    
    if kill -0 $(cat "$FRONTEND_PID") 2>/dev/null; then
        echo -e "${GREEN}✅ Streamlit frontend started (PID: $(cat $FRONTEND_PID))${NC}"
        echo -e "   📍 UI: http://localhost:$FRONTEND_PORT"
    else
        echo -e "${RED}❌ Failed to start Streamlit. Check logs/streamlit.log${NC}"
        return 1
    fi
}

stop_service() {
    local name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            echo -e "${YELLOW}Stopping $name (PID: $pid)...${NC}"
            kill $pid
            sleep 2
            if kill -0 $pid 2>/dev/null; then
                kill -9 $pid
            fi
            echo -e "${GREEN}✅ $name stopped${NC}"
        else
            echo -e "${YELLOW}$name not running${NC}"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}$name not running (no PID file)${NC}"
    fi
}

stop_all() {
    echo -e "${YELLOW}Stopping all services...${NC}"
    stop_service "Streamlit" "$FRONTEND_PID"
    stop_service "FastAPI" "$BACKEND_PID"
    
    # Also kill any orphaned processes
    pkill -f "uvicorn fastapi_backend" 2>/dev/null || true
    pkill -f "streamlit run autonomous_business_platform" 2>/dev/null || true
    
    echo -e "${GREEN}✅ All services stopped${NC}"
}

show_status() {
    echo -e "${BLUE}Service Status:${NC}"
    
    if [ -f "$BACKEND_PID" ] && kill -0 $(cat "$BACKEND_PID") 2>/dev/null; then
        echo -e "  ${GREEN}✅ FastAPI Backend: Running (PID: $(cat $BACKEND_PID))${NC}"
    else
        echo -e "  ${RED}❌ FastAPI Backend: Stopped${NC}"
    fi
    
    if [ -f "$FRONTEND_PID" ] && kill -0 $(cat "$FRONTEND_PID") 2>/dev/null; then
        echo -e "  ${GREEN}✅ Streamlit Frontend: Running (PID: $(cat $FRONTEND_PID))${NC}"
    else
        echo -e "  ${RED}❌ Streamlit Frontend: Stopped${NC}"
    fi
    
    # Check Ray
    if python3 -c "import ray; print(ray.is_initialized())" 2>/dev/null | grep -q "True"; then
        echo -e "  ${GREEN}✅ Ray: Initialized${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Ray: Not initialized (will start with backend)${NC}"
    fi
}

show_logs() {
    echo -e "${BLUE}Tailing logs (Ctrl+C to exit)...${NC}"
    tail -f logs/fastapi.log logs/streamlit.log
}

# ========================================
# MAIN
# ========================================

# Create logs directory
mkdir -p logs

case "${1:-all}" in
    all)
        print_header
        check_dependencies
        start_backend
        start_frontend
        echo ""
        echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  �� Platform is ready!                                   ║${NC}"
        echo -e "${GREEN}╠══════════════════════════════════════════════════════════╣${NC}"
        echo -e "${GREEN}║  FastAPI API:    http://localhost:$BACKEND_PORT             ║${NC}"
        echo -e "${GREEN}║  API Docs:       http://localhost:$BACKEND_PORT/docs         ║${NC}"
        echo -e "${GREEN}║  Streamlit UI:   http://localhost:$FRONTEND_PORT            ║${NC}"
        echo -e "${GREEN}║  Ray Dashboard:  http://127.0.0.1:8265               ║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
        ;;
    backend)
        print_header
        check_dependencies
        start_backend
        ;;
    frontend)
        print_header
        check_dependencies
        start_frontend
        ;;
    stop)
        print_header
        stop_all
        ;;
    restart)
        print_header
        stop_all
        sleep 2
        check_dependencies
        start_backend
        start_frontend
        ;;
    status)
        print_header
        show_status
        ;;
    logs)
        show_logs
        ;;
    all|"")
        print_header
        check_dependencies
        start_backend
        start_frontend
        echo ""
    *)
        echo "Usage: $0 {all|backend|frontend|stop|restart|status|logs}"
        exit 1
        ;;
esac
