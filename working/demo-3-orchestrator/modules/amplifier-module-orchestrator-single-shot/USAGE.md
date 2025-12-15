# Single-Shot Orchestrator - Usage Guide

## Installation

The single-shot orchestrator is a registry module that can be referenced in mount plans.

## Mount Plan Configuration

### Basic Configuration

```yaml
# profile.yaml
orchestrator:
  module: registry/orchestrator/single-shot
  config: {}
```

### With Extended Thinking

```yaml
orchestrator:
  module: registry/orchestrator/single-shot
  config:
    extended_thinking: true
```

## Use Cases

### 1. Batch Processing Worker

```yaml
# worker-profile.yaml
name: batch-processor
description: Processes individual batch items with single-shot responses

orchestrator:
  module: registry/orchestrator/single-shot

context:
  module: amplifier-core/context/simple
  config:
    max_messages: 50

providers:
  - module: amplifier-core/providers/anthropic
    config:
      model: claude-3-5-sonnet-20241022

tools:
  - module: registry/tools/database
  - module: registry/tools/email
```

**Usage:**
```python
# Batch processor that handles one item at a time
for item in batch:
    response = await session.run(f"Process customer {item.id}")
    # Guaranteed: max 2 LLM calls, returns immediately
```

### 2. Scheduled Task Worker

```yaml
# daily-report.yaml
name: daily-report-generator
description: Generates daily report with single execution

orchestrator:
  module: registry/orchestrator/single-shot

tools:
  - module: registry/tools/analytics
  - module: registry/tools/file-write
```

**Usage:**
```python
# Scheduled at 6am daily
async def generate_daily_report():
    report = await session.run("Generate today's metrics report")
    # One cycle: query metrics, generate report, write file
    return report
```

### 3. Quick Query Responder

```yaml
# quick-query.yaml
name: quick-responder
description: Answers queries with single database lookup

orchestrator:
  module: registry/orchestrator/single-shot

tools:
  - module: registry/tools/search
  - module: registry/tools/database
```

**Usage:**
```python
# API endpoint for quick queries
@app.get("/query")
async def handle_query(q: str):
    answer = await session.run(q)
    # Fast, predictable response time
    return {"answer": answer}
```

## Behavior Guarantees

### Execution Flow

```
Input: "What's the status of order #1234?"

Step 1: LLM receives prompt
→ Returns tool call: database_query(order_id="1234")

Step 2: Execute tool
→ Returns: "Order #1234: Shipped, ETA Dec 15"

Step 3: LLM receives tool result
→ Returns: "Order #1234 has been shipped. Estimated arrival: December 15."

Output: Final text response
```

**Total LLM calls: 2**
**Total execution time: ~2-4 seconds**

### What It Does NOT Do

❌ Loop until task is "complete"
❌ Make multiple tool execution rounds
❌ Retry on errors
❌ Stream tokens
❌ Iterate adaptively

### What It DOES Do

✅ Execute exactly one cycle
✅ Handle tool calls (one round max)
✅ Return immediately after processing
✅ Emit proper events
✅ Add messages to context

## Performance Characteristics

### Predictable Timing

```python
# Without tools: 1 LLM call
start = time.time()
result = await session.run("Explain quantum computing")
elapsed = time.time() - start
# elapsed ≈ 2-3 seconds (single LLM latency)

# With tools: 2 LLM calls
start = time.time()
result = await session.run("Get user #1234's email")
elapsed = time.time() - start
# elapsed ≈ 4-6 seconds (2 × LLM latency + tool execution)
```

### Cost Control

```python
# Loop-based: Unknown cost
response = await loop_session.run("Build a website")
# Could make 10-50 LLM calls depending on complexity

# Single-shot: Bounded cost
response = await single_shot_session.run("Get website status")
# Always makes 1-2 LLM calls, no more
```

## Integration Examples

### With Autonomous Agent System

```python
class BatchWorker:
    def __init__(self):
        # Use single-shot for predictable per-item processing
        self.session = AmplifierSession(profile="registry/orchestrator/single-shot")

    async def process_item(self, item):
        """Process one item with bounded execution."""
        prompt = f"Process {item.type} item: {item.data}"
        result = await self.session.run(prompt)
        # Guaranteed: returns after one cycle
        return result

    async def process_batch(self, items):
        """Process batch with predictable total time."""
        results = []
        for item in items:
            result = await self.process_item(item)
            results.append(result)
        return results
```

### With Scheduled Tasks

```python
import schedule
import asyncio

async def daily_task():
    """Run daily with single-shot for reliability."""
    session = AmplifierSession(profile="daily-report")

    # Single execution, predictable outcome
    report = await session.run("Generate and email today's report")

    print(f"Daily report completed: {report[:100]}...")

# Schedule with confidence in execution time
schedule.every().day.at("06:00").do(lambda: asyncio.run(daily_task()))
```

### With API Endpoints

```python
from fastapi import FastAPI
from amplifier import AmplifierSession

app = FastAPI()
session = AmplifierSession(profile="quick-query")

@app.get("/query")
async def query_endpoint(q: str):
    """Fast, bounded query responses."""
    # Single-shot guarantees reasonable response time
    answer = await session.run(q)

    return {
        "query": q,
        "answer": answer,
        "execution": "single-shot"  # Client knows it's bounded
    }
```

## Comparison with Loop-Based

### When to Use Single-Shot

✅ Batch processing (predictable per-item time)
✅ Scheduled tasks (reliable execution)
✅ Quick queries (fast responses)
✅ Cost control (bounded LLM calls)
✅ Worker delegation (clear completion)

### When to Use Loop-Based

✅ Interactive chat (unknown steps needed)
✅ Complex tasks (adaptive workflow)
✅ Exploratory work (agent decides when done)
✅ Multi-step planning (iterative refinement)

## Summary

The single-shot orchestrator is designed for **autonomous systems** that need:
- **Predictable execution time**
- **Bounded resource usage**
- **Clear completion semantics**
- **Fast, focused responses**

It's the building block for workers, schedulers, and batch processors in the Amplifier ecosystem.
