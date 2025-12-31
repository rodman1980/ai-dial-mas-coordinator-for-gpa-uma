---
title: API Reference
description: Complete API documentation for MAS Coordinator endpoints, interfaces, and data models
version: 1.0.0
last_updated: 2025-12-31
related: [architecture.md, setup.md]
tags: [api, reference, endpoints]
---

# API Reference

Complete API documentation for the MAS Coordinator, including endpoints, request/response formats, and data models.

## Table of Contents
- [Endpoints](#endpoints)
- [Request Format](#request-format)
- [Response Format](#response-format)
- [Data Models](#data-models)
- [Custom Content](#custom-content)
- [Error Handling](#error-handling)
- [Code Interfaces](#code-interfaces)

## Endpoints

### Chat Completion

Create a chat completion routed through the MAS Coordinator.

```http
POST /openai/deployments/mas-coordinator/chat/completions
```

**Headers:**
```
Content-Type: application/json
Api-Key: dial_api_key
x-conversation-id: <optional-conversation-id>
```

**Body Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `messages` | array | ✅ | Array of message objects |
| `stream` | boolean | ❌ | Enable streaming (default: false) |
| `temperature` | number | ❌ | Sampling temperature (0-2) |
| `max_tokens` | integer | ❌ | Maximum tokens to generate |
| `model` | string | ❌ | Model override (ignored) |

**Example Request:**
```bash
curl -X POST http://localhost:8055/openai/deployments/mas-coordinator/chat/completions \
  -H "Content-Type: application/json" \
  -H "Api-Key: dial_api_key" \
  -H "x-conversation-id: test-conversation-123" \
  -d '{
    "messages": [
      {"role": "user", "content": "List all users named John"}
    ],
    "stream": true
  }'
```

**Example Response (non-streaming):**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1704067200,
  "model": "mas-coordinator",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Found 3 users named John:\n1. John Smith (ID: 123)\n2. John Doe (ID: 456)\n3. John Brown (ID: 789)",
        "custom_content": {
          "state": {
            "ums_conversation_id": "conv-uuid-456"
          }
        }
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 45,
    "total_tokens": 65
  }
}
```

**Example Response (streaming):**
```
data: {"choices":[{"index":0,"delta":{"role":"assistant","content":"Found"},"finish_reason":null}]}

data: {"choices":[{"index":0,"delta":{"content":" 3"},"finish_reason":null}]}

data: {"choices":[{"index":0,"delta":{"content":" users"},"finish_reason":null}]}

data: {"choices":[{"index":0,"delta":{"custom_content":{"stages":[{"index":0,"name":"🧭 Coordination","status":"open"}]}},"finish_reason":null}]}

data: {"choices":[{"index":0,"delta":{"custom_content":{"stages":[{"index":0,"status":"completed"}]}},"finish_reason":null}]}

data: [DONE]
```

## Request Format

### Message Object

```typescript
interface Message {
  role: "system" | "user" | "assistant";
  content?: string;
  custom_content?: CustomContent;
}
```

**Example:**
```json
{
  "role": "user",
  "content": "What is the weather in Paris?",
  "custom_content": {
    "attachments": [
      {
        "type": "image/png",
        "url": "data:image/png;base64,iVBORw0KG..."
      }
    ]
  }
}
```

### Custom Content Object

```typescript
interface CustomContent {
  attachments?: Attachment[];
  state?: Record<string, any>;
  stages?: Stage[];
}
```

**Attachments:**
Supported file types for upload:
- Images: `image/png`, `image/jpeg`
- Documents: `application/pdf`, `text/plain`, `text/csv`

**State:**
Arbitrary JSON object for conversation state persistence.

## Response Format

### Streaming Response

Streaming responses use Server-Sent Events (SSE) format:

**Delta Structure:**
```typescript
interface Delta {
  role?: "assistant";
  content?: string;
  custom_content?: {
    attachments?: Attachment[];
    state?: Record<string, any>;
    stages?: Stage[];
  };
}
```

**Stage Updates:**
```json
{
  "custom_content": {
    "stages": [
      {
        "index": 0,
        "name": "🧭 Coordination",
        "status": "open"
      }
    ]
  }
}
```

```json
{
  "custom_content": {
    "stages": [
      {
        "index": 0,
        "content": "Routing to: **GPA**"
      }
    ]
  }
}
```

```json
{
  "custom_content": {
    "stages": [
      {
        "index": 0,
        "status": "completed"
      }
    ]
  }
}
```

### Non-Streaming Response

Complete response returned as single JSON object.

**Success Response (200 OK):**
```json
{
  "id": "chatcmpl-xyz",
  "object": "chat.completion",
  "created": 1704067200,
  "model": "mas-coordinator",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Complete response text...",
      "custom_content": {
        "state": {},
        "attachments": []
      }
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 200,
    "total_tokens": 300
  }
}
```

## Data Models

### CoordinationRequest

Pydantic model for LLM routing decisions.

```python
from enum import StrEnum
from typing import Optional
from pydantic import BaseModel, Field

class AgentName(StrEnum):
    GPA = "GPA"
    UMS = "UMS"

class CoordinationRequest(BaseModel):
    agent_name: AgentName = Field(
        description=(
            "Agent name. GPA (General-purpose Agent) is used for general tasks, "
            "web search, RAG, calculations with Python. "
            "UMS (Users Management Service agent) is used for user management."
        )
    )
    additional_instructions: Optional[str] = Field(
        default=None,
        description="**Optional**: Additional instructions to Agent."
    )
```

**JSON Schema (for LLM structured output):**
```json
{
  "type": "object",
  "properties": {
    "agent_name": {
      "type": "string",
      "enum": ["GPA", "UMS"],
      "description": "Agent name. GPA (General-purpose Agent)..."
    },
    "additional_instructions": {
      "type": "string",
      "description": "**Optional**: Additional instructions to Agent."
    }
  },
  "required": ["agent_name"]
}
```

**Example:**
```json
{
  "agent_name": "UMS",
  "additional_instructions": "Filter by active users only"
}
```

### Attachment

File attachment in messages.

```python
from typing import Literal
from pydantic import BaseModel

class Attachment(BaseModel):
    type: str  # MIME type: "image/png", "application/pdf", etc.
    title: Optional[str] = None
    data: Optional[str] = None  # Base64-encoded content
    url: Optional[str] = None   # Data URL or external URL
```

**Example:**
```json
{
  "type": "image/png",
  "title": "chart.png",
  "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
}
```

### Stage

Real-time progress indicator in UI.

```python
from typing import Optional, Literal

class Stage:
    index: int
    name: Optional[str]
    status: Literal["open", "completed"]
    content: Optional[str]
    attachments: Optional[list[Attachment]]
```

**Example Stage Lifecycle:**
```json
// Open stage
{"index": 0, "name": "🤖 GPA Agent", "status": "open"}

// Add content
{"index": 0, "content": "Searching the web..."}

// Complete stage
{"index": 0, "status": "completed"}
```

## Custom Content

### State Management

**GPA State** (stored in `custom_content.state`):
```json
{
  "is_gpa": true,
  "gpa_messages": {
    "tool_calls": [...],
    "tool_responses": [...]
  }
}
```

**UMS State**:
```json
{
  "ums_conversation_id": "conv-uuid-123"
}
```

**Accessing State in Code:**
```python
from aidial_sdk.chat_completion import Request

def get_state(request: Request):
    for message in request.messages:
        if message.custom_content and message.custom_content.state:
            return message.custom_content.state
    return None
```

### Attachments in Responses

**Generated Image (from GPA):**
```json
{
  "custom_content": {
    "attachments": [
      {
        "type": "image/png",
        "title": "generated_chart.png",
        "url": "data:image/png;base64,..."
      }
    ]
  }
}
```

**CSV Export (from Python interpreter):**
```json
{
  "custom_content": {
    "attachments": [
      {
        "type": "text/csv",
        "title": "results.csv",
        "data": "name,age\nJohn,30\nJane,25"
      }
    ]
  }
}
```

## Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid JSON or missing required fields |
| 401 | Unauthorized | Invalid or missing API key |
| 500 | Internal Error | LLM failure, agent timeout |
| 503 | Service Unavailable | Agent or MCP server down |

### Error Response Format

```json
{
  "error": {
    "message": "Invalid request: missing 'messages' field",
    "type": "invalid_request_error",
    "code": "invalid_request"
  }
}
```

**Common Errors:**

**Missing API Key:**
```json
{
  "error": {
    "message": "Missing Api-Key header",
    "type": "authentication_error"
  }
}
```

**Agent Timeout:**
```json
{
  "error": {
    "message": "Agent request timeout after 120 seconds",
    "type": "timeout_error"
  }
}
```

**LLM Failure:**
```json
{
  "error": {
    "message": "Upstream LLM error: Rate limit exceeded",
    "type": "upstream_error"
  }
}
```

## Code Interfaces

### MASCoordinator

Main orchestrator class.

**File**: [task/agent.py](../task/agent.py)

```python
class MASCoordinator:
    """
    Multi-Agent System Coordinator that routes user requests to specialized agents.
    """
    
    def __init__(
        self,
        endpoint: str,
        deployment_name: str,
        ums_agent_endpoint: str
    ):
        """
        Args:
            endpoint: DIAL Core endpoint for LLM calls
            deployment_name: LLM model deployment name (e.g., 'gpt-4o')
            ums_agent_endpoint: UMS Agent base URL
        """
        ...
    
    async def handle_request(
        self,
        choice: Choice,
        request: Request
    ) -> Message:
        """
        Main entry point - orchestrate the full request handling flow.
        
        Flow:
        1. Create AsyncDial client for LLM calls
        2. Open coordination stage and determine routing
        3. Delegate to appropriate agent
        4. Synthesize final response
        
        Args:
            choice: DIAL choice for streaming response
            request: User request with message history
            
        Returns:
            Final assistant message
        """
        ...
```

**Usage:**
```python
from task.agent import MASCoordinator
from aidial_sdk.chat_completion import Choice, Request

coordinator = MASCoordinator(
    endpoint="http://localhost:8080",
    deployment_name="gpt-4o",
    ums_agent_endpoint="http://localhost:8042"
)

await coordinator.handle_request(choice, request)
```

### GPAGateway

Gateway for GPA agent communication.

**File**: [task/coordination/gpa.py](../task/coordination/gpa.py)

```python
class GPAGateway:
    """
    Gateway for communicating with the General-Purpose Agent.
    Handles stage propagation, attachment forwarding, and tool call state restoration.
    """
    
    def __init__(self, endpoint: str):
        """
        Args:
            endpoint: DIAL Core endpoint URL (e.g., http://localhost:8080)
        """
        ...
    
    async def response(
        self,
        choice: Choice,
        stage: Stage,
        request: Request,
        additional_instructions: Optional[str]
    ) -> Message:
        """
        Send user request to GPA and stream the response with full DIAL feature support.
        
        Key Features:
        - Stage propagation: GPA's internal stages are mirrored to coordinator
        - Attachment forwarding: Images/files from GPA appear in coordinator response
        - State persistence: Tool call history preserved for multi-turn conversations
        
        Args:
            choice: DIAL choice for state storage and custom content
            stage: Parent stage to append content
            request: Original request with message history
            additional_instructions: Optional context from coordinator
            
        Returns:
            Assistant message with GPA's response content
        """
        ...
```

### UMSAgentGateway

Gateway for UMS agent communication.

**File**: [task/coordination/ums_agent.py](../task/coordination/ums_agent.py)

```python
class UMSAgentGateway:
    """
    Gateway for communicating with the UMS (Users Management Service) Agent.
    Handles conversation lifecycle and streaming responses.
    """
    
    def __init__(self, ums_agent_endpoint: str):
        """
        Args:
            ums_agent_endpoint: Base URL of UMS agent (e.g., http://localhost:8042)
        """
        ...
    
    async def response(
        self,
        choice: Choice,
        stage: Stage,
        request: Request,
        additional_instructions: Optional[str]
    ) -> Message:
        """
        Send user request to UMS Agent and stream the response.
        
        Flow:
        1. Retrieve or create UMS conversation (UMS tracks its own conversation state)
        2. Augment last user message with coordinator instructions
        3. Call UMS agent with streaming enabled
        4. Persist conversation ID for future requests
        
        Args:
            choice: DIAL choice to store state
            stage: Stage to append streamed content
            request: Original user request with message history
            additional_instructions: Optional context from coordinator
            
        Returns:
            Assistant message with UMS agent's response
        """
        ...
```

### StageProcessor

Utility for managing stage lifecycle.

**File**: [task/stage_util.py](../task/stage_util.py)

```python
class StageProcessor:
    
    @staticmethod
    def open_stage(choice: Choice, name: Optional[str] = None) -> Stage:
        """
        Create and open a new stage.
        
        Args:
            choice: DIAL choice to create stage in
            name: Display name for the stage
            
        Returns:
            Opened stage object
        """
        stage = choice.create_stage(name)
        stage.open()
        return stage
    
    @staticmethod
    def close_stage_safely(stage: Stage) -> None:
        """
        Safely close a stage, handling errors.
        
        Args:
            stage: Stage to close
        """
        try:
            if not stage._closed:
                stage.close()
        except Exception as e:
            print("⚠️ Unable to close stage.", e)
```

**Usage:**
```python
from task.stage_util import StageProcessor

# Open stage
stage = StageProcessor.open_stage(choice, "🧭 Coordination")

# Add content
stage.append_content("Routing to: **GPA**")

# Close stage
StageProcessor.close_stage_safely(stage)
```

## Advanced Usage

### Custom Agent Integration

To add a new agent:

1. Create gateway class in `task/coordination/`:
```python
class NewAgentGateway:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
    
    async def response(
        self,
        choice: Choice,
        stage: Stage,
        request: Request,
        additional_instructions: Optional[str]
    ) -> Message:
        # Implement agent communication
        ...
```

2. Update `AgentName` enum in [task/models.py](../task/models.py):
```python
class AgentName(StrEnum):
    GPA = "GPA"
    UMS = "UMS"
    NEWAGENT = "NEWAGENT"  # Add here
```

3. Update routing in [task/agent.py](../task/agent.py):
```python
elif coordination_request.agent_name == AgentName.NEWAGENT:
    gateway = NewAgentGateway(self.newagent_endpoint)
    return await gateway.response(choice, stage, request, ...)
```

4. Update coordination prompt in [task/prompts.py](../task/prompts.py).

---

**Related Documents**:
- [Architecture](architecture.md) - System design
- [Setup Guide](setup.md) - Installation instructions
- [Testing](testing.md) - Test procedures
