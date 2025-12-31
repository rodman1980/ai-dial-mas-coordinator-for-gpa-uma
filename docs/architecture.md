---
title: MAS Coordinator Architecture
description: Detailed system design, data flow, and architectural decisions for the Multi-Agent System Coordinator
version: 1.0.0
last_updated: 2025-12-31
related: [api.md, setup.md, adr/README.md]
tags: [architecture, design, multi-agent, dial-sdk]
---

# MAS Coordinator Architecture

This document describes the architectural design of the Multi-Agent System (MAS) Coordinator, including system boundaries, component interactions, data flow, and key design decisions.

## Table of Contents
- [System Overview](#system-overview)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [State Management](#state-management)
- [Stage Propagation](#stage-propagation)
- [Design Patterns](#design-patterns)
- [Deployment Architecture](#deployment-architecture)
- [Constraints and Limitations](#constraints-and-limitations)

## System Overview

The MAS Coordinator is a **routing layer** in the DIAL ecosystem that intelligently delegates user requests to specialized agents based on intent analysis.

```mermaid
graph TB
    subgraph "User Interface"
        UI[DIAL Chat UI :3000]
    end
    
    subgraph "Gateway Layer"
        DC[DIAL Core :8080]
    end
    
    subgraph "Coordinator Layer"
        MAS[MAS Coordinator :8055]
    end
    
    subgraph "Agent Layer"
        GPA[GPA Agent :8052]
        UMS[UMS Agent :8042]
    end
    
    subgraph "Service Layer"
        DDG[DuckDuckGo MCP :8051]
        PY[Python Interpreter MCP :8050]
        UMSMCP[UMS MCP Server :8041]
        USRVC[User Service :8040]
    end
    
    subgraph "Infrastructure"
        REDIS[(Redis :6379)]
        LLM[EPAM AI Proxy<br/>GPT-4o/DALL-E]
    end
    
    UI --> DC
    DC --> MAS
    MAS --> GPA
    MAS --> UMS
    GPA --> DDG
    GPA --> PY
    GPA --> LLM
    UMS --> UMSMCP
    UMSMCP --> USRVC
    UMS --> REDIS
    DC --> REDIS
    MAS --> LLM
```

### System Boundaries

**What the MAS Coordinator IS:**
- An intelligent router analyzing user intent
- A response synthesizer creating user-friendly output
- A state orchestrator managing conversation continuity

**What the MAS Coordinator IS NOT:**
- A tool executor (delegates to GPA)
- A user database (delegates to UMS)
- A general-purpose agent (uses specialized agents)

## Component Architecture

### Layer Architecture

```mermaid
graph TD
    subgraph "Presentation Layer"
        A[DIALApp FastAPI Server]
        B[MASCoordinatorApplication<br/>ChatCompletion Handler]
    end
    
    subgraph "Orchestration Layer"
        C[MASCoordinator]
        D[Coordination Logic]
        E[Synthesis Logic]
    end
    
    subgraph "Integration Layer"
        F[GPAGateway]
        G[UMSAgentGateway]
    end
    
    subgraph "Infrastructure Layer"
        H[AsyncDial Client]
        I[HTTPX Client]
        J[StageProcessor]
    end
    
    A --> B
    B --> C
    C --> D
    C --> E
    D --> F
    D --> G
    F --> H
    G --> I
    C --> J
```

### Module Responsibilities

| Module | File | Responsibility |
|--------|------|----------------|
| **Application** | [task/app.py](../task/app.py) | DIAL app initialization, endpoint registration |
| **Coordinator** | [task/agent.py](../task/agent.py) | Request orchestration, routing, synthesis |
| **GPA Gateway** | [task/coordination/gpa.py](../task/coordination/gpa.py) | GPA communication, stage propagation |
| **UMS Gateway** | [task/coordination/ums_agent.py](../task/coordination/ums_agent.py) | UMS conversation management |
| **Models** | [task/models.py](../task/models.py) | Pydantic data schemas |
| **Prompts** | [task/prompts.py](../task/prompts.py) | LLM system prompts |
| **Stage Utils** | [task/stage_util.py](../task/stage_util.py) | Stage lifecycle management |

## Data Flow

### Request Processing Sequence

```mermaid
sequenceDiagram
    participant User
    participant MASCoordinator
    participant LLM
    participant GPA/UMS as Agent (GPA or UMS)
    participant Stage

    User->>MASCoordinator: Chat completion request
    
    rect rgb(230, 240, 255)
        note right of MASCoordinator: Stage 1: Coordination
        MASCoordinator->>Stage: Open "Coordination" stage
        MASCoordinator->>LLM: Analyze intent (JSON schema)
        LLM-->>MASCoordinator: CoordinationRequest {agent_name, instructions}
        MASCoordinator->>Stage: Log routing decision
        MASCoordinator->>Stage: Close coordination stage
    end
    
    rect rgb(240, 255, 240)
        note right of MASCoordinator: Stage 2: Agent Execution
        MASCoordinator->>Stage: Open "Agent" stage
        MASCoordinator->>GPA/UMS: Delegate request with instructions
        
        loop Streaming Response
            GPA/UMS-->>MASCoordinator: Stream chunk (content/stages/attachments)
            MASCoordinator->>Stage: Append content
            MASCoordinator->>Stage: Mirror nested stages
        end
        
        GPA/UMS-->>MASCoordinator: Complete response + state
        MASCoordinator->>Stage: Close agent stage
    end
    
    rect rgb(255, 245, 230)
        note right of MASCoordinator: Stage 3: Synthesis
        MASCoordinator->>LLM: Synthesize final response
        
        loop Streaming Synthesis
            LLM-->>MASCoordinator: Stream chunk
            MASCoordinator->>User: Stream to client
        end
    end
    
    MASCoordinator-->>User: Complete response with attachments/state
```

### Message Flow Details

1. **Incoming Request** (User → Coordinator)
   - OpenAI-compatible chat completion format
   - Headers: `Api-Key`, `x-conversation-id`
   - Body: `{messages: [...], model: "mas-coordinator"}`

2. **Coordination Decision** (Coordinator → LLM)
   - System prompt: [COORDINATION_REQUEST_SYSTEM_PROMPT](../task/prompts.py)
   - Structured output: `CoordinationRequest` JSON schema
   - Response: `{agent_name: "GPA"|"UMS", additional_instructions: string?}`

3. **Agent Delegation** (Coordinator → Agent)
   - **GPA**: Filtered message history + tool state restoration
   - **UMS**: New or existing conversation ID + message augmentation

4. **Agent Response** (Agent → Coordinator)
   - **GPA**: Streaming with custom_content (stages, attachments, state)
   - **UMS**: SSE format with conversation_id

5. **Synthesis** (Coordinator → LLM → User)
   - System prompt: [FINAL_RESPONSE_SYSTEM_PROMPT](../task/prompts.py)
   - Context: Original request + agent response
   - Output: Polished, user-friendly response

## State Management

### Conversation State Patterns

```mermaid
stateDiagram-v2
    [*] --> NoState: First message
    
    NoState --> GPAState: GPA handles request
    NoState --> UMSState: UMS handles request
    
    GPAState --> GPAState: Multi-turn with tools
    UMSState --> UMSState: Multi-turn in same conversation
    
    GPAState --> UMSState: User switches to user mgmt
    UMSState --> GPAState: User switches to general task
    
    state GPAState {
        [*] --> ToolHistory
        ToolHistory --> ToolHistory: Store tool calls
    }
    
    state UMSState {
        [*] --> ConversationID
        ConversationID --> ConversationID: Reuse conversation
    }
```

### State Storage Strategy

**GPA State** ([coordination/gpa.py](../task/coordination/gpa.py)):
```python
{
    "is_gpa": True,
    "gpa_messages": {
        # GPA's internal tool call state
        # Restored on next GPA request
    }
}
```

**UMS State** ([coordination/ums_agent.py](../task/coordination/ums_agent.py)):
```python
{
    "ums_conversation_id": "uuid-string"
    # UMS agent maintains full history server-side
}
```

**Why Different Strategies?**
- **GPA**: Stateless service; requires tool call history for multi-turn
- **UMS**: Stateful service with conversation API; only needs conversation ID

## Stage Propagation

### The Stage Mirroring Pattern

Stages provide real-time UI feedback. GPA's internal stages must be mirrored to the coordinator's response.

```mermaid
sequenceDiagram
    participant GPA
    participant Coordinator
    participant UI

    GPA->>Coordinator: delta.custom_content.stages[0] {name: "Web Search", status: "open"}
    Coordinator->>UI: Open stage "Web Search"
    
    GPA->>Coordinator: delta.custom_content.stages[0] {content: "Searching..."}
    Coordinator->>UI: Append content to stage
    
    GPA->>Coordinator: delta.custom_content.stages[0] {status: "completed"}
    Coordinator->>UI: Close stage "Web Search"
```

**Implementation** ([coordination/gpa.py](../task/coordination/gpa.py#L90-L115)):
- Track stages by `index` in a `dict[int, Stage]`
- Open new stages on first appearance
- Append content to existing stages
- Close on `status: "completed"`

## Design Patterns

### 1. Gateway Pattern

**Purpose**: Isolate agent-specific communication logic

```mermaid
classDiagram
    class Gateway {
        <<interface>>
        +response(choice, stage, request, instructions) Message
    }
    
    class GPAGateway {
        -endpoint: str
        +response() Message
        -__prepare_gpa_messages()
    }
    
    class UMSAgentGateway {
        -ums_agent_endpoint: str
        +response() Message
        -__get_ums_conversation_id()
        -__create_ums_conversation()
        -__call_ums_agent()
    }
    
    Gateway <|-- GPAGateway
    Gateway <|-- UMSAgentGateway
```

**Benefits**:
- Agent-specific concerns encapsulated
- Easy to add new agents (extend Gateway)
- Testable in isolation

### 2. Three-Stage Orchestration Pattern

**Coordination → Delegation → Synthesis**

Each stage has a clear responsibility:
1. **Coordination**: Decision-making (which agent?)
2. **Delegation**: Execution (call the agent)
3. **Synthesis**: Presentation (polish the output)

### 3. Structured Output with JSON Schema

Forces LLM responses into validated Pydantic models:

```python
extra_body={
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "response",
            "schema": CoordinationRequest.model_json_schema()
        }
    }
}
```

**Benefits**:
- Type-safe routing decisions
- No parsing errors
- Self-documenting API

## Deployment Architecture

### Docker Compose Services

```mermaid
graph TB
    subgraph "Frontend"
        CHAT[DIAL Chat :3000]
        THEME[Themes :3001]
    end
    
    subgraph "Core Services"
        CORE[DIAL Core :8080]
        ADAPTER[DIAL Adapter :internal]
    end
    
    subgraph "Agents"
        MAS[MAS Coordinator :8055<br/>HOST NETWORK]
        GPA[GPA Agent :8052]
        UMS[UMS Agent :8042]
    end
    
    subgraph "MCP Servers"
        DDG[DuckDuckGo :8051]
        PY[Python Interpreter :8050]
        UMSMCP[UMS MCP :8041]
    end
    
    subgraph "Data Services"
        USRVC[User Service :8040]
        REDIS[Redis :6379]
        REDISUI[Redis Insight :6380]
    end
    
    CHAT --> THEME
    CHAT --> CORE
    CORE --> ADAPTER
    CORE --> MAS
    MAS -.runs on host.-> HOST[Host Machine]
    CORE --> GPA
    CORE --> UMS
    GPA --> DDG
    GPA --> PY
    UMS --> UMSMCP
    UMSMCP --> USRVC
    REDIS --- CORE
    REDIS --- UMS
    REDISUI --> REDIS
```

**Port Mapping:**
| Service | Internal Port | External Port | Network |
|---------|--------------|---------------|---------|
| MAS Coordinator | 8055 | 8055 | host.docker.internal |
| GPA Agent | 5000 | 8052 | Docker bridge |
| UMS Agent | 8000 | 8042 | Docker bridge |
| DIAL Core | 8080 | 8080 | Docker bridge |
| Redis | 6379 | 6379 | Docker bridge |

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DIAL_API_KEY` | ✅ | - | EPAM AI Proxy API key |
| `DIAL_ENDPOINT` | ❌ | http://localhost:8080 | DIAL Core URL |
| `UMS_AGENT_ENDPOINT` | ❌ | http://localhost:8042 | UMS Agent URL |
| `DEPLOYMENT_NAME` | ❌ | gpt-4o | LLM model name |
| `LOG_LEVEL` | ❌ | INFO | Logging verbosity |

## Constraints and Limitations

### Technical Constraints

1. **Pydantic Version Mismatch**
   - `aidial_client` uses Pydantic v1-style models
   - `aidial_sdk` uses Pydantic v2
   - **Workaround**: Convert via `.dict(exclude_none=True)`

2. **Single-Choice Response**
   - Coordinator always returns one choice (no multi-choice support)

3. **Synchronous Agent Calls**
   - Agents called sequentially, not in parallel
   - Future: Could support multi-agent consultation

4. **State Size Limits**
   - Large tool call histories may exceed Redis limits
   - TODO: Implement state pruning strategy

### Operational Constraints

1. **LLM Dependency**
   - Three LLM calls per request (coordination + agent + synthesis)
   - Failure in routing stage = entire request fails

2. **Network Latency**
   - Coordinator → Agent → MCP → Service (multi-hop)
   - Affects time-to-first-token

3. **Conversation Isolation**
   - GPA and UMS maintain separate conversation contexts
   - No cross-agent context sharing

## Security Considerations

1. **API Key Management**
   - ⚠️ **CRITICAL**: Remove keys from [core/config.json](../core/config.json) before commit
   - Use environment variables for all secrets

2. **Input Validation**
   - Pydantic models validate LLM outputs
   - DIAL SDK validates incoming requests

3. **Network Boundaries**
   - All services in Docker network except coordinator (host network)
   - No direct external access to agents/MCP servers

## Future Architecture Considerations

See [roadmap.md](roadmap.md) for planned enhancements:
- Multi-agent parallel execution
- Agent capability discovery
- Dynamic agent registration
- State compression strategies

---

**Related Documents**:
- [API Reference](api.md) - Detailed interface specifications
- [ADR-001: Gateway Pattern](adr/001-gateway-pattern.md) - Design decision rationale
- [ADR-002: Three-Stage Orchestration](adr/002-three-stage-orchestration.md) - Flow design
