---
title: ADR 001 - Gateway Pattern for Agent Communication
status: Accepted
date: 2025-12-31
---

# ADR 001: Gateway Pattern for Agent Communication

## Status
**Accepted** - Implemented in v1.0.0

## Context

The MAS Coordinator needs to communicate with multiple heterogeneous agents:
- **GPA Agent**: DIAL-compatible, supports streaming, stage propagation, tool state
- **UMS Agent**: Custom API, conversation-based, different streaming format

Each agent has unique requirements:
- Different authentication mechanisms
- Different message formats
- Different state management strategies
- Different streaming protocols

The coordinator must isolate these differences while providing a consistent interface for the orchestration layer.

## Decision

We will use the **Gateway Pattern** to encapsulate agent-specific communication logic.

### Implementation

Create a gateway class for each agent:

```python
class GPAGateway:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
    
    async def response(
        self,
        choice: Choice,
        stage: Stage,
        request: Request,
        additional_instructions: Optional[str]
    ) -> Message:
        # GPA-specific logic:
        # - Filter message history
        # - Restore tool state
        # - Stream via AsyncDial
        # - Mirror stages
        # - Forward attachments
        ...

class UMSAgentGateway:
    def __init__(self, ums_agent_endpoint: str):
        self.ums_agent_endpoint = ums_agent_endpoint
    
    async def response(
        self,
        choice: Choice,
        stage: Stage,
        request: Request,
        additional_instructions: Optional[str]
    ) -> Message:
        # UMS-specific logic:
        # - Manage conversation lifecycle
        # - Parse SSE format
        # - Track conversation ID
        ...
```

### Key Principles

1. **Uniform Interface**: All gateways expose the same `response()` signature
2. **Encapsulation**: Agent-specific details hidden from coordinator
3. **Single Responsibility**: Each gateway handles one agent only
4. **Extensibility**: New agents added by creating new gateway classes

## Consequences

### Positive

✅ **Clean Separation**: Coordinator logic decoupled from agent protocols  
✅ **Easy Testing**: Gateways testable in isolation with mocked agents  
✅ **Maintainability**: Agent changes don't ripple through coordinator  
✅ **Extensibility**: Adding new agents is straightforward  
✅ **Code Readability**: Clear boundaries between orchestration and integration  

### Negative

⚠️ **Additional Abstraction**: One more layer in the call stack  
⚠️ **Duplication**: Some streaming logic duplicated across gateways  
⚠️ **Complexity**: Gateway pattern may be overkill for simple agents  

### Trade-offs

- **Flexibility vs Simplicity**: Chose flexibility to handle heterogeneous agents
- **Abstraction vs Performance**: Minor overhead acceptable for maintainability

## Alternatives Considered

### Alternative 1: Direct Agent Calls in Coordinator

```python
class MASCoordinator:
    async def handle_request(self, ...):
        if agent_name == "GPA":
            # GPA-specific code inline
            client = AsyncDial(...)
            stream = await client.chat.completions.create(...)
            # ...100 lines of GPA logic...
        elif agent_name == "UMS":
            # UMS-specific code inline
            async with httpx.AsyncClient() as client:
                response = await client.post(...)
            # ...100 lines of UMS logic...
```

**Rejected because:**
- Coordinator becomes a monolith
- Hard to test individual agents
- Violates Single Responsibility Principle

### Alternative 2: Abstract Base Class

```python
from abc import ABC, abstractmethod

class AgentGateway(ABC):
    @abstractmethod
    async def response(self, ...) -> Message:
        pass
```

**Rejected because:**
- Python's duck typing makes ABC unnecessary
- Interface already clear from method signature
- ABC adds boilerplate without benefit

### Alternative 3: Plugin System with Registry

```python
agent_registry = {
    "GPA": GPAGateway,
    "UMS": UMSAgentGateway
}

gateway_class = agent_registry[agent_name]
gateway = gateway_class(...)
```

**Considered but deferred:**
- Overkill for 2 agents
- Could be added later if agents become numerous
- Current if/elif is explicit and readable

## Implementation Notes

**File Locations:**
- [task/coordination/gpa.py](../../task/coordination/gpa.py) - GPA gateway
- [task/coordination/ums_agent.py](../../task/coordination/ums_agent.py) - UMS gateway
- [task/agent.py](../../task/agent.py) - Gateway usage in coordinator

**Key Methods:**
- `GPAGateway.__prepare_gpa_messages()` - Message history filtering
- `UMSAgentGateway.__get_ums_conversation_id()` - State extraction
- `UMSAgentGateway.__create_ums_conversation()` - Conversation init

## Related Decisions

- [ADR-002: Three-Stage Orchestration](002-three-stage-orchestration.md) - How gateways fit in flow
- [ADR-004: State Management Strategy](004-state-management-strategy.md) - Gateway state responsibilities

## References

- Martin Fowler - [Gateway Pattern](https://martinfowler.com/eaaCatalog/gateway.html)
- DIAL SDK - [ChatCompletion Interface](https://github.com/epam/ai-dial-sdk)

---

**Last Updated**: 2025-12-31  
**Contributors**: Architecture team
