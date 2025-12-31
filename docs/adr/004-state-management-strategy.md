---
title: ADR 004 - Differentiated State Management Strategy
status: Accepted
date: 2025-12-31
---

# ADR 004: Differentiated State Management Strategy

## Status
**Accepted** - Implemented in v1.0.0

## Context

The MAS Coordinator needs to maintain conversation continuity across multi-turn interactions with both GPA and UMS agents. However, these agents have fundamentally different architectures:

### GPA Agent
- **Stateless service**: No server-side conversation storage
- **Tool-based**: Uses MCP tools (web search, Python interpreter, RAG)
- **State requirement**: Must restore tool call history for context
- **Format**: DIAL SDK's custom_content.state with tool calls/responses

### UMS Agent
- **Stateful service**: Maintains conversation history server-side
- **Conversation API**: Explicit conversation create/continue endpoints
- **State requirement**: Only needs conversation ID
- **Format**: Simple UUID string

A one-size-fits-all state management approach would be inefficient and complex.

## Decision

Implement **differentiated state management strategies** optimized for each agent's architecture.

### GPA State Strategy: State Restoration

**Storage Format:**
```python
{
    "is_gpa": True,          # Marker to identify GPA conversations
    "gpa_messages": {         # GPA's internal state
        "tool_calls": [...],  # Previous tool invocations
        "tool_responses": [...],  # Previous tool outputs
        # GPA-specific metadata
    }
}
```

**Workflow:**
1. **Outgoing (to GPA)**: Extract `gpa_messages` from coordinator state, restore to GPA format
2. **Incoming (from GPA)**: Wrap GPA state in `{is_gpa: True, gpa_messages: ...}`, store in coordinator

**Implementation** ([task/coordination/gpa.py](../../task/coordination/gpa.py)):
```python
def __prepare_gpa_messages(self, request, additional_instructions):
    res_messages = []
    
    # Filter history for GPA-related exchanges
    for idx, msg in enumerate(request.messages):
        if msg.role == Role.ASSISTANT and msg.custom_content:
            state = msg.custom_content.state
            if state and state.get(_IS_GPA):
                # Include preceding user message + this assistant message
                if idx > 0:
                    res_messages.append(messages[idx - 1].dict(exclude_none=True))
                
                # Restore GPA's expected state format
                msg_copy = deepcopy(msg)
                msg_copy.custom_content.state = state.get(_GPA_MESSAGES)
                res_messages.append(msg_copy.dict(exclude_none=True))
    
    # Add current user message
    res_messages.append(messages[-1].dict(exclude_none=True))
    return res_messages

# On response
choice.set_state({_IS_GPA: True, _GPA_MESSAGES: result_custom_content.state})
```

### UMS State Strategy: Conversation ID Tracking

**Storage Format:**
```python
{
    "ums_conversation_id": "uuid-string"  # Simple ID reference
}
```

**Workflow:**
1. **First request**: Create new conversation via `POST /conversations`, store ID
2. **Subsequent requests**: Extract ID from previous state, reuse for `POST /conversations/{id}/chat`

**Implementation** ([task/coordination/ums_agent.py](../../task/coordination/ums_agent.py)):
```python
def __get_ums_conversation_id(self, request):
    for message in request.messages:
        if message.role == Role.ASSISTANT and message.custom_content:
            state = message.custom_content.state
            if state and _UMS_CONVERSATION_ID in state:
                return state[_UMS_CONVERSATION_ID]
    return None

async def response(self, choice, stage, request, additional_instructions):
    # Get or create conversation
    conversation_id = self.__get_ums_conversation_id(request)
    if conversation_id is None:
        conversation_id = await self.__create_ums_conversation()
        choice.set_state({_UMS_CONVERSATION_ID: conversation_id})
    
    # Use conversation ID for all calls
    response_content = await self.__call_ums_agent(conversation_id, user_content, stage)
    return Message(role=Role.ASSISTANT, content=response_content)
```

## Consequences

### Positive

✅ **Efficiency**: Each strategy optimized for agent's needs  
✅ **Simplicity**: No unnecessary data stored  
✅ **Clarity**: State format clearly indicates agent type  
✅ **Performance**: UMS state is tiny (UUID only), GPA state only contains tool history  
✅ **Isolation**: State formats don't interfere with each other  

### Negative

⚠️ **No Cross-Agent Context**: GPA and UMS can't share conversation history  
⚠️ **Manual State Management**: Each gateway implements own logic  
⚠️ **State Key Collisions**: Must ensure `is_gpa` and `ums_conversation_id` don't conflict  

### Trade-offs

**Agent Isolation vs Context Sharing**: Chose isolation for simplicity (v1.0)  
**Complexity vs Optimization**: Per-agent strategies add complexity but improve efficiency

## State Size Analysis

### GPA State
**Initial**: ~500 bytes  
**After 5 tool calls**: ~5 KB  
**After 20 tool calls**: ~20 KB  

**Concern**: Can grow large with extensive tool usage  
**Mitigation** (future): Implement state compression/pruning

### UMS State
**Always**: ~50 bytes (UUID + wrapper)  

**No scaling issues**

## Example Multi-Turn Conversations

### GPA Multi-Turn (Code Execution)

**Turn 1:**
```
User: "Calculate fibonacci(10)"
→ GPA executes Python code
← State: {is_gpa: True, gpa_messages: {tool_calls: [python_run], ...}}
```

**Turn 2:**
```
User: "Now calculate fibonacci(20)"
→ Coordinator restores tool_calls from state
→ GPA has context of previous execution
← State updated with new tool call
```

### UMS Multi-Turn (User Management)

**Turn 1:**
```
User: "List users"
→ Create UMS conversation "conv-123"
← State: {ums_conversation_id: "conv-123"}
```

**Turn 2:**
```
User: "Delete the first user"
→ Continue conversation "conv-123"
← State: unchanged (same conversation)
```

### Mixed Conversation (Switching Agents)

**Turn 1:**
```
User: "List users"
→ Routes to UMS
← State: {ums_conversation_id: "conv-456"}
```

**Turn 2:**
```
User: "What's the weather in Paris?"
→ Routes to GPA (NEW conversation, no tool history)
← State: {is_gpa: True, gpa_messages: {...}}
```

**Result**: No shared context between agents (limitation accepted for v1.0)

## Implementation Notes

**State Constants:**
```python
# task/coordination/gpa.py
_IS_GPA = "is_gpa"
_GPA_MESSAGES = "gpa_messages"

# task/coordination/ums_agent.py
_UMS_CONVERSATION_ID = "ums_conversation_id"
```

**State Validation:**
Currently no validation beyond existence checks. Future: Pydantic models for state schemas.

**State Persistence:**
Managed by DIAL Core in Redis. Coordinator only reads/writes via `choice.set_state()` and `message.custom_content.state`.

## Future Enhancements (v2.0+)

### Cross-Agent Context Sharing
```python
# Store shared context separately
{
    "is_gpa": True,
    "gpa_messages": {...},
    "shared_context": {
        "last_mentioned_location": "Paris",
        "last_mentioned_user": "John"
    }
}
```

### State Compression
```python
# Prune old tool calls beyond N turns
def compress_gpa_state(state, keep_last_n=5):
    tool_calls = state["tool_calls"]
    if len(tool_calls) > keep_last_n:
        state["tool_calls"] = tool_calls[-keep_last_n:]
    return state
```

### State Schema Validation
```python
class GPAState(BaseModel):
    is_gpa: Literal[True]
    gpa_messages: dict

class UMSState(BaseModel):
    ums_conversation_id: str
```

## Alternatives Considered

### Alternative 1: Unified State Format

```python
{
    "current_agent": "GPA",
    "gpa_state": {...},
    "ums_state": {...},
    "shared_context": {...}
}
```

**Rejected because:**
- Unnecessarily complex for v1.0
- Most conversations use single agent
- Wastes space storing empty agent states
- Over-engineering for current requirements

### Alternative 2: Agent-Managed State

Let agents store state in their own databases, coordinator only tracks conversation IDs.

**Rejected because:**
- GPA is stateless by design
- Would require modifying GPA architecture
- Increases coupling between coordinator and agents
- DIAL SDK provides state management - use it

### Alternative 3: No State Management

Force users to provide full context in each message.

**Rejected because:**
- Terrible user experience
- Defeats purpose of multi-turn conversations
- Standard practice in AI chat applications

## Testing

**Test GPA State Restoration:**
```python
async def test_gpa_state_persistence():
    # Turn 1: Initial tool call
    response1 = await coordinator.handle_request(
        choice1, request1  # "Calculate 2+2"
    )
    state1 = choice1.get_state()
    assert state1["is_gpa"] == True
    assert "tool_calls" in state1["gpa_messages"]
    
    # Turn 2: Use saved state
    request2.messages.append(Message(
        role=Role.ASSISTANT,
        content=response1.content,
        custom_content=CustomContent(state=state1)
    ))
    request2.messages.append(Message(
        role=Role.USER,
        content="Now calculate 3+3"
    ))
    
    response2 = await coordinator.handle_request(choice2, request2)
    # GPA should have context from turn 1
```

**Test UMS Conversation Continuity:**
```python
async def test_ums_conversation_reuse():
    # Turn 1: Create conversation
    response1 = await coordinator.handle_request(
        choice1, request1  # "List users"
    )
    state1 = choice1.get_state()
    conv_id = state1["ums_conversation_id"]
    
    # Turn 2: Reuse conversation
    request2.messages.append(Message(
        role=Role.ASSISTANT,
        content=response1.content,
        custom_content=CustomContent(state=state1)
    ))
    request2.messages.append(Message(
        role=Role.USER,
        content="Delete first user"
    ))
    
    response2 = await coordinator.handle_request(choice2, request2)
    state2 = choice2.get_state()
    assert state2["ums_conversation_id"] == conv_id  # Same conversation
```

## Related Decisions

- [ADR-001: Gateway Pattern](001-gateway-pattern.md) - Gateways implement state strategies
- [ADR-005: Stage Mirroring](005-stage-mirroring.md) - Stage state is separate from conversation state

## References

- DIAL SDK - [CustomContent State](https://github.com/epam/ai-dial-sdk)
- [task/coordination/gpa.py](../../task/coordination/gpa.py) - GPA state implementation
- [task/coordination/ums_agent.py](../../task/coordination/ums_agent.py) - UMS state implementation

---

**Last Updated**: 2025-12-31  
**Contributors**: Architecture team
