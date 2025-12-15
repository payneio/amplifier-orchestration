# Foreman-Worker Orchestrator

**Purpose**: Specialized orchestrator implementing the foreman-worker pattern with hardcoded roles and minimal configuration.

## Contract

**Inputs**:
- Foreman profile (mount plan name)
- Worker configurations (profile + count)
- User messages

**Outputs**:
- Foreman responses to user messages
- Continuous background worker execution

**Side Effects**:
- Spawns background worker tasks
- Workers continuously claim and complete tasks
- All sessions write to workspace (tools, files, etc.)

## Architecture

### Pattern

```
User → Foreman (request-response)
           ↓
      Task Queue
           ↓
    Workers (continuous loops)
```

**Foreman**:
- Receives user messages
- Returns responses
- Manages work delegation

**Workers**:
- Run in infinite background loops
- Claim available tasks
- Complete work autonomously
- Sleep briefly between cycles

### No Workflow YAML

Unlike general-purpose orchestrators, this module **hardcodes the pattern**:
- No workflow definitions needed
- Pattern is built into the orchestrator
- Configuration is minimal (profiles + counts)

## Usage

```python
from amplifier_orchestrator_foreman_worker import (
    ForemanWorkerOrchestrator,
    WorkerConfig
)

# Configure workers
workers = [
    WorkerConfig(profile="coding-worker", count=2),
    WorkerConfig(profile="research-worker", count=1),
]

# Create orchestrator
async with ForemanWorkerOrchestrator(
    loader=module_loader,
    mount_plans_dir=Path("registry/profiles"),
    foreman_profile="foreman-profile",
    worker_configs=workers,
    workspace_root=Path("workspace")
) as orchestrator:
    # Send user messages to foreman
    response = await orchestrator.execute_user_message(
        "Build me a web scraper"
    )
    print(response)

    # Workers continue in background
    await asyncio.sleep(60)

# Automatic shutdown on exit
```

## Configuration

### Minimal Config

Only need:
- Foreman profile name
- Worker profile names + counts

No workflow YAML, no complex configuration!

### Worker Config

```python
@dataclass
class WorkerConfig:
    profile: str  # Mount plan name (e.g., "coding-worker")
    count: int    # Number of worker instances
```

## Mount Plans

Mount plans define agent capabilities:

**foreman-profile.json**:
```json
{
  "mounts": {
    "system_prompt": "You are the Foreman...",
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "tools": ["bash", "issue"]
  }
}
```

**coding-worker.json**:
```json
{
  "mounts": {
    "system_prompt": "You are a coding worker...",
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "tools": ["bash"]
  }
}
```

## Dependencies

```toml
dependencies = []  # Only amplifier-core (via parent)
```

No Pydantic, no YAML parsing - ruthlessly simple!

## Lifecycle

1. **Initialization**: Create orchestrator with profiles
2. **First Message**: Lazy initialization of foreman + workers
3. **Runtime**: Foreman handles messages, workers loop continuously
4. **Shutdown**: Signal workers, wait for completion, close sessions

## Error Handling

- Workers catch errors and retry after delay
- Foreman errors propagate to caller
- Shutdown ensures clean resource cleanup

## Performance

- Workers sleep 2s between cycles (configurable)
- Foreman responds immediately to user messages
- Background tasks don't block user interaction

## Comparison to Multi-Context

**Multi-Context Orchestrator**:
- General-purpose workflow executor
- YAML workflow definitions
- Complex state machines
- ~500 lines

**Foreman-Worker Orchestrator**:
- Purpose-built for one pattern
- No workflow files
- Simple background loops
- ~300 lines

Both are useful for different scenarios!

## Regeneration Specification

This module can be regenerated from this specification alone.

**Invariants**:
- ForemanWorkerOrchestrator public API
- WorkerConfig structure
- Context manager protocol
- execute_user_message signature
- Worker loop behavior
