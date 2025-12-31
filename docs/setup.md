---
title: Setup Guide
description: Environment setup, installation, and configuration instructions for MAS Coordinator
version: 1.0.0
last_updated: 2025-12-31
related: [README.md, testing.md]
tags: [setup, installation, configuration]
---

# Setup Guide

This guide walks through setting up the MAS Coordinator development environment from scratch.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Infrastructure Setup](#infrastructure-setup)
- [Coordinator Setup](#coordinator-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **OS**: macOS, Linux, or Windows (with WSL2)
- **RAM**: Minimum 8GB (16GB recommended)
- **Disk**: 5GB free space for Docker images

### Required Software

| Software | Version | Installation |
|----------|---------|-------------|
| Python | 3.12+ | [python.org](https://www.python.org/downloads/) |
| Docker | 24.0+ | [docker.com](https://www.docker.com/get-started) |
| Docker Compose | 2.20+ | Included with Docker Desktop |
| Git | 2.30+ | [git-scm.com](https://git-scm.com/) |

**Verify installations:**
```bash
python3 --version  # Should be 3.12+
docker --version   # Should be 24.0+
docker-compose --version  # Should be 2.20+
```

### API Access
- **EPAM AI Proxy API Key**: Required for GPT-4o and DALL-E access
  - Obtain from: https://ai-proxy.lab.epam.com
  - Store securely (never commit to Git)

## Environment Setup

### 1. Clone Repository

```bash
git clone git@git.epam.com:ai-dial-mas-coordinator-for-gpa-uma.git
cd ai-dial-mas-coordinator-for-gpa-uma
```

### 2. Configure Environment Variables

Create a `.env` file (or export directly):

```bash
# Required: EPAM AI Proxy API key
export DIAL_API_KEY="your_api_key_here"

# Optional: Override defaults
export DIAL_ENDPOINT="http://localhost:8080"
export UMS_AGENT_ENDPOINT="http://localhost:8042"
export DEPLOYMENT_NAME="gpt-4o"
export LOG_LEVEL="INFO"
```

**⚠️ Security Note**: Never commit `.env` files or hardcode API keys in code.

### 3. Create Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv dial_mas_coordinator

# Activate environment
# macOS/Linux:
source dial_mas_coordinator/bin/activate

# Windows (PowerShell):
# dial_mas_coordinator\Scripts\Activate.ps1

# Verify activation (should show venv path)
which python
```

### 4. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Installed packages:**
- `aidial-sdk==0.27.0` - DIAL application framework
- `aidial-client==0.3.0` - DIAL API client
- `pydantic==2.12.3` - Data validation
- `httpx>=0.28.1` - Async HTTP client

**Verify installation:**
```bash
python -c "import aidial_sdk; print(aidial_sdk.__version__)"
# Expected output: 0.27.0
```

## Infrastructure Setup

### 1. Configure DIAL Core

Edit [core/config.json](../core/config.json) to set your API key:

```json
{
  "keys": {
    "dial_api_key": {
      "project": "TEST-PROJECT",
      "role": "default"
    }
  },
  "models": {
    "gpt-4o": {
      "upstreams": [
        {
          "endpoint": "https://ai-proxy.lab.epam.com/openai/deployments/gpt-4o/chat/completions",
          "key": "${DIAL_API_KEY}"
        }
      ]
    }
  }
}
```

**⚠️ CRITICAL**: Remove API keys from this file before committing!

### 2. Start Docker Services

```bash
# Start all services in background
docker-compose up -d

# Verify all services are running
docker-compose ps
```

**Expected output:**
```
NAME                         STATUS    PORTS
chat                         Up        0.0.0.0:3000->3000/tcp
core                         Up        0.0.0.0:8080->8080/tcp
redis                        Up        0.0.0.0:6379->6379/tcp
redis-insight                Up        0.0.0.0:6380->5540/tcp
general-purpose-agent        Up        0.0.0.0:8052->5000/tcp
ums-agent                    Up        0.0.0.0:8042->8000/tcp
python-interpreter-mcp-server Up       0.0.0.0:8050->8000/tcp
ddg-search-mcp-server        Up        0.0.0.0:8051->8000/tcp
ums-mcp-server               Up        0.0.0.0:8041->8005/tcp
userservice                  Up        0.0.0.0:8040->8000/tcp
```

### 3. Verify Service Health

**Check DIAL Core:**
```bash
curl http://localhost:8080/health
# Expected: {"status": "healthy"}
```

**Check GPA Agent:**
```bash
curl http://localhost:8052/health
# Expected: 200 OK
```

**Check UMS Agent:**
```bash
curl http://localhost:8042/health
# Expected: 200 OK
```

### 4. Configure Redis (Optional)

Access Redis Insight for debugging:
1. Open http://localhost:6380
2. Click "Add Redis Database"
3. **Host**: `redis` (service name in Docker network)
4. **Port**: `6379`
5. **Database Alias**: `DIAL Core Redis`

## Coordinator Setup

### 1. Verify Project Structure

```bash
tree -L 2 task/
```

**Expected structure:**
```
task/
├── __init__.py
├── app.py              # DIAL application entry point
├── agent.py            # MASCoordinator orchestration
├── models.py           # Pydantic schemas
├── prompts.py          # LLM system prompts
├── stage_util.py       # Stage management utilities
├── logging_config.py   # Logging setup
└── coordination/       # Agent gateways
    ├── __init__.py
    ├── gpa.py         # GPA gateway
    └── ums_agent.py   # UMS agent gateway
```

### 2. Run MAS Coordinator

```bash
# Ensure virtual environment is activated
source dial_mas_coordinator/bin/activate

# Run with uvicorn
python -m uvicorn task.app:app --port 8055 --host 0.0.0.0 --reload

# Alternative: Direct Python execution
# python task/app.py
```

**Expected output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8055 (Press CTRL+C to quit)
2025-12-31 10:00:00 - task.app - INFO - Starting MAS Coordinator on port 8055
2025-12-31 10:00:00 - task.app - INFO - DIAL Endpoint: http://localhost:8080
2025-12-31 10:00:00 - task.app - INFO - UMS Agent Endpoint: http://localhost:8042
```

### 3. Development Mode

For auto-reload on code changes:
```bash
uvicorn task.app:app --port 8055 --host 0.0.0.0 --reload
```

## Verification

### Test 1: Health Check

```bash
curl -X POST http://localhost:8055/openai/deployments/mas-coordinator/chat/completions \
  -H "Content-Type: application/json" \
  -H "Api-Key: dial_api_key" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

**Expected**: JSON response with assistant message.

### Test 2: GPA Routing

```bash
curl -X POST http://localhost:8055/openai/deployments/mas-coordinator/chat/completions \
  -H "Content-Type: application/json" \
  -H "Api-Key: dial_api_key" \
  -d '{
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "stream": false
  }'
```

**Expected**: Response using Python code interpreter via GPA.

### Test 3: UMS Routing

```bash
curl -X POST http://localhost:8055/openai/deployments/mas-coordinator/chat/completions \
  -H "Content-Type: application/json" \
  -H "Api-Key: dial_api_key" \
  -d '{
    "messages": [{"role": "user", "content": "List all users"}],
    "stream": false
  }'
```

**Expected**: User list from UMS agent.

### Test 4: DIAL Chat UI

1. Open http://localhost:3000
2. Log in (any credentials work in test mode)
3. Select "MAS Coordinator Agent" from model dropdown
4. Send a test message
5. Verify stages appear in UI

## Troubleshooting

### Issue: `DIAL_API_KEY` not set

**Symptoms:**
```
ERROR: DIAL_API_KEY environment variable not set
```

**Solution:**
```bash
export DIAL_API_KEY="your_api_key_here"
# Restart coordinator
```

### Issue: Docker services not starting

**Symptoms:**
```
Error response from daemon: Ports are not available
```

**Solution:**
```bash
# Check port conflicts
lsof -i :8080
lsof -i :3000

# Stop conflicting services or change ports in docker-compose.yml
```

### Issue: Import errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'aidial_sdk'
```

**Solution:**
```bash
# Verify virtual environment is activated
which python  # Should show venv path

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Connection refused to GPA/UMS

**Symptoms:**
```
httpx.ConnectError: Connection refused [Errno 61]
```

**Solution:**
```bash
# Check service status
docker-compose ps

# Restart services
docker-compose restart general-purpose-agent ums-agent

# Check logs
docker-compose logs general-purpose-agent
```

### Issue: Redis connection errors

**Symptoms:**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solution:**
```bash
# Restart Redis
docker-compose restart redis

# Verify Redis is accessible
docker-compose exec redis redis-cli ping
# Expected: PONG
```

### Issue: Streaming not working

**Symptoms:**
Response comes all at once instead of streaming.

**Solution:**
```bash
# Ensure stream=true in request
curl -N -X POST ... -d '{"stream": true, ...}'

# Check uvicorn timeout settings
uvicorn task.app:app --timeout-keep-alive 120
```

### Getting Help

**Check logs:**
```bash
# Coordinator logs
tail -f logs/coordinator.log

# Docker service logs
docker-compose logs -f core
docker-compose logs -f general-purpose-agent
docker-compose logs -f ums-agent
```

**Enable debug logging:**
```bash
export LOG_LEVEL="DEBUG"
python -m uvicorn task.app:app --port 8055 --log-level debug
```

## Next Steps

- Review [Architecture](architecture.md) to understand system design
- Explore [API Reference](api.md) for endpoint details
- Run tests: [Testing Guide](testing.md)
- Check [ADR Index](adr/README.md) for design decisions

---

**Last Updated**: 2025-12-31  
**Maintainer**: TODO: Add maintainer contact
