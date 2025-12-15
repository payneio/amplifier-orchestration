# amplifierd Documentation

**amplifierd** is the configuration and session management daemon for Amplifier. It transforms reusable profile templates into session-ready configurations that amplifier-core can execute.

## What is amplifierd?

amplifierd solves a fundamental problem: **configuring Amplifier sessions shouldn't require repeating the same module sources, settings, and agents every time.**

Instead of manually specifying every module path and configuration for each session, you:
1. Define reusable **profiles** that describe your desired setup
2. Let amplifierd resolve, compile, and prepare everything
3. Get ready-to-run sessions with all modules and configuration in place

**Think of it like Docker Compose for Amplifier sessions** - declarative configuration that gets compiled into runtime-ready artifacts.

## Quick Start

**If you're new to amplifierd:**
1. Start with [Concepts Overview](./01-concepts/overview.md) - understand the big picture
2. Read [Profiles](./01-concepts/profiles.md) - learn how to define configurations
3. Review [Mount Plans](./01-concepts/mount-plans.md) - see how profiles become sessions

**If you want deep technical details:**
- Jump to [Profile Lifecycle](./04-advanced/profile-lifecycle.md) - complete transformation flow

## Core Concepts

### Profiles
**Reusable session templates** that specify:
- Which modules to load (orchestrator, context, providers, tools, hooks)
- What configuration each module needs
- Which agents and context to include

Profiles live in collections and can reference external resources via git URLs.

### Mount Plans
**Session-ready configurations** generated from profiles:
- Module IDs with profile hints for path resolution
- Configuration dictionaries ready for amplifier-core
- Embedded agent content

Mount plans are the contract between amplifierd (profile-aware) and amplifier-core (path-aware).

### Collections
**Named groups of profiles** that can be:
- Stored in git repositories
- Referenced in `collections.yaml`
- Shared across projects and teams

## Architecture Overview

```
User Request → Profile Selection → Profile Compilation → Mount Plan Generation → Session Initialization
    ↓              ↓                     ↓                        ↓                      ↓
Profile ID    Load from cache    Resolve git refs      Generate dict config    amplifier-core loads modules
              (foundation/base)  Organize by type      Add profile hints       Execute session
```

**Key Flow:**
1. **Profile Definition** - Markdown files with YAML frontmatter specify desired configuration
2. **Compilation** - Git references resolved, modules organized, agents embedded
3. **Mount Plan** - Dict-based configuration with module IDs and profile hints
4. **Resolution** - `DaemonModuleSourceResolver` translates module IDs to filesystem paths
5. **Execution** - amplifier-core loads modules and runs session

## Why This Design?

**Problem:** Amplifier sessions need many modules (orchestrator, context, providers, tools, hooks). Specifying absolute paths is:
- **Repetitive** - Same paths copied everywhere
- **Brittle** - Breaks when files move
- **Not portable** - Paths differ across systems

**Solution:** amplifierd provides:
- **Declarative profiles** - Specify what you want, not where it lives
- **Automatic resolution** - Git refs → organized directories → resolved paths
- **Profile hints** - Mount plans contain `"source": "collection/profile"` instead of paths
- **Runtime resolution** - Resolver translates hints to paths when session starts

**Result:** Portable, maintainable, reusable session configurations.

## Documentation Structure

### Concepts (Start Here)
- [Overview](./01-concepts/overview.md) - High-level system explanation
- [Profiles](./01-concepts/profiles.md) - Profile structure and syntax
- [Mount Plans](./01-concepts/mount-plans.md) - Mount plan format and purpose

### Advanced Topics
- [Profile Lifecycle](./04-advanced/profile-lifecycle.md) - Complete transformation flow with diagrams

## Key Files

**In amplifierd codebase:**
- `amplifierd/services/mount_plan_service.py` - Generates mount plans from profiles
- `amplifierd/module_resolver.py` - Resolves module IDs to filesystem paths
- `amplifierd/services/profile_compilation.py` - Compiles profiles from collections
- `registry/profiles/` - Example profile definitions
- `.amplifierd/share/` - Compiled profiles and cached resources

**In user projects:**
- `.amplifierd/share/collections.yaml` - Collection references
- `.amplifierd/share/profiles/` - Compiled profile directories

## Example: foundation/base Profile

The `foundation/base` profile demonstrates the complete system:

**Profile Definition** (`registry/profiles/foundation/base.md`):
```yaml
---
session:
  orchestrator:
    module: loop-streaming
    source: git+https://github.com/payneio/amplifier-module-loop-streaming@main
  context:
    module: context-simple
    source: git+https://github.com/microsoft/amplifier-module-context-simple@main

providers:
- module: provider-anthropic
  source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
---
```

**Compiled Structure** (`.amplifierd/share/profiles/foundation/base/`):
```
orchestrator/loop-streaming/amplifier_module_loop_streaming/
context/context-simple/amplifier_module_context_simple/
providers/provider-anthropic/amplifier_module_provider_anthropic/
agents/explorer.md
```

**Mount Plan** (generated for session):
```python
{
  "session": {
    "orchestrator": {"module": "loop-streaming", "source": "foundation/base", "config": {...}},
    "context": {"module": "context-simple", "source": "foundation/base", "config": {...}}
  },
  "providers": [
    {"module": "provider-anthropic", "source": "foundation/base", "config": {...}}
  ],
  "agents": {
    "explorer": {"content": "...", "metadata": {"source": "foundation/base:agents/explorer.md"}}
  }
}
```

**At Runtime:**
- `DaemonModuleSourceResolver` sees `"source": "foundation/base"`
- Translates `"loop-streaming"` → `.amplifierd/share/profiles/foundation/base/orchestrator/loop-streaming`
- amplifier-core imports and executes the module

## Getting Help

- **Conceptual questions?** Start with [Concepts Overview](./01-concepts/overview.md)
- **Profile syntax?** See [Profiles](./01-concepts/profiles.md)
- **Mount plan format?** Check [Mount Plans](./01-concepts/mount-plans.md)
- **Deep technical details?** Read [Profile Lifecycle](./04-advanced/profile-lifecycle.md)
- **Code questions?** Review implementation in `amplifierd/services/` and `amplifierd/module_resolver.py`

## Philosophy

amplifierd follows Amplifier's core principles:
- **Ruthless simplicity** - Profile → mount plan → session (3 clear phases)
- **Self-contained modules** - Each module is a complete Python package
- **Contract-based design** - Profile hints + resolver = portable configurations
- **Testable components** - Resolver can be mocked, mount plans can be validated

The system is designed to be **transparent** (you can inspect every artifact), **predictable** (same profile always produces same mount plan), and **maintainable** (clear separation of concerns).
