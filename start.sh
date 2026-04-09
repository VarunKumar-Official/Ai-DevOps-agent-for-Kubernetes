#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

echo "🤖 Starting DevOps AI Agent..."
echo ""
echo "Choose mode:"
echo "1) CLI mode (interactive terminal)"
echo "2) Web UI - Full (port 8080, with auth)"
echo "3) Web UI - Simple (port 5000)"
echo "4) Monitoring mode (auto-healing)"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1) python agent.py ;;
    2) python devops_agent.py ;;
    3) python web_ui.py ;;
    4) python monitoring.py ;;
    *) echo "Invalid choice. Starting CLI mode..."; python agent.py ;;
esac
