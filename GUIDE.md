# MAS Coordinator Setup & Usage Guide

A Multi-Agent System Coordinator that routes user requests to specialized agents (GPA or UMS).

## Prerequisites

- Python 3.12+ (3.13 works fine)
- Docker & Docker Compose
- DIAL API Key from EPAM AI Proxy

## Quick Start

### 1. Set Environment Variables

```bash
export DIAL_API_KEY=your_api_key_here
```

### 2. Start Infrastructure

```bash
docker-compose up -d
```

This starts:
| Service | Port | Description |
|---------|------|-------------|
| DIAL Chat UI | 3000 | Web interface |
| DIAL Core | 8080 | API gateway |
| Redis | 6379 | State storage |
| Redis Insight | 6380 | Redis GUI |
| UMS Agent | 8042 | User management |
| GPA | 8052 | General-purpose agent |

### 3. Create Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run MAS Coordinator

```bash
python -m uvicorn task.app:app --port 8055 --host 0.0.0.0
```

## Testing

### Via DIAL Chat UI

1. Open http://localhost:3000
2. Select "MAS Coordinator Agent" from model list
3. Start chatting

### Via cURL

**UMS Agent routing:**
```bash
curl -X POST http://localhost:8055/openai/deployments/mas-coordinator/chat/completions \
  -H "Content-Type: application/json" \
  -H "Api-Key: dial_api_key" \
  -d '{"messages": [{"role": "user", "content": "Do we have Andrej Karpathy as a user?"}]}'
```

**GPA routing:**
```bash
curl -X POST http://localhost:8055/openai/deployments/mas-coordinator/chat/completions \
  -H "Content-Type: application/json" \
  -H "Api-Key: dial_api_key" \
  -d '{"messages": [{"role": "user", "content": "What is the weather in Kyiv?"}]}'
```

### Direct Agent Testing

**GPA direct:**
```bash
curl -X POST http://localhost:8052/openai/deployments/general-purpose-agent/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "hi"}]}'
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Request                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   MAS Coordinator (:8055)                    │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 1. Coordination Stage: LLM decides GPA vs UMS           ││
│  │ 2. Agent Stage: Delegate to chosen agent                ││
│  │ 3. Synthesis: LLM creates final response                ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                    │                   │
        ┌───────────┘                   └───────────┐
        ▼                                           ▼
┌───────────────────┐                   ┌───────────────────┐
│   GPA (:8052)     │                   │  UMS Agent (:8042)│
│ • Web search      │                   │ • User CRUD       │
│ • RAG/documents   │                   │ • User search     │
│ • Python code     │                   │                   │
│ • Image gen       │                   │                   │
└───────────────────┘                   └───────────────────┘
        │                                           │
        ▼                                           ▼
┌───────────────────┐                   ┌───────────────────┐
│ MCP Servers       │                   │ UMS MCP (:8041)   │
│ • DDG Search      │                   │ User Service API  │
│ • Python Interp.  │                   │                   │
└───────────────────┘                   └───────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `task/app.py` | DIAL app entry point, uvicorn server |
| `task/agent.py` | MAS Coordinator orchestration logic |
| `task/prompts.py` | System prompts for routing & synthesis |
| `task/coordination/gpa.py` | GPA gateway with stage propagation |
| `task/coordination/ums_agent.py` | UMS gateway with conversation tracking |
| `task/models.py` | Pydantic models (CoordinationRequest) |
| `core/config.json` | DIAL Core configuration |

## Routing Logic

The coordinator uses GPT-4o to analyze user intent:

| User Intent | Routes To |
|-------------|-----------|
| Create/search/update/delete users | UMS Agent |
| Web search, calculations, code | GPA |
| Document analysis (PDF, CSV) | GPA |
| Image generation | GPA |

## Troubleshooting

### "Connection refused" errors
```bash
# Check all services are running
docker-compose ps

# Restart specific service
docker-compose restart core
```

### API Key issues
```bash
# Verify key is set
echo $DIAL_API_KEY

# Check core/config.json has ${DIAL_API_KEY} in upstreams
```

### View Redis data
1. Open http://localhost:6380
2. Connect to `redis:6379` (use service name, not localhost)

### Check logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f general-purpose-agent
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DIAL_API_KEY` | - | Required. EPAM AI Proxy key |
| `DIAL_ENDPOINT` | `http://localhost:8080` | DIAL Core URL |
| `UMS_AGENT_ENDPOINT` | `http://localhost:8042` | UMS Agent URL |
| `DEPLOYMENT_NAME` | `gpt-4o` | LLM model for routing |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## Security Note

⚠️ **Before committing**: Remove any hardcoded API keys from `core/config.json`. Use `${DIAL_API_KEY}` environment variable reference instead.
