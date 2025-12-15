# Mount Plans

**Mount plans are session-ready configurations** generated from profiles that amplifier-core can use to initialize sessions. This document explains what mount plans are, how they differ from profiles, and why they exist.

## Why Mount Plans Exist

**The problem:** amplifier-core needs concrete information to load modules:
- Module IDs for discovery/import
- Configuration dicts for initialization
- Filesystem paths for loading Python packages

**But profiles contain:**
- Git URLs (not paths)
- Declarative specifications (not execution instructions)
- Human-friendly references (not machine-ready data)

**The solution:** Mount plans are the **translation layer** between:
- **Profiles** (human-friendly templates)
- **amplifier-core** (execution engine)

**Think of it like:**
- **Profile** = Blueprint (what you want to build)
- **Mount plan** = Work order (how to build it)
- **Session** = Built structure (running system)

## What Mount Plans Contain

A mount plan is a **Python dict** with these sections:

### 1. Session Requirements (required)
```python
"session": {
  "orchestrator": {
    "module": "loop-streaming",      # Module identifier
    "source": "foundation/base",     # Profile hint for resolution
    "config": {...}                  # Module configuration
  },
  "context": {
    "module": "context-simple",
    "source": "foundation/base",
    "config": {...}
  }
}
```

### 2. Providers (at least one required)
```python
"providers": [
  {
    "module": "provider-anthropic",
    "source": "foundation/base",
    "config": {"default_model": "claude-sonnet-4-5"}
  }
]
```

### 3. Optional Resources
```python
"tools": [
  {"module": "tool-web", "source": "foundation/base", "config": {}},
  {"module": "tool-search", "source": "foundation/base", "config": {}}
],

"hooks": [
  {"module": "hooks-logging", "source": "foundation/base", "config": {...}},
  {"module": "hooks-redaction", "source": "foundation/base", "config": {...}}
],

"agents": {
  "code-expert": {
    "content": "You are an expert software engineer...",
    "metadata": {"source": "foundation/base:agents/code-expert.md"}
  }
}
```

## Key Design: Profile Hints

**The critical innovation:** Mount plans use **profile hints** instead of absolute paths.

### Instead of This (brittle):
```python
{
  "module": "provider-anthropic",
  "source": "/home/user/.amplifierd/share/profiles/foundation/base/providers/provider-anthropic"
  # Absolute path - breaks if share directory moves or on different system
}
```

### Mount Plans Use This (portable):
```python
{
  "module": "provider-anthropic",
  "source": "foundation/base"        # Profile hint - just collection/profile
}
```

### At Runtime (resolver translates):
```python
# DaemonModuleSourceResolver receives:
module_id = "provider-anthropic"
profile_hint = "foundation/base"

# Resolver translates to:
path = share_dir / "profiles" / "foundation" / "base" / "providers" / "provider-anthropic"

# Returns:
# /home/user/.amplifierd/share/profiles/foundation/base/providers/provider-anthropic
```

**Why this matters:**
- ✅ **Portable** - Mount plans work on any system
- ✅ **Relocatable** - Share directory can move without breaking mount plans
- ✅ **Cleaner** - Less redundant path information
- ✅ **Maintainable** - Path logic centralized in resolver

## Mount Plan Format

### Complete Example

```python
{
  # Session requirements (orchestrator + context)
  "session": {
    "orchestrator": {
      "module": "loop-streaming",           # Module identifier
      "source": "foundation/base",          # Profile hint (NOT absolute path)
      "config": {
        "extended_thinking": True,
        "max_iterations": 25
      }
    },
    "context": {
      "module": "context-simple",
      "source": "foundation/base",
      "config": {
        "max_tokens": 400000,
        "compact_threshold": 0.8,
        "auto_compact": True
      }
    }
  },

  # LLM providers (at least one required)
  "providers": [
    {
      "module": "provider-anthropic",
      "source": "foundation/base",
      "config": {
        "default_model": "claude-sonnet-4-5",
        "api_key": "${ANTHROPIC_API_KEY}"
      }
    }
  ],

  # Optional tools
  "tools": [
    {"module": "tool-web", "source": "foundation/base", "config": {}},
    {"module": "tool-search", "source": "foundation/base", "config": {}},
    {"module": "tool-task", "source": "foundation/base", "config": {}}
  ],

  # Optional hooks
  "hooks": [
    {
      "module": "hooks-logging",
      "source": "foundation/base",
      "config": {
        "mode": "session-only",
        "session_log_template": "~/.amplifier/projects/{project}/sessions/{session_id}/events.jsonl"
      }
    },
    {
      "module": "hooks-redaction",
      "source": "foundation/base",
      "config": {
        "allowlist": ["session_id", "turn_id", "span_id"]
      }
    }
  ],

  # Optional agents (embedded content)
  "agents": {
    "code-expert": {
      "content": "You are an expert software engineer with deep knowledge of...",
      "metadata": {
        "source": "foundation/base:agents/code-expert.md"
      }
    },
    "debug-helper": {
      "content": "You specialize in debugging complex issues...",
      "metadata": {
        "source": "foundation/base:agents/debug-helper.md"
      }
    }
  }
}
```

### Field Breakdown

**Every module reference has three parts:**

```python
{
  "module": "provider-anthropic",    # 1. Module identifier (what to load)
  "source": "foundation/base",       # 2. Profile hint (where to find it)
  "config": {...}                    # 3. Configuration (how to initialize)
}
```

**Agents are different** (they're embedded content, not modules):

```python
"agents": {
  "name": {
    "content": "Full agent markdown content here...",
    "metadata": {"source": "foundation/base:agents/name.md"}
  }
}
```

## Profiles vs. Mount Plans

### Profiles (human-friendly templates)

**Format:** Markdown + YAML frontmatter
**Contains:** Git URLs, declarative specs
**Purpose:** Reusable configuration templates
**Audience:** Developers, administrators
**Lifecycle:** Created manually, versioned in git

**Example:**
```yaml
---
providers:
- module: provider-anthropic
  source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
  config:
    default_model: claude-sonnet-4-5
---
```

### Mount Plans (execution-ready configs)

**Format:** Python dict
**Contains:** Module IDs, profile hints, embedded content
**Purpose:** Session initialization
**Audience:** amplifierd, amplifier-core
**Lifecycle:** Generated automatically from profiles

**Example:**
```python
{
  "providers": [
    {
      "module": "provider-anthropic",
      "source": "foundation/base",      # Profile hint, not git URL
      "config": {"default_model": "claude-sonnet-4-5"}
    }
  ]
}
```

### Key Differences

| Aspect | Profiles | Mount Plans |
|--------|----------|-------------|
| **Format** | Markdown + YAML | Python dict |
| **Sources** | Git URLs | Profile hints |
| **Agents** | URL references | Embedded content |
| **Context** | Git refs | Not included (loaded via @mentions) |
| **Purpose** | Define what you want | Ready for execution |
| **Lifecycle** | Created by humans | Generated by amplifierd |
| **Portability** | Git refs work anywhere | Profile hints work anywhere |

## When Mount Plans Are Generated

Mount plans are generated during **session creation**:

```python
# User requests session
POST /sessions
{
  "profile": "foundation/base",
  "message": "Help me debug this issue"
}

# amplifierd generates mount plan
mount_plan = mount_plan_service.generate_mount_plan("foundation/base")
# Returns: Dict with profile hints + module IDs + config

# amplifierd creates session with mount plan
session = amplifier.execute(config=mount_plan, message="...")
# amplifier-core uses resolver to translate hints → paths
```

**Generation flow:**
1. **Parse profile.md** - Read YAML frontmatter
2. **Load agents** - Read markdown files from `agents/` directory
3. **Transform structure** - Convert to dict format
4. **Add profile hints** - Set `"source": "collection/profile"`
5. **Embed agents** - Include full agent content
6. **Return dict** - Ready for amplifier-core

## How Modules Are Resolved

Mount plans contain profile hints, not paths. At runtime, `DaemonModuleSourceResolver` translates hints to paths.

### Resolution Algorithm

**Input:** Module ID + profile hint
```python
module_id = "provider-anthropic"
profile_hint = "foundation/base"
```

**Steps:**

1. **Extract context:**
   ```python
   collection = "foundation"
   profile = "base"
   ```

2. **Detect mount type** (from module ID):
   ```python
   # Pattern matching in module_id
   "provider-anthropic" → "providers/"  # Has "provider" in name
   "loop-streaming" → "orchestrator/"   # Has "loop" in name
   "tool-web" → "tools/"                # Has "tool" in name
   ```

3. **Build path:**
   ```python
   path = share_dir / "profiles" / collection / profile / mount_type / module_id
   # Example: .amplifierd/share/profiles/foundation/base/providers/provider-anthropic
   ```

4. **Return source:**
   ```python
   return ModuleSource(path=path, module_id=module_id)
   ```

**Output:** Path to directory containing Python package

### Mount Type Detection

The resolver guesses mount type from module ID naming conventions:

| Module ID Pattern | Mount Type | Example |
|------------------|------------|---------|
| `orchestrator-*` or `loop-*` | `orchestrator/` | `loop-streaming` |
| `context-*` | `context/` | `context-simple` |
| `provider-*` | `providers/` | `provider-anthropic` |
| `tool-*` | `tools/` | `tool-web` |
| `hooks-*` | `hooks/` | `hooks-logging` |

**This is why module naming conventions matter** - the resolver depends on predictable patterns.

## Directory Structure Contract

Mount plans work because of **consistent directory structure**:

```
.amplifierd/share/profiles/foundation/base/
  orchestrator/
    loop-streaming/                              ← Resolver returns this directory
      amplifier_module_loop_streaming/           ← Python package (what gets imported)
        __init__.py
        orchestrator.py

  context/
    context-simple/                              ← Resolver returns this directory
      amplifier_module_context_simple/           ← Python package
        __init__.py
        manager.py

  providers/
    provider-anthropic/                          ← Resolver returns this directory
      amplifier_module_provider_anthropic/       ← Python package
        __init__.py
        provider.py

  tools/
    tool-web/                                    ← Resolver returns this directory
      amplifier_module_tool_web/                 ← Python package
        __init__.py
        tool.py

  agents/
    code-expert.md                               ← Agent content (embedded in mount plan)
    debug-helper.md
```

**Key contract:**
- **Resolver returns:** Directory containing Python package
- **ModuleLoader expects:** Directory with `amplifier_module_{name}/` package inside
- **Import statement:** `import amplifier_module_loop_streaming`

## Integration with amplifier-core

### Session Creation Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. API REQUEST (to amplifierd)                                         │
│    POST /sessions {"profile": "foundation/base", "user_id": "user123"} │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. GENERATE MOUNT PLAN (amplifierd)                                    │
│    mount_plan_service.generate_mount_plan("foundation/base")            │
│    → Returns dict with profile hints + module IDs                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. MOUNT RESOLVER (amplifierd)                                         │
│    resolver = DaemonModuleSourceResolver(share_dir)                     │
│    Mount resolver in coordinator for amplifier-core to use              │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. CREATE SESSION (amplifier-core via amplifier_library)               │
│    session = AmplifierSession(config=mount_plan)                        │
│    amplifier-core's ModuleLoader uses mounted resolver automatically    │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. RESOLVE MODULES (amplifier-core calls resolver)                     │
│    For each module_id in mount_plan:                                    │
│      source = resolver.resolve(module_id, "foundation/base")            │
│      path = source.resolve()  # Get filesystem path                     │
│      # Add to sys.path and import                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. SESSION READY                                                        │
│    All modules loaded, session executing                                │
└─────────────────────────────────────────────────────────────────────────┘
```

### Code Example

**amplifierd (session creation):**
```python
from amplifierd.services.mount_plan_service import MountPlanService
from amplifierd.module_resolver import DaemonModuleSourceResolver
from amplifier_library import AmplifierSession

# Generate mount plan from profile
mount_plan_service = MountPlanService(share_dir=Path(".amplifierd/share"))
mount_plan = mount_plan_service.generate_mount_plan("foundation/base")
# Returns: {"session": {...}, "providers": [...], ...}

# Create resolver
resolver = DaemonModuleSourceResolver(share_dir=Path(".amplifierd/share"))

# Mount resolver in coordinator (amplifier-core will use it automatically)
coordinator.mount("module-source-resolver", resolver)

# Create session (amplifier-core uses mount plan + resolver)
session = AmplifierSession(config=mount_plan)
# Session ready - modules loaded and initialized
```

**amplifier-core (module loading):**
```python
# ModuleLoader sees mount plan entry:
module_spec = {
  "module": "provider-anthropic",
  "source": "foundation/base",    # Profile hint
  "config": {...}
}

# ModuleLoader uses mounted resolver automatically:
resolver = self.coordinator.get("module-source-resolver")
source = resolver.resolve("provider-anthropic", "foundation/base")
path = source.resolve()
# Returns: .amplifierd/share/profiles/foundation/base/providers/provider-anthropic

# Add to sys.path and import
sys.path.insert(0, str(path))
import amplifier_module_provider_anthropic
```

## Validation Rules

Mount plans are validated by amplifier-core when creating sessions:

### Required Fields

```python
# config dict must exist
if not config:
    raise ValueError("Config must not be empty")

# session.orchestrator must exist
if "orchestrator" not in config["session"]:
    raise ValueError("session.orchestrator is required")

# session.context must exist
if "context" not in config["session"]:
    raise ValueError("session.context is required")

# At least one provider required
if not config.get("providers"):
    raise RuntimeError("At least one provider must be configured")
```

### Optional Fields (with defaults)

```python
# These default to empty lists if missing
tools = config.get("tools", [])
hooks = config.get("hooks", [])
agents = config.get("agents", {})
```

### Module Loading Behavior

- **Orchestrator/context failure:** Fatal, raises RuntimeError
- **Provider/tool/hook failure:** Warning logged, continues loading other modules
- **Missing source:** Falls back to entry point resolution
- **Missing config:** Defaults to `{}`

## Common Use Cases

### 1. Standard Session
```python
# Simple mount plan for standard session
{
  "session": {
    "orchestrator": {"module": "loop-streaming", "source": "foundation/base", "config": {}},
    "context": {"module": "context-simple", "source": "foundation/base", "config": {}}
  },
  "providers": [
    {"module": "provider-anthropic", "source": "foundation/base", "config": {...}}
  ]
}
```

### 2. Rich Tooling
```python
# Mount plan with full tool suite
{
  "session": {...},
  "providers": [...],
  "tools": [
    {"module": "tool-web", "source": "foundation/base", "config": {}},
    {"module": "tool-search", "source": "foundation/base", "config": {}},
    {"module": "tool-task", "source": "foundation/base", "config": {}},
    {"module": "tool-todo", "source": "foundation/base", "config": {}}
  ]
}
```

### 3. Security Hooks
```python
# Mount plan with security features
{
  "session": {...},
  "providers": [...],
  "hooks": [
    {"module": "hooks-redaction", "source": "foundation/base", "config": {"allowlist": [...]}},
    {"module": "hooks-logging", "source": "foundation/base", "config": {"mode": "session-only"}},
    {"module": "hooks-approval", "source": "enterprise/secure", "config": {...}}
  ]
}
```

### 4. Specialized Agents
```python
# Mount plan with embedded agents
{
  "session": {...},
  "providers": [...],
  "agents": {
    "code-expert": {
      "content": "You are an expert software engineer...",
      "metadata": {"source": "foundation/base:agents/code-expert.md"}
    },
    "debug-helper": {
      "content": "You specialize in debugging...",
      "metadata": {"source": "foundation/base:agents/debug-helper.md"}
    }
  }
}
```

## Next Steps

Now that you understand mount plans:

1. **See the complete lifecycle:** [Profile Lifecycle](../04-advanced/profile-lifecycle.md)
2. **Explore module resolution:** Check `amplifierd/module_resolver.py`
3. **Review mount plan generation:** See `amplifierd/services/mount_plan_service.py`

## Key Takeaways

- **Mount plans bridge profiles and execution** - Translation layer
- **Profile hints replace absolute paths** - Portable, relocatable
- **Generated automatically from profiles** - Not hand-written
- **Resolver translates hints to paths** - Runtime path resolution
- **Consistent directory structure required** - Predictable layout
- **Python dicts, not files** - Passed directly to amplifier-core
- **Agents embedded, context loaded separately** - Different treatment
- **Module naming conventions matter** - Resolver depends on patterns
