# DevOps AI Agent 🤖

An AI-powered DevOps assistant for Kubernetes cluster management with natural language interface, auto-remediation, and multi-LLM support.

## Features

- **AI-Powered Chat** — Natural language queries to manage your K8s cluster
- **Multi-LLM Support** — Ollama (local, free) or Google Gemini (cloud)
- **RAG System** — Learns from your cluster docs, YAMLs, and RCA documents
- **Auto-Remediation** — Detects and fixes CrashLoopBackOff, OOMKilled, ImagePullBackOff
- **RBAC Authentication** — User login with Kubernetes service account tokens
- **Namespace Scoping** — Read-only users see only their namespace
- **MCP Integration** — K8s MCP Server support for advanced operations
- **Command Safety** — Safe/restricted command classification with approval layer
- **Conversation Memory** — Remembers context across queries
- **Pod Namespace Auto-Detection** — Automatically finds pod namespaces
- **Multiple Interfaces** — Full Web UI, Simple Web UI, CLI, Monitoring mode

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/<your-username>/devops-ai-agent.git
cd devops-ai-agent
chmod +x setup.sh start.sh
./setup.sh
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your GEMINI_API_KEY (optional if using Ollama)
```

### 3. Run

```bash
source venv/bin/activate

# Full Web UI with auth (recommended)
python devops_agent.py

# Simple CLI mode
python agent.py

# No-LLM simple mode
python simple_agent.py

# Monitoring mode
python monitoring.py
```

Open http://localhost:8080 for the full Web UI.

## Architecture

```
devops-ai-agent/
├── devops_agent.py          # Main agent with Web UI, auth, LLM, MCP
├── agent.py                 # CLI agent with Gemini LLM
├── simple_agent.py          # Simple agent (no LLM needed)
├── web_ui.py                # Basic Flask web interface
├── auth.py                  # Authentication & RBAC
├── rag_system.py            # RAG knowledge base (ChromaDB)
├── monitoring.py            # Auto-healing monitoring loop
├── auto_remediation.py      # Issue detection & auto-fix
├── scheduler.py             # Scheduled health checks
├── manage_users.py          # User management CLI
├── tools/
│   ├── kubectl_tool.py      # Safe kubectl execution
│   ├── docker_tool.py       # Safe docker execution
│   ├── helm_tool.py         # Safe helm execution
│   ├── k8s_mcp_tool.py      # K8s MCP Server integration
│   └── log_analyzer.py      # Log pattern detection
├── templates/
│   ├── index.html           # Full dashboard UI
│   ├── login.html           # Login page
│   └── chatbot.html         # Simple chatbot UI
├── knowledge/               # Your docs for RAG (add YAMLs, MDs, RCAs)
│   ├── cluster_config.md    # Sample cluster config
│   ├── kong_configs/        # API gateway configs
│   ├── kubernetes_yaml/     # K8s manifests
│   └── rca_docs/            # Root cause analysis docs
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── setup.sh
└── start.sh
```

## Usage Examples

### Natural Language Queries
```
> Show all pods
> Why is my pod crashing?
> Check cluster health
> Fix node not ready
> Recommend improvements
```

### Direct Commands
```
> kubectl get pods -A
> kubectl logs my-pod -n my-namespace
> docker ps
```

### Troubleshooting
```
> Fix imagepullbackoff
> Fix pending pods
> Show problem pods
```

## User Management

```bash
# Add user
python manage_users.py add john.doe MyPassword123

# List users
python manage_users.py list

# Remove user
python manage_users.py remove john.doe
```

## Docker Deployment

```bash
docker-compose up -d
```

## Adding Knowledge

Place files in the `knowledge/` directory:
- `knowledge/kubernetes_yaml/` — Your K8s manifests
- `knowledge/kong_configs/` — API gateway configs
- `knowledge/rca_docs/` — Root cause analysis documents
- `knowledge/cluster_config.md` — Cluster-specific info

The RAG system indexes `.yaml`, `.yml`, `.md`, and `.txt` files automatically.

## LLM Configuration

**Option 1: Ollama (Recommended — free, local, unlimited)**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
```

**Option 2: Google Gemini (cloud, rate-limited)**
1. Get free API key at https://makersuite.google.com/app/apikey
2. Add to `.env`: `GEMINI_API_KEY=your-key-here`

## Safety Features

| Command Type | Examples | Behavior |
|---|---|---|
| Safe | get, describe, logs, top | Auto-executed |
| Restricted | delete, scale, apply, rollout | Requires approval |

## Prerequisites

- Python 3.10+
- kubectl configured with cluster access
- Docker (optional)
- Ollama or Gemini API key (optional for simple mode)

## Author

**Varun Kumar**
- 📧 <email>
- 🔗 [LinkedIn](https://linkedin.com/in/devopseng)
