# Multi-Worker Orchestration Demo

A demonstration of multi-agent coordination patterns using **real Amplifier Core sessions** and introducing the **Multi-Context Workflow Orchestrator** - a new orchestration pattern for managing multiple AI agents in coordinated workflows.

## What This Demo Shows

This project demonstrates two approaches to multi-agent orchestration:

1. **Manual Orchestration (`demo.py`)**: Traditional approach with explicit Python code managing multiple AmplifierSession instances
2. **Declarative Orchestration (`demo_orchestrated.py`)**: New approach using a workflow orchestrator with YAML-defined workflows

Both implement the same foreman-worker pattern:
- **Foreman Session**: Creates and monitors work queue of issues
- **Worker Sessions**: Multiple specialized workers process issues concurrently
- **Real Coordination**: Workers claim issues, complete work, and handle blocking

---

## The Multi-Context Workflow Orchestrator

### Concept

A **meta-orchestrator** - an Amplifier Core orchestrator that manages multiple execution contexts (each representing a different agent role) within coordinated workflows.

**Key Innovation:**
Instead of external scripts managing multiple AmplifierSession instances, the orchestrator creates lightweight execution contexts that:
- Share sessions per profile (one session for all "coding-worker" contexts)
- Maintain independent conversation histories
- Execute concurrently via asyncio
- Communicate through shared state (tools like issue management)

### Architecture

**Traditional Approach:**
```python
# External script orchestrates
async def main():
    async with AmplifierSession(foreman_config) as foreman:
        await foreman.execute("create issues")

    workers = [worker1(), worker2(), worker3()]
    await asyncio.gather(*workers)
```

**Multi-Context Approach:**
```python
# Orchestrator manages everything
orchestrator = MultiContextOrchestrator(loader, mount_plans_dir)
result = await orchestrator.execute_workflow(workflow)
# Workflow defined in YAML, orchestrator handles all coordination
```

### How It Works

**1. Workflow Definition (YAML)**
```yaml
phases:
  - name: "Issue Creation"
    execution_mode: "sequential"
    tasks:
      - context_name: "foreman"
        profile: "foreman"
        prompt: "Create issues..."

  - name: "Processing"
    execution_mode: "parallel"
    tasks:
      - context_name: "worker1"
        profile: "coding-worker"
        prompt: "Process coding issues..."
      - context_name: "worker2"
        profile: "coding-worker"
        prompt: "Process coding issues..."
```

**2. Orchestrator Execution**
- Loads workflow from YAML
- Creates ExecutionContext for each context (tracks history)
- Creates AmplifierSession for each unique profile (one per profile type)
- Executes phases sequentially
- Within phases, executes tasks (sequential or parallel per phase config)
- Cleans up all sessions when complete

**3. Session Pooling**
- `worker1` and `worker2` share the same `coding-worker` session
- Each has independent conversation history
- Reduces resource overhead (fewer LLM connections)

---

## Prerequisites

1. **Python 3.11+**
2. **Anthropic API Key**: Get from [console.anthropic.com](https://console.anthropic.com)
3. **Amplifier Dev Repository**: `/data/repos/msft/amplifier/amplifier-dev/` (for modules)

## Setup

### 1. Install Modules

```bash
python setup_modules.py
```

This creates symlinks in `modules/` with proper `amplifier-module-*` naming:
- `amplifier-module-provider-anthropic/`
- `amplifier-module-tool-bash/`
- `amplifier-module-tool-filesystem/`
- `amplifier-module-tool-issue/`
- `amplifier-module-tool-web/`
- `amplifier-module-loop-streaming/`
- `amplifier-module-context-persistent/`
- `amplifier-module-orchestrator-multi-context/` (NEW!)

### 2. Set API Key

```bash
export ANTHROPIC_API_KEY='sk-ant-api03-...'
```

Or create `.env`:
```bash
cp .env.example .env
# Edit .env with your API key
```

---

## Running the Demos

### Original Manual Demo

```bash
python demo.py
```

**What it does:**
- Explicitly creates AmplifierSession for each role
- Manually coordinates phases with asyncio
- Shows "traditional" multi-agent pattern

**Output:** Direct execution with explicit phase markers

### Multi-Context Orchestrated Demo

```bash
python demo_orchestrated.py
```

**What it does:**
- Loads workflow from `workflows/foreman_demo.yaml`
- Orchestrator manages all session creation and coordination
- Shows new declarative orchestration pattern

**Output:** Progress indicators, phase timing, task completion status

**Example output:**
```
======================================================================
📋 PHASE: Issue Processing
   Mode: PARALLEL
   Tasks: 3
======================================================================

  🔄 [coding_worker_1] Starting task with profile 'coding-worker'...
  🔄 [coding_worker_2] Starting task with profile 'coding-worker'...
  🔄 [research_worker_1] Starting task with profile 'research-worker'...
  ✅ [coding_worker_1] Task completed (3298 chars)
  ✅ [coding_worker_2] Task completed (3421 chars)
  ✅ [research_worker_1] Task completed (4102 chars)

  ⏱️  Phase 'Issue Processing' completed in 187.4s
```

---

## The Foreman-Worker Pattern

### Roles

**Foreman:**
- Creates work queue (issues)
- Monitors for blocked work
- Provides blocking information when needed
- Summarizes completed work

**Coding Workers (2 instances):**
- Claim coding issues from queue
- Execute coding tasks (fix bugs, add features)
- Can mark issues as blocked if information needed
- Use: filesystem, bash, issue tools

**Research Worker (1 instance):**
- Claim research issues from queue
- Conduct research tasks
- Use: web search, filesystem, issue tools

### Workflow Phases

1. **Issue Creation** - Foreman creates 4 demo issues
2. **Issue Processing** - 3 workers process in parallel
3. **Issue Monitoring** - Foreman checks for blocked issues and unblocks
4. **Process Unblocked** - Workers handle newly unblocked work
5. **Summary** - Foreman reports final status

---

## Multi-Context Orchestrator Module

**Location:** `modules/amplifier-module-orchestrator-multi-context/`

### Module Structure

```
amplifier-module-orchestrator-multi-context/
├── README.md                          # Module documentation
├── pyproject.toml                     # Dependencies
├── amplifier_orchestrator_multi_context/
│   ├── __init__.py                   # Public API
│   ├── orchestrator.py               # MultiContextOrchestrator class
│   ├── context.py                    # ExecutionContext class
│   ├── workflow.py                   # Pydantic workflow models
│   └── config.py                     # YAML loading
└── tests/
    ├── __init__.py
    └── fixtures/
        └── example_workflow.yaml     # Example workflow
```

### Key Classes

**ExecutionContext:**
- Manages conversation history for one context
- Auto-trims to prevent unbounded growth (max 50 messages)
- Tracks metadata about context execution

**MultiContextOrchestrator:**
- Executes workflows defined in YAML
- Manages session pool (one session per profile)
- Handles sequential and parallel phase execution
- Provides cleanup and error handling

**Workflow Models (Pydantic):**
- `Workflow` - Complete workflow definition
- `Phase` - Collection of tasks to execute
- `Task` - Single context execution with prompt

### Using the Orchestrator

**Basic Usage:**
```python
from amplifier_orchestrator_multi_context import (
    MultiContextOrchestrator,
    load_workflow
)
from amplifier_core import ModuleLoader

# Set up module loading
loader = ModuleLoader(search_paths=[Path("modules")])

# Load workflow
workflow = load_workflow("workflows/my_workflow.yaml")

# Create orchestrator
orchestrator = MultiContextOrchestrator(
    loader=loader,
    mount_plans_dir=Path("mount_plans")
)

# Execute workflow
try:
    result = await orchestrator.execute_workflow(workflow)
    print(f"Success! {result['successful_tasks']}/{result['total_tasks']} tasks completed")
finally:
    await orchestrator.cleanup()
```

**Workflow YAML:**
```yaml
name: "My Workflow"
description: "What this workflow does"
default_profile: "general"

phases:
  - name: "Phase 1"
    execution_mode: "sequential"  # or "parallel"
    tasks:
      - context_name: "my_context"
        profile: "my-profile"  # Maps to mount_plans/my-profile.json
        prompt: "Do something specific..."
```

---

## Use Cases for Multi-Context Orchestrator

### When to Use This Pattern

**Good for:**
- Multiple specialized agents working on shared problem
- Parallel processing of independent tasks
- Phased workflows (planning → execution → review)
- Reusable multi-agent patterns

**Examples:**
- **Code Review:** Multiple reviewers analyze different aspects concurrently
- **Research Synthesis:** Parallel research → synthesis → review
- **Content Creation:** Research → draft → edit → publish pipeline
- **Quality Assurance:** Multiple testers working on different test suites

### When NOT to Use

- Simple single-agent tasks (use normal orchestrator)
- Highly dynamic workflows with complex branching (use Python script)
- One-off ad-hoc automation (script is simpler)

---

## Configuration

### Mount Plans

Each profile needs a mount plan in `mount_plans/[profile-name].json`:

```json
{
  "session": {
    "orchestrator": {
      "module": "loop-streaming",
      "source": "local",
      "config": {}
    },
    "context": {
      "module": "context-persistent",
      "source": "local",
      "config": {}
    }
  },
  "providers": [
    {
      "module": "provider-anthropic",
      "source": "local",
      "config": {
        "default_model": "claude-sonnet-4-5"
      }
    }
  ],
  "tools": [
    {
      "module": "tool-issue",
      "source": "local",
      "config": {
        "data_dir": ".demo-workspace/.amplifier/issues",
        "auto_create_dir": true,
        "actor": "my-worker"
      }
    }
  ]
}
```

### Workflows

Define workflows in `workflows/`:

```yaml
name: "My Workflow"
description: "Brief description"
default_profile: "general"

phases:
  - name: "Planning"
    execution_mode: "sequential"
    tasks:
      - context_name: "planner"
        profile: "planning-agent"
        prompt: "Create a plan..."

  - name: "Execution"
    execution_mode: "parallel"
    tasks:
      - context_name: "executor1"
        profile: "worker"
        prompt: "Execute part 1..."
      - context_name: "executor2"
        profile: "worker"
        prompt: "Execute part 2..."
```

---

## Real Execution Results

From actual demo run (December 2025):

**Execution:** ~6.7 minutes (404 seconds)
**Tasks:** 8 total, 8 successful, 0 failed
**Sessions:** 3 created (foreman, coding-worker, research-worker)
**Contexts:** 4 used (foreman, coding_worker_1, coding_worker_2, research_worker_1)

**Real Work Performed:**
- Created 4 new issues
- Workers processed 21 total issues
- Completed 2 issues (closed)
- Researched competitor pricing models with full analysis
- Generated comprehensive summaries and reports

**Proof of Real Integration:**
- Actual Anthropic API calls made
- Real tool-issue operations (CRUD on issue database)
- Persistent JSONL database in `.demo-workspace/`
- Rate limits encountered (proves real API usage)

---

## Comparison: Manual vs. Declarative

| Aspect | demo.py (Manual) | demo_orchestrated.py (Declarative) |
|--------|------------------|-----------------------------------|
| **Code Length** | 235 lines | 150 lines + YAML |
| **Workflow Changes** | Edit Python code | Edit YAML file |
| **Reusability** | One-off script | Reusable orchestrator |
| **Flexibility** | Maximum (any Python) | Structured (YAML schema) |
| **Debugging** | Step through Python | Trace orchestrator logs |
| **Learning Curve** | Understand asyncio | Understand YAML schema |

**Both are valid!** Choose based on your needs.

---

## Extending the Demo

### Add More Worker Types

**1. Create mount plan:**
```bash
cp mount_plans/coding-worker.json mount_plans/testing-worker.json
# Edit tools to include test-specific tools
```

**2. Add to workflow:**
```yaml
- name: "Testing"
  execution_mode: "parallel"
  tasks:
    - context_name: "tester1"
      profile: "testing-worker"
      prompt: "Run test suites..."
```

### Create New Workflows

**1. Copy template:**
```bash
cp workflows/foreman_demo.yaml workflows/my_workflow.yaml
```

**2. Modify phases and tasks**

**3. Run:**
```bash
python demo_orchestrated.py  # If you update foreman_demo.yaml
# Or modify demo_orchestrated.py to load different workflow file
```

---

## Integration with Amplifier Core

### Using in Your Own Projects

The multi-context orchestrator can be used in any Amplifier Core project:

**1. Copy the module:**
```bash
cp -r modules/amplifier-module-orchestrator-multi-context /your/project/modules/
```

**2. Create mount plan with multi-context orchestrator:**
```json
{
  "session": {
    "orchestrator": {
      "module": "orchestrator-multi-context",
      "source": "local",
      "config": {
        "workflow_path": ".amplifier/workflows/my_workflow.yaml",
        "mount_plans_dir": ".amplifier/mount_plans"
      }
    }
  }
}
```

**3. Define your workflow:**
```yaml
# .amplifier/workflows/my_workflow.yaml
name: "My Multi-Agent Workflow"
phases:
  - name: "Planning"
    tasks: [...]
  - name: "Execution"
    tasks: [...]
```

**4. Run through Amplifier:**
```python
async with AmplifierSession(config, loader=loader) as session:
    result = await session.execute("Run my workflow")
```

The orchestrator will:
- Load the workflow YAML
- Create contexts for each agent role
- Execute phases in order
- Handle parallel execution within phases
- Return results

---

## Architecture Highlights

### Session vs. Context

**AmplifierSession:**
- Heavyweight (LLM connection, tool loading, orchestrator)
- Defined by mount plan configuration
- One per profile type

**ExecutionContext:**
- Lightweight (just conversation history)
- One per agent instance
- Multiple contexts can share one session

**Example:**
```
coding-worker session (AmplifierSession)
    ├── coding_worker_1 context (ExecutionContext)
    ├── coding_worker_2 context (ExecutionContext)
    └── coding_worker_3 context (ExecutionContext)

Each context has its own history but shares the session's tools and LLM configuration
```

### Execution Model

**Sequential Phases:**
```
Phase 1 → Phase 2 → Phase 3
```

**Parallel Tasks within Phase:**
```
Phase 2: [Worker1, Worker2, Worker3] all execute concurrently
```

**Hybrid:**
```
Phase 1 (sequential)
    → Phase 2 (parallel: 3 workers)
        → Phase 3 (sequential)
            → Phase 4 (parallel: 2 workers)
```

---

## Files Overview

### Core Demo Files

- **demo.py** - Original manual orchestration approach
- **demo_orchestrated.py** - New declarative orchestration approach
- **setup_modules.py** - Creates module symlinks
- **pyproject.toml** - Dependencies

### Configuration

- **mount_plans/** - AmplifierSession configurations per profile
  - `foreman.json` - Foreman agent (issue tool only)
  - `coding-worker.json` - Coding worker (filesystem, bash, issues)
  - `research-worker.json` - Research worker (web, filesystem, issues)

- **workflows/** - Declarative workflow definitions
  - `foreman_demo.yaml` - Complete 5-phase workflow

### Modules

- **modules/** - Amplifier Core modules (symlinks)
  - Standard modules from amplifier-dev
  - `amplifier-module-orchestrator-multi-context/` - Multi-context orchestrator (NEW!)

### Sample Work Files

- **login_auth.py** - Sample authentication code
- **password_reset.py** - Sample password reset feature
- **database_optimization.py** - Sample database optimization

### Documentation

- **ORCHESTRATOR_DEMO.md** - Detailed comparison and architecture
- **EXAMPLE_OUTPUT.md** - What the demo output looks like
- **README.md** - This file

---

## Troubleshooting

### Demo hangs with no output

**Cause:** Invalid or missing API key
**Fix:** Ensure `ANTHROPIC_API_KEY` is set to a valid key (starts with `sk-ant-api03-`)

```bash
# Check key
echo $ANTHROPIC_API_KEY

# Should show: sk-ant-api03-...
```

### "Module not found" errors

**Cause:** Module symlinks not created
**Fix:**
```bash
python setup_modules.py
```

### "tool-web not found" for research worker

**Cause:** tool-web module not symlinked
**Fix:** Research worker will gracefully degrade without web search, or add the module symlink

### Sessions don't clean up

**Cause:** Script interrupted before cleanup
**Fix:** The `finally` block should handle this, but you can manually kill Python processes if needed

---

## Performance Notes

**Expected execution time:** 4-7 minutes for full workflow

**Why?**
- Real LLM API calls (1-5 seconds each)
- Workers iterate through multiple issues (not just one)
- Comprehensive analysis and research in responses
- Tool calls for issue management (list, update, close)

**Parallelism helps:**
- Phase 2: 3 workers running concurrently
- Speedup: ~1.5-3x vs. sequential execution
- Still takes time due to iteration and API call overhead

---

## Key Learnings

### What This Demonstrates

1. **Multi-Agent Coordination** - Real agents working on shared problem
2. **Declarative Workflows** - YAML-defined coordination patterns
3. **Session Pooling** - Efficient resource sharing
4. **Context Isolation** - Independent conversation histories
5. **Parallel Execution** - Concurrent task processing
6. **Meta-Orchestration** - Orchestrator managing orchestrators

### Design Patterns

**Foreman-Worker:**
- One coordinator (foreman)
- Multiple executors (workers)
- Shared work queue (issues)
- Blocking/unblocking mechanism

**Map-Reduce:**
- Map: Workers process items in parallel
- Reduce: Foreman aggregates results

**Pipeline:**
- Sequential phases (planning → execution → review)
- Each phase can have parallel tasks

---

## Future Enhancements

### For the Orchestrator

- **Conditional branching** - Different phases based on results
- **Loop constructs** - Repeat phases until condition met
- **Cross-context communication** - Contexts passing data directly
- **Workflow persistence** - Save/resume long-running workflows
- **Dynamic workflows** - Modify workflow during execution

### For the Demo

- **More worker types** - Testing, documentation, security workers
- **Epic hierarchies** - Parent issues with subtasks
- **Priority queues** - High-priority work processed first
- **Dependency management** - Issues blocking other issues
- **Metrics dashboard** - Real-time workflow monitoring

---

## Learn More

**Amplifier Core:**
- [Amplifier Core Documentation](https://github.com/microsoft/amplifier-core)
- [Amplifier Module Development Guide](https://github.com/microsoft/amplifier-core/docs/modules.md)

**Related Projects:**
- [Max Payne Collection](https://github.com/payneio/max-payne-collection) - Issue management tool
- [Amplifier Collections](https://github.com/microsoft/amplifier-collections) - Reusable modules

**This Demo:**
- `ORCHESTRATOR_DEMO.md` - Detailed architecture and comparison
- `EXAMPLE_OUTPUT.md` - Example execution output with annotations
- `modules/amplifier-module-orchestrator-multi-context/README.md` - Module documentation

---

## License

MIT

---

## Contributing

This is an experimental demo. If you build on this pattern:

1. Share your workflows! (Submit as examples)
2. Report issues with the orchestrator
3. Suggest enhancements for common patterns
4. Document your use cases

---

**The multi-context workflow orchestrator represents a new pattern for declarative multi-agent coordination in Amplifier Core. Experiment with it and see what workflows you can create!**
