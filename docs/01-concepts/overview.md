# Concepts Overview

This document explains **what amplifierd is**, **what problem it solves**, and **how the key concepts fit together**. After reading this, you'll understand why amplifierd exists and what it does.

## The Problem

Imagine you want to start an Amplifier session. You need to specify:
- An orchestrator module (the execution loop)
- A context manager module (message history)
- At least one LLM provider (Anthropic, OpenAI, etc.)
- Optional tools (web search, task delegation, etc.)
- Optional hooks (logging, redaction, UI streaming, etc.)
- Optional agents (specialized personas)

**Without amplifierd**, you'd need to:
1. Manually specify the filesystem path to each module
2. Repeat this configuration for every session
3. Update paths everywhere when modules move
4. Copy configurations between projects

**This is painful:**
- 🔴 **Repetitive** - Same paths/config copied everywhere
- 🔴 **Brittle** - Breaks when files move or repos change
- 🔴 **Not portable** - Paths differ across systems (Windows vs. Linux, different repo locations)
- 🔴 **Hard to maintain** - Updates require changing multiple files

**Example pain point:**
```python
# Manual configuration (brittle, repetitive)
config = {
  "session": {
    "orchestrator": {
      "module": "loop-streaming",
      "source": "/home/user/repos/amplifier-modules/loop-streaming",  # Absolute path
      "config": {"extended_thinking": True}
    },
    "context": {
      "module": "context-simple",
      "source": "/home/user/repos/amplifier-modules/context-simple",  # Absolute path
      "config": {"max_tokens": 400000}
    }
  },
  "providers": [
    {
      "module": "provider-anthropic",
      "source": "/home/user/repos/amplifier-modules/provider-anthropic",  # Absolute path
      "config": {"default_model": "claude-sonnet-4-5"}
    }
  ],
  # ... and this needs to be repeated for EVERY session
}
```

If you have 10 modules and 5 different session types, that's 50 path specifications to maintain!

## The Solution

**amplifierd** transforms how you configure Amplifier sessions:

```yaml
# Profile: foundation/base.md (reusable template)
---
session:
  orchestrator:
    module: loop-streaming
    source: git+https://github.com/payneio/amplifier-module-loop-streaming@main
    config:
      extended_thinking: true
  context:
    module: context-simple
    source: git+https://github.com/microsoft/amplifier-module-context-simple@main
    config:
      max_tokens: 400000

providers:
- module: provider-anthropic
  source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
  config:
    default_model: claude-sonnet-4-5
---
```

**Benefits:**
- ✅ **Declarative** - Say WHAT you want, not WHERE it lives
- ✅ **Reusable** - Define once, use many times
- ✅ **Portable** - Git refs work everywhere
- ✅ **Maintainable** - Update in one place
- ✅ **Shareable** - Profiles can be distributed via git

**To use it:**
```python
# Just reference the profile - amplifierd does the rest
response = amplifier.execute(
    profile="foundation/base",
    message="Help me debug this issue"
)
```

That's it! amplifierd:
1. Finds the profile definition
2. Resolves all git references
3. Organizes modules by type
4. Generates a mount plan
5. Provides paths to amplifier-core
6. Your session runs

## Key Concepts

amplifierd has three main concepts that work together:

### 1. Profiles - Session Templates

**Profiles** are reusable configurations that describe a complete session setup.

**A profile contains:**
- **Session requirements** - Orchestrator and context modules (required)
- **Providers** - LLM providers like Anthropic, OpenAI (at least one required)
- **Tools** - Optional capabilities (web search, task delegation)
- **Hooks** - Optional interceptors (logging, redaction, UI)
- **Agents** - Optional personas (code expert, debug helper)

**Profiles are written in Markdown with YAML frontmatter** - easy to read, easy to edit, easy to version control.

**Profiles live in collections:**
- Collections group related profiles (e.g., "foundation", "enterprise")
- Collections can be git repositories
- You reference profiles as `collection/profile` (e.g., `foundation/base`)

**Example structure:**
```
foundation collection:
  - base profile       (core functionality)
  - advanced profile   (extended features)
  - minimal profile    (lightweight setup)
```

👉 **Learn more:** [Profiles](./profiles.md)

### 2. Mount Plans - Session-Ready Configs

**Mount plans** are the bridge between profiles (human-friendly) and amplifier-core (execution engine).

**A mount plan contains:**
- **Module IDs** - Names like `loop-streaming`, `provider-anthropic`
- **Profile hints** - Context like `"source": "foundation/base"`
- **Configuration** - Settings for each module
- **Embedded content** - Agent definitions

**Mount plans are Python dicts**, not files. They're generated from profiles and passed directly to amplifier-core.

**Key difference from profiles:**
- **Profiles** = Templates (git refs, declarative, reusable)
- **Mount Plans** = Execution configs (module IDs, runtime-ready)

**Why "hints" instead of paths?**
- Mount plans contain `"source": "foundation/base"` (profile hint)
- NOT `"source": "/home/user/.amplifierd/share/profiles/foundation/base/..."`
- At runtime, `DaemonModuleSourceResolver` translates hints → paths
- This makes mount plans **portable** (work on any system)

**Example mount plan:**
```python
{
  "session": {
    "orchestrator": {
      "module": "loop-streaming",
      "source": "foundation/base",  # Profile hint, not absolute path
      "config": {"extended_thinking": True}
    }
  },
  "providers": [
    {"module": "provider-anthropic", "source": "foundation/base", "config": {...}}
  ]
}
```

👉 **Learn more:** [Mount Plans](./mount-plans.md)

### 3. Collections - Profile Repositories

**Collections** are named groups of profiles that can be shared and reused.

**Collections provide:**
- **Namespacing** - `foundation/base` vs `enterprise/base`
- **Versioning** - Git tags/branches control which version you use
- **Distribution** - Share profiles via git repositories
- **Organization** - Group related profiles together

**How collections work:**
1. Define collections in `.amplifierd/share/collections.yaml`
2. Reference git repositories (or local directories)
3. amplifierd clones/caches the collection content
4. Profiles become available as `collection/profile`

**Example collections.yaml:**
```yaml
collections:
  foundation:
    source: git+https://github.com/microsoft/amplifier-profiles@v1.0.0

  enterprise:
    source: git+https://github.com/myorg/amplifier-profiles@main

  local:
    source: file:///home/user/my-profiles
```

Now you can use:
- `foundation/base` - From Microsoft's profiles
- `enterprise/secure` - From your organization
- `local/experimental` - From your local development

## How It All Fits Together

**The complete flow:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. DEFINE PROFILES (collections.yaml + profile.md files)               │
│    • User creates/references collections in collections.yaml            │
│    • Profiles describe desired modules, config, agents                  │
│    • Git refs point to module sources                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. COMPILE PROFILES (amplifierd resolves and organizes)                │
│    • Clone git repositories to cache                                    │
│    • Resolve module sources (git refs → cached content)                │
│    • Organize by mount type (orchestrator/, providers/, tools/, etc.)  │
│    • Create profile.lock for change detection                          │
│    Output: .amplifierd/share/profiles/collection/profile/               │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. GENERATE MOUNT PLAN (amplifierd creates session config)             │
│    • Read profile.md YAML frontmatter                                   │
│    • Load embedded agents from agents/ directory                        │
│    • Generate dict with profile hints ("source": "collection/profile")  │
│    • Include all module configs                                         │
│    Output: Python dict ready for amplifier-core                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. RESOLVE MODULE PATHS (DaemonModuleSourceResolver)                   │
│    • Mount plan has: {"module": "loop-streaming", "source": "found/base"} │
│    • Resolver translates: "loop-streaming" + "found/base"               │
│      → .amplifierd/share/profiles/foundation/base/orchestrator/loop...  │
│    • Returns filesystem paths to amplifier-core                         │
│    Output: Absolute paths for module loading                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. INITIALIZE SESSION (amplifier-core loads and runs)                  │
│    • ModuleLoader adds paths to sys.path                                │
│    • Imports Python packages (amplifier_module_loop_streaming, etc.)    │
│    • Initializes orchestrator, context, providers, tools, hooks         │
│    • Session ready to execute                                           │
│    Output: Running Amplifier session                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key transformations:**
- **Profile** (git refs) → **Compiled directory** (organized modules)
- **Compiled directory** → **Mount plan** (dict with hints)
- **Mount plan** (hints) → **Resolved paths** (filesystem)
- **Resolved paths** → **Loaded modules** (running session)

## Why This Design?

**Separation of concerns:**
- **Profiles** = Human-friendly templates (what you want)
- **Mount plans** = Machine-ready configs (how to load it)
- **Resolver** = Bridge between profiles and execution (where to find it)

**Portability:**
- No absolute paths in profiles or mount plans
- Git refs work everywhere
- Resolver handles local filesystem differences

**Maintainability:**
- Define once, use many times
- Update profiles in one place
- Change detection via profile.lock

**Composability:**
- Profiles can extend other profiles
- Collections can reference external collections
- Modules can be mixed and matched

## Simple Mental Model

Think of amplifierd like **Docker Compose for Amplifier**:

**Docker Compose:**
```yaml
# docker-compose.yml
services:
  web:
    image: nginx:latest
    ports: ["80:80"]
```
↓ `docker-compose up`
→ Running container with nginx

**amplifierd:**
```yaml
# profile.md
session:
  orchestrator:
    module: loop-streaming
    source: git+https://github.com/.../loop-streaming@main
```
↓ `amplifier.execute(profile="foundation/base")`
→ Running session with loop-streaming

**Both provide:**
- Declarative configuration
- Automatic resolution
- Reusable templates
- Version control

## What's Next?

Now that you understand the big picture:

1. **Learn profile syntax:** [Profiles](./profiles.md)
   - YAML frontmatter structure
   - Module references
   - Configuration options

2. **Understand mount plans:** [Mount Plans](./mount-plans.md)
   - Generated format
   - Profile hints
   - Runtime resolution

3. **Deep dive (advanced):** [Profile Lifecycle](../04-advanced/profile-lifecycle.md)
   - Complete transformation flow
   - Directory structures
   - Change detection

## Key Takeaways

- **amplifierd solves configuration repetition** - Define once, use everywhere
- **Profiles are templates** - Declarative configs with git refs
- **Mount plans are execution configs** - Dict-based with profile hints
- **Collections enable sharing** - Git repos of reusable profiles
- **Resolver bridges the gap** - Translates hints to paths at runtime
- **It's like Docker Compose** - Declarative → compiled → running

Ready to dive deeper? Start with [Profiles](./profiles.md) to learn how to write your own.
