# Single-Shot Orchestrator

Minimal orchestrator that executes exactly ONE LLM interaction cycle and returns immediately.

## Purpose

Workers and autonomous systems need an orchestrator that:
- Executes ONE prompt-response cycle
- Does NOT loop until "done"
- Returns immediately after processing
- Maximum 2 LLM calls total

## Key Difference from Loop-Based Orchestrators

| Orchestrator | Behavior | Use Case |
|--------------|----------|----------|
| loop-streaming | `while not done: call_llm()` | Interactive chat sessions |
| loop-basic | `while not done: call_llm()` | Standard agentic workflows |
| **single-shot** | `call_llm(); return` | **Autonomous workers** |

## Flow

1. Take prompt
2. Call LLM once
3. If LLM requests tools:
   - Execute all tools in parallel
   - Make ONE follow-up LLM call with results
4. Return final text response
5. **Total: Maximum 2 LLM calls**

## Configuration

```yaml
orchestrator:
  module: registry/orchestrator/single-shot
  config:
    extended_thinking: false  # Optional: enable extended thinking
```

## Contract

### Input
- `prompt`: User's input text
- `context`: Message history
- `providers`: Available LLM providers
- `tools`: Available tool functions
- `hooks`: Event system
- `coordinator`: Module coordinator

### Output
- `str`: Final text response from LLM

### Side Effects
- Adds messages to context (user, assistant, tool)
- Emits events: PROMPT_SUBMIT, PROVIDER_REQUEST, TOOL_PRE, TOOL_POST, ORCHESTRATOR_COMPLETE

## Implementation Notes

**Total lines**: ~200 (including comments)

**No loops**: The code contains ZERO while/for loops for orchestration logic
**No retry logic**: Errors are returned as error messages
**No "until done"**: Executes exactly once and returns

This is intentionally the simplest possible orchestrator - a building block for autonomous systems that need predictable, bounded execution.
