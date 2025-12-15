# Single-Shot vs Loop Orchestrators

## Architectural Comparison

### Loop-Streaming (742 lines)
```python
while self.max_iterations == -1 or iteration < self.max_iterations:
    iteration += 1
    response = await provider.complete(chat_request)

    if tool_calls:
        # Execute tools
        # Continue loop for next iteration
        continue
    else:
        # Got final response
        break
```

**Characteristics:**
- Loops until LLM stops requesting tools
- Unlimited iterations by default
- Streaming token-by-token output
- Complex state management across iterations

### Loop-Basic (516 lines)
```python
while self.max_iterations == -1 or iteration < self.max_iterations:
    response = await provider.complete(chat_request)

    if tool_calls:
        await execute_tools()
        iteration += 1
        continue

    if content:
        break
```

**Characteristics:**
- Loops until final content received
- Unlimited iterations by default
- Non-streaming output
- Simpler than streaming but still loops

### Single-Shot (222 lines) ⭐
```python
# First call
response = await provider.complete(chat_request)

if tool_calls:
    await execute_tools()
    # Second call with results
    response = await provider.complete(chat_request)

return response.text
```

**Characteristics:**
- **NO LOOPS** - executes once and returns
- **Maximum 2 LLM calls** - initial + optional follow-up
- **Predictable execution** - always returns after one cycle
- **Ideal for workers** - bounded, deterministic behavior

## Execution Flow Comparison

### Interactive Chat (Loop-Streaming)
```
User: "Build a website"
→ LLM: [requests file_write tool]
→ Execute: write index.html
→ LLM: [requests file_write tool]
→ Execute: write styles.css
→ LLM: [requests file_write tool]
→ Execute: write script.js
→ LLM: "Done! Created 3 files."
(4 LLM calls, 3 tool executions)
```

### Autonomous Worker (Single-Shot)
```
System: "Process this batch item"
→ LLM: [requests database_query tool]
→ Execute: query_customer_data
→ LLM: "Customer #1234: Active, expires 2025-06"
(2 LLM calls, 1 tool execution, DONE)
```

## When to Use Each

### Loop-Based Orchestrators
✅ Interactive chat sessions
✅ Complex multi-step tasks
✅ User can guide the process
✅ Unknown number of steps needed

### Single-Shot Orchestrator
✅ Autonomous batch processing
✅ Scheduled/reactive workflows
✅ Predictable execution time needed
✅ One-query-one-response pattern
✅ Worker/agent delegation
✅ Cost control (bounded LLM calls)

## Code Complexity Metrics

| Metric | Loop-Streaming | Loop-Basic | Single-Shot |
|--------|---------------|------------|-------------|
| Total Lines | 742 | 516 | 222 |
| Core Logic | ~200 | ~150 | ~100 |
| Max LLM Calls | Unlimited | Unlimited | **2** |
| While Loops | 1 | 1 | **0** |
| Iteration Tracking | Yes | Yes | **No** |
| Max Iteration Handling | Yes | Yes | **No** |

## Implementation Highlights

### What Single-Shot Removes
❌ While loops
❌ Iteration counters
❌ Max iteration checks
❌ "Until done" logic
❌ Streaming token management
❌ Complex state across iterations

### What Single-Shot Keeps
✅ Tool execution (parallel)
✅ Hook emissions
✅ Context management
✅ Provider selection
✅ Error handling
✅ Event system integration

## Real-World Use Cases

### Loop-Based: "Build me a calculator app"
The LLM needs multiple iterations to:
1. Create HTML structure
2. Add CSS styling
3. Implement JavaScript logic
4. Test and fix bugs
5. Add final touches

**Total**: 10-20 LLM calls, adaptive workflow

### Single-Shot: "Get customer status for ID 1234"
The worker needs bounded execution:
1. Query database for customer
2. Return formatted status

**Total**: 1-2 LLM calls, predictable workflow

## Performance Characteristics

### Loop-Based
- Time: Variable (depends on task complexity)
- Cost: Variable (unbounded LLM calls)
- Predictability: Low (unknown iterations)

### Single-Shot
- Time: **Predictable** (~2 LLM call latencies)
- Cost: **Bounded** (max 2 LLM calls)
- Predictability: **High** (always 1-2 calls)

## Summary

**Single-shot is intentionally minimal** - it does exactly one thing (one cycle) and nothing more. This makes it:
- Easy to reason about
- Predictable in execution
- Cost-effective for batch work
- Perfect for autonomous systems

For interactive agentic workflows where the number of steps is unknown, use loop-based orchestrators. For autonomous workers with bounded tasks, use single-shot.
