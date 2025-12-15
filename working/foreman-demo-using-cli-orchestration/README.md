# Multi-Worker Orchestration Demo

A demonstration of multi-worker orchestration patterns using **real Amplifier Core sessions** and the actual issue management tool from max-payne-collection.

## What This Demo Shows

This demo demonstrates a practical multi-worker pattern where:

1. **Foreman Session**: Creates and monitors a work queue of issues
2. **Worker Sessions**: Multiple specialized workers process issues concurrently
3. **Real Coordination**: Workers claim issues, work on them, and report completion
4. **Blocked Issue Handling**: Foreman monitors for blocked issues and unblocks them

## Architecture

### Mount Plans

The demo uses three mount plan configurations:

**`foreman.json`**: Foreman with issue tool only
- Creates and monitors work queue
- Checks for blocked issues
- Unblocks issues when possible

**`coding-worker.json`**: Coding specialist with development tools
- Filesystem access for code changes
- Bash execution for commands
- Issue tool for work queue management

**`research-worker.json`**: Research specialist with investigation tools
- Web search capabilities
- Filesystem for documentation
- Issue tool for work queue management

### Real Amplifier Core Sessions

Each role runs in its own `AmplifierSession`:

```python
config = load_mount_plan("foreman")
async with AmplifierSession(config, workspace_dir=str(workspace)) as session:
    result = await session.execute(prompt)
```

The sessions use real Amplifier Core orchestration with:
- `loop-streaming` orchestrator
- `context-simple` for context management
- Real tool execution via MCP
- Actual Claude API calls

### Issue Management

Uses the real `tool-issue` from max-payne-collection:

- Issues stored in `.demo-workspace/.beads/` database
- Full CRUD operations (create, list, update, close)
- Rich metadata (assignee, priority, status, blocking_notes)
- Worker specialization via metadata filters

## Prerequisites

1. **Python 3.11+**
2. **Anthropic API Key**: Get one from [console.anthropic.com](https://console.anthropic.com)
3. **Amplifier Dev Repository**: Required at `/data/repos/msft/amplifier/amplifier-dev/`
   - The demo uses modules from this repository for API compatibility

## Setup

### 1. Install Modules

The demo requires modules from the amplifier-dev repository. These need to be set up with proper naming for Amplifier Core's module loader.

**First time setup**:
```bash
python setup_modules.py
```

This creates symlinks in `demo/modules/` with the proper `amplifier-module-*` naming convention that Amplifier Core expects:
- `amplifier-module-provider-anthropic/` → amplifier-dev/amplifier-module-provider-anthropic
- `amplifier-module-tool-bash/` → amplifier-dev/amplifier-module-tool-bash
- `amplifier-module-tool-filesystem/` → amplifier-dev/amplifier-module-tool-filesystem
- etc.

**What the setup does**:
- Creates `demo/modules/` directory
- Links to amplifier-dev modules (ensures API compatibility)
- Verifies all required modules are available

**Why amplifier-dev?**: The modules from amplifier-dev match the installed amplifier-core version, ensuring API compatibility.

### 2. Set API Key

```bash
export ANTHROPIC_API_KEY='your-key-here'
```

Or create a `.env` file:
```bash
cp .env.example .env
# Edit .env with your API key
```

### 3. Run Demo

```bash
python demo.py
```

## What Happens During the Demo

### Phase 1: Issue Creation (Foreman)
The foreman creates 5 issues:
1. Fix login authentication bug (coding, critical)
2. Add password reset feature (coding, high)
3. Research competitor pricing models (research, medium)
4. User onboarding flow analysis (research, medium)
5. Optimize database queries (coding, high, **blocked**)

### Phase 2: Parallel Processing (Workers)
Three workers start processing concurrently:
- **coding-worker-1**: Claims and works on coding issues
- **coding-worker-2**: Claims and works on coding issues
- **research-worker-1**: Claims and works on research issues

Each worker:
1. Lists ready issues using issue tool
2. Filters to their specialization
3. Claims an issue (sets assignee, status=in_progress)
4. Works on it (adds notes about approach)
5. Closes it when complete
6. Repeats until no more work

### Phase 3: Monitoring & Unblocking (Foreman)
After workers have time to process, foreman:
1. Checks for blocked issues
2. Finds the database optimization issue
3. Unblocks it with the required input
4. Lists all issues with current status

## Expected Output

```
======================================================================
  Multi-Worker Orchestration Demo
  Using REAL Amplifier Core Sessions
======================================================================

Workspace: /path/to/.demo-workspace
Running demo...

=== FOREMAN: Starting ===
Creating issues for the work queue...
[Foreman creates 5 issues using issue tool]
Issues created!

=== CODING-WORKER (coding-worker-1): Starting ===
coding-worker-1: Iteration 1
[Worker lists issues, finds coding issue, claims it, works on it]

=== CODING-WORKER (coding-worker-2): Starting ===
coding-worker-2: Iteration 1
[Worker lists issues, finds coding issue, claims it, works on it]

=== RESEARCH-WORKER (research-worker-1): Starting ===
research-worker-1: Iteration 1
[Worker lists issues, finds research issue, claims it, works on it]

=== FOREMAN: Checking blocked issues ===
[Foreman finds blocked issue, unblocks it, lists all issues]
Foreman check complete

======================================================================
Demo complete!
======================================================================
```

## Mount Plan Details

### Foreman Configuration
```json
{
  "session": {
    "orchestrator": "loop-streaming",
    "context": "context-simple"
  },
  "providers": [
    {
      "module": "provider-anthropic",
      "config": {
        "default_model": "claude-sonnet-4-5"
      }
    }
  ],
  "tools": [
    {
      "module": "tool-issue",
      "source": "max-payne-collection",
      "config": {}
    }
  ]
}
```

### Worker Configuration
Similar structure but with additional tools:
- `tool-filesystem`: For file operations
- `tool-bash`: For command execution (coding workers)
- `tool-web-search`: For research (research workers)
- `tool-issue`: For work queue management

## Real vs Simulated

**This demo uses REAL components**:

✅ Actual `AmplifierSession` from amplifier-core
✅ Real mount plan configurations
✅ Actual issue tool from max-payne-collection
✅ Real Claude API calls
✅ Actual file-based issue database
✅ Real concurrent session execution

**Not simulated**:
- Sessions create real Amplifier Core instances
- Tool calls execute actual operations
- Database changes persist to disk
- API usage counts against your quota

## Troubleshooting

### "Modules directory not found"
Run the setup script:
```bash
python setup_modules.py
```

This creates the `modules/` directory with properly named symlinks.

### "ANTHROPIC_API_KEY not set"
Set the environment variable:
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

### "Source not found" during setup
The setup script couldn't find max-payne-collection modules. Make sure:
1. amplifierd has been run at least once (to install collections)
2. The collection path is correct: `../amplifierd/.amplifierd/share/profiles/max-payne-collection/`

### Symlink creation fails on Windows
Windows requires either:
- Administrator privileges, or
- Developer Mode enabled in Windows Settings

Enable Developer Mode:
1. Open Settings → Update & Security → For Developers
2. Enable "Developer Mode"
3. Restart and run `python setup_modules.py` again

### "ModuleNotFoundError: No module named 'amplifier_module_*'"
This means the module loader can't find the modules. Verify:
1. `demo/modules/` directory exists
2. It contains symlinks with `amplifier-module-*` naming
3. Symlinks point to valid collection directories

### Sessions hang or timeout
- Check API key is valid
- Verify network connectivity
- Check Anthropic API status
- Increase timeout in mount plans if needed

### Workers don't find issues
- Verify issue creation succeeded (check foreman output)
- Check `.demo-workspace/.beads/` directory exists
- Ensure workers are filtering correctly on worker_type metadata

### Issue tool errors
- Ensure max-payne-collection is installed in amplifier-core
- Check that collection path is accessible
- Verify workspace directory permissions

## Extending the Demo

### Add More Workers
Create additional worker tasks:
```python
asyncio.create_task(worker_session("coding-worker-3", "coding", workspace))
```

### Different Worker Types
Create new mount plans for specialized workers:
- Testing worker (runs tests)
- Documentation worker (writes docs)
- Security worker (security audits)

### Custom Issue Workflows
Modify foreman prompts to:
- Set up dependencies between issues
- Create epics with sub-issues
- Implement priority queues
- Add time estimates

### Integration with Real Work
Point workspace at actual project directory:
```python
workspace = Path("/path/to/real/project")
```

## Learn More

- [Amplifier Core Documentation](https://github.com/microsoft/amplifier-core)
- [Max Payne Collection](https://github.com/payneio/max-payne-collection)
- [Multi-Worker Patterns](../docs/multi-worker-patterns.md)

## License

MIT
