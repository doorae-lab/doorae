# Task 4: Manual CLI Test Results

**Date:** 2026-01-31
**Test Command:** `uv run thetable -m "회의를 시작합니다"`

## Result: FAILED ❌

The `ValueError: Found AIMessages with tool_calls that do not have a corresponding ToolMessage` error **still occurs**.

## Error Analysis

### Root Cause Identified

The wrapper pattern we implemented in `agent_factory.py` is **fundamentally flawed**:

```python
def supervisor_wrapper(state):
    """Wrapper that invokes internal supervisor subgraph"""
    result = internal_supervisor.invoke(state)
    return result

supervisor_wrapper.name = profile.name
return supervisor_wrapper
```

**Why this fails:**

1. **langgraph-supervisor** expects agents to be `Pregel` objects (compiled graphs)
2. When a nested supervisor (e.g., PM) finishes its work, it calls `transfer_back_to_coordinator` tool
3. This creates an AIMessage with a tool_call that needs to be handled by the parent supervisor
4. By wrapping the compiled supervisor in a plain Python function, we lose all the special handling that `langgraph-supervisor` provides for:
   - Handoff tools (`transfer_to_*`)
   - Handback tools (`transfer_back_to_*`)
   - Tool message generation
   - State management

### The Error in Detail

```
ValueError: Found AIMessages with tool_calls that do not have a corresponding ToolMessage.
Here are the first few of those tool calls: [
    {
        'name': 'transfer_back_to_coordinator',
        'args': {},
        'id': 'tool_transfer_back_to_coordinator_uBAjj1Db0ZCJx9rLdOIO',
        'type': 'tool_call'
    }
]
```

This happens because:
1. PM supervisor finishes its subtask
2. PM calls `transfer_back_to_coordinator` (auto-generated tool)
3. The call creates an AIMessage with tool_calls
4. Our wrapper function just returns the state without handling this tool call
5. When Coordinator tries to process the next message, it finds an AIMessage with unresolved tool_calls
6. LangGraph validation fails

## The Correct Solution

**We should NOT wrap nested supervisors in functions.** Instead, we should:

1. Pass **compiled supervisor graphs directly** to `create_supervisor()`
2. Let `langgraph-supervisor` handle all the handoff/handback logic internally
3. This means we cannot use the same `create_supervisor()` API for nested supervisors

## Next Steps

We need to revise our approach. Possible solutions:

### Option A: Flat Structure (Recommended)
- Remove all supervisor nesting from YAML
- Make Host, PM, TechLead all leaf agents
- Let Coordinator handle all routing
- **Pros:** Simple, works with langgraph-supervisor
- **Cons:** Less hierarchical structure

### Option B: Direct Compiled Graph Passing
- Don't wrap nested supervisors
- Pass compiled graphs directly to parent supervisor
- **Pros:** Maintains hierarchy
- **Cons:** Needs investigation if langgraph-supervisor supports this

### Option C: Custom Supervisor Implementation
- Implement our own supervisor logic
- Don't use langgraph-supervisor for nested cases
- **Pros:** Full control
- **Cons:** More complex, reinventing the wheel

## Recommendation

**Go with Option A (Flat Structure)** because:
1. It's the simplest and most reliable
2. langgraph-supervisor is designed for flat structures
3. We can still maintain logical grouping through prompts
4. Host can delegate to PM/TechLead through Coordinator

This aligns with the supervisor pattern's intended use case.
