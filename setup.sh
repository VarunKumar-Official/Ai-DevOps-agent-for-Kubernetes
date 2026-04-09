#!/bin/bash

echo "🚀 DevOps AI Agent - Setup"
echo "=========================="

# Install Ollama (optional, for local LLM)
echo ""
echo "1️⃣ Installing Ollama (optional)..."
if ! command -v ollama &> /dev/null; then
    read -p "Install Ollama for local LLM? (y/n): " install_ollama
    if [ "$install_ollama" = "y" ]; then
        curl -fsSL https://ollama.com/install.sh | sh
        sudo systemctl start ollama 2>/dev/null || ollama serve &
        sleep 3
        ollama pull llama3.2
    fi
else
    echo "✅ Ollama already installed"
fi

# Setup Python virtual environment
echo ""
echo "2️⃣ Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt

# Create initial admin user
echo ""
echo "3️⃣ Creating admin user..."
if [ ! -f "users.txt" ]; then
    read -p "Enter admin password: " admin_pass
    python3 manage_users.py add admin "$admin_pass"
fi

# Setup .env
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  Edit .env to add your GEMINI_API_KEY (optional if using Ollama)"
fi

echo ""
echo "✅ Setup Complete!"
echo ""
echo "To start:"
echo "  source venv/bin/activate"
echo "  python devops_agent.py       # Full agent with Web UI (port 8080)"
echo "  python agent.py              # CLI mode"
echo "  python simple_agent.py       # Simple mode (no LLM needed)"
echo "  python web_ui.py             # Basic Web UI (port 5000)"
echo "  python monitoring.py         # Monitoring mode"
