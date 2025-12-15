# Profiles

**Profiles are reusable session templates** that describe what modules to load, how to configure them, and what agents/context to include. This document explains how to write and use profiles.

## What Profiles Contain

A complete profile specifies:

1. **Session requirements** (required)
   - **Orchestrator** - The execution loop (one required)
   - **Context** - Message history manager (one required)

2. **Providers** (at least one required)
   - LLM providers (Anthropic, OpenAI, Azure, Ollama, etc.)

3. **Optional resources**
   - **Tools** - Capabilities like web search, task delegation
   - **Hooks** - Interceptors for logging, redaction, UI streaming
   - **Agents** - Specialized personas
   - **Context directories** - Runtime-injected documentation

4. **Configuration**
   - Settings for each module
   - Session-level parameters
   - UI preferences

**Minimum viable profile:**
```yaml
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
```

This is the bare minimum - orchestrator, context, and one provider.

## Profile Structure

Profiles are **Markdown files with YAML frontmatter**.

**Format:**
```markdown
---
profile:
  name: base
  version: 1.1.0
  description: Base configuration with core functionality
  schema_version: 2

session:
  orchestrator:
    module: loop-streaming
    source: git+https://github.com/org/modules@main
    config:
      extended_thinking: true
  context:
    module: context-simple
    source: git+https://github.com/org/modules@main
    config:
      max_tokens: 400000

providers:
- module: provider-anthropic
  source: git+https://github.com/org/modules@main
  config:
    default_model: claude-sonnet-4-5

tools:
- module: tool-web
  source: git+https://github.com/org/modules@main

hooks:
- module: hooks-logging
  source: git+https://github.com/org/modules@main
  config:
    mode: session-only

agents:
  explorer: https://raw.githubusercontent.com/org/agents/main/explorer.md

context:
  docs: git+https://github.com/org/docs@main#subdirectory=docs

ui:
  show_thinking_stream: true
---

@docs:context/USAGE.md

# Base Profile

This profile provides core Amplifier functionality with streaming orchestrator,
simple context management, and basic tools for web search and task delegation.

## Features
- Extended thinking enabled for complex reasoning
- Auto-compacting context at 80% capacity
- Streaming UI with progress indicators

## Usage
Use this profile for general-purpose sessions where you need standard tooling
and agent capabilities.
```

**Key structure points:**

### YAML Frontmatter (between `---` delimiters)

**Profile metadata** (under `profile:` key):
```yaml
profile:
  name: base                    # Profile identifier
  version: 1.1.0                # Semantic version
  description: Short summary    # Human-readable description
  schema_version: 2             # Format version
  extends: foundation           # Optional: inherit from another profile
```

**All other configuration** at top level (NOT under `profile:`):
```yaml
session:         # Session requirements (orchestrator + context)
  orchestrator:  # Required: execution loop
    module: loop-streaming
    source: git+https://...
    config: {...}
  context:       # Required: message history
    module: context-simple
    source: git+https://...
    config: {...}

providers:       # Required: at least one LLM provider
- module: provider-anthropic
  source: git+https://...
  config: {...}

tools:           # Optional: capabilities
- module: tool-web
  source: git+https://...

hooks:           # Optional: interceptors
- module: hooks-logging
  source: git+https://...

agents:          # Optional: personas
  name: URL or path

context:         # Optional: runtime documentation
  name: git+https://...#subdirectory=path

ui:              # Optional: UI preferences
  show_thinking_stream: true
```

### Markdown Body (after frontmatter)

Everything after the closing `---` is Markdown documentation:
- Describes the profile's purpose
- Can include @mentions for runtime context injection
- Not processed during compilation (except for @mentions)
- Useful for documenting usage, features, caveats

## Profile Naming

Profiles use **collection/profile** naming:

**Collection** - Named group of related profiles:
- `foundation` - Core profiles from Microsoft
- `enterprise` - Organization-specific profiles
- `local` - Local development profiles

**Profile** - Individual configuration within collection:
- `base` - Core functionality
- `advanced` - Extended features
- `minimal` - Lightweight setup

**Full identifier:** `foundation/base`, `enterprise/secure`, `local/experimental`

**Directory structure:**
```
registry/profiles/
  foundation/
    base.md           → foundation/base
    advanced.md       → foundation/advanced
    minimal.md        → foundation/minimal
  enterprise/
    secure.md         → enterprise/secure
    dev.md            → enterprise/dev
```

**After compilation:**
```
.amplifierd/share/profiles/
  foundation/
    base/             → Compiled foundation/base
    advanced/         → Compiled foundation/advanced
  enterprise/
    secure/           → Compiled enterprise/secure
```

## Module References

Modules are referenced via **fsspec** URLs that support multiple protocols:

### Git References (most common)

**Standalone repository:**
```yaml
source: git+https://github.com/payneio/amplifier-module-loop-streaming@main
```
- Clones the entire repository
- `@main` specifies branch/tag/commit
- Whole repo becomes the module

**Subdirectory within repository:**
```yaml
source: git+https://github.com/myorg/amplifier-modules@v1.0.0#subdirectory=modules/tool-custom
```
- Clones repository, extracts subdirectory
- Useful for monorepos with multiple modules
- `#subdirectory=` specifies path within repo

### HTTP/HTTPS References

**Direct file download:**
```yaml
agents:
  explorer: https://raw.githubusercontent.com/org/agents/main/explorer.md
```
- Downloads file directly
- Useful for single-file resources like agents
- No git cloning required

### Local File References

**Local directory:**
```yaml
source: file:///home/user/dev/my-custom-module
```
- Points to local filesystem
- Useful during development
- Not portable across systems

### Git Reference Patterns

**Branch:**
```yaml
source: git+https://github.com/org/module@main
```

**Tag:**
```yaml
source: git+https://github.com/org/module@v1.0.0
```

**Commit hash:**
```yaml
source: git+https://github.com/org/module@abc123def456
```

**Subdirectory:**
```yaml
source: git+https://github.com/org/modules@main#subdirectory=providers/anthropic
```

**Recommendation:** Use **tags** for production (`@v1.0.0`), **branches** for development (`@main`).

## Real Example: foundation/base

Let's annotate a real profile to show how everything fits together:

```yaml
---
# Profile metadata (ONLY under profile: key)
profile:
  name: base                                    # Profile identifier
  version: 1.1.0                                # Current version
  description: Base configuration with core functionality
  schema_version: 2                             # Format version

# Session requirements (orchestrator + context)
session:
  orchestrator:                                 # Required: execution loop
    module: loop-streaming                      # Module identifier
    source: git+https://github.com/payneio/amplifier-module-loop-streaming@main
    config:
      extended_thinking: true                   # Enable extended reasoning
  context:                                      # Required: message history
    module: context-simple                      # Module identifier
    source: git+https://github.com/microsoft/amplifier-module-context-simple@main
    config:
      max_tokens: 400000                        # Maximum context size
      compact_threshold: 0.8                    # Compact at 80% capacity
      auto_compact: true                        # Automatic compaction

# Task delegation settings
task:
  max_recursion_depth: 1                        # Allow one level of task nesting

# LLM providers (at least one required)
providers:
- module: provider-anthropic                    # Anthropic Claude provider
  source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
  config:
    default_model: claude-sonnet-4-5            # Default model selection

# Optional tools
tools:
- module: tool-web                              # Web browsing
  source: git+https://github.com/microsoft/amplifier-module-tool-web@main
- module: tool-search                           # Web search
  source: git+https://github.com/microsoft/amplifier-module-tool-search@main
- module: tool-task                             # Task delegation
  source: git+https://github.com/microsoft/amplifier-module-tool-task@main
- module: tool-todo                             # TODO tracking
  source: git+https://github.com/microsoft/amplifier-module-tool-todo@main

# Optional hooks
hooks:
- module: hooks-status-context                  # Inject status into context
  source: git+https://github.com/microsoft/amplifier-module-hooks-status-context@main
  config:
    include_datetime: true                      # Add timestamp
    datetime_include_timezone: false            # Local time only

- module: hooks-redaction                       # Redact sensitive data
  source: git+https://github.com/microsoft/amplifier-module-hooks-redaction@main
  config:
    allowlist:                                  # Allow these IDs through
    - session_id
    - turn_id
    - span_id

- module: hooks-logging                         # Session logging
  source: git+https://github.com/microsoft/amplifier-module-hooks-logging@main
  config:
    mode: session-only                          # Log session events only
    session_log_template: ~/.amplifier/projects/{project}/sessions/{session_id}/events.jsonl

- module: hooks-todo-reminder                   # TODO reminders
  source: git+https://github.com/microsoft/amplifier-module-hooks-todo-reminder@main
  config:
    inject_role: user                           # Inject as user messages
    priority: 10                                # High priority

- module: hooks-streaming-ui                    # UI streaming
  source: git+https://github.com/microsoft/amplifier-module-hooks-streaming-ui@main

# Optional agents
agents:
  explorer: https://raw.githubusercontent.com/payneio/amplifierd/refs/heads/main/registry/agents/foundation/explorer.md

# Optional context directories (for @mention resolution)
context:
  foundation: git+https://github.com/payneio/amplifierd@main#subdirectory=registry/context/foundation
---

@foundation:context/shared/common-agent-base.md

# Base Profile

This profile provides comprehensive Amplifier functionality including:
- Streaming orchestrator with extended thinking
- Auto-compacting context manager
- Full tool suite (web, search, task delegation)
- Security hooks (redaction, logging)
- Development aids (TODO reminders, streaming UI)

Use this for general-purpose sessions requiring rich tooling.
```

## Configuration Options

### Session Configuration

**Orchestrator config:**
```yaml
session:
  orchestrator:
    config:
      extended_thinking: true               # Enable complex reasoning
      max_iterations: 25                    # Maximum loop iterations
      timeout: 300                          # Session timeout (seconds)
```

**Context config:**
```yaml
session:
  context:
    config:
      max_tokens: 400000                    # Maximum context size
      compact_threshold: 0.8                # Compact at 80% full
      auto_compact: true                    # Automatic compaction
```

**Session-level settings:**
```yaml
session:
  injection_budget_per_turn: 10000          # Max tokens per turn injection
  injection_size_limit: 50000               # Max total injection size
```

### Provider Configuration

```yaml
providers:
- module: provider-anthropic
  config:
    default_model: claude-sonnet-4-5        # Model selection
    api_key: ${ANTHROPIC_API_KEY}           # Environment variable reference
    max_retries: 3                          # Retry attempts
    timeout: 60                             # Request timeout
```

### Tool Configuration

Most tools require no configuration:
```yaml
tools:
- module: tool-web                          # No config needed
- module: tool-search                       # No config needed
```

Some tools have optional config:
```yaml
tools:
- module: tool-custom
  config:
    api_endpoint: https://api.example.com
    api_key: ${CUSTOM_API_KEY}
```

### Hook Configuration

Hooks vary widely - check module documentation:
```yaml
hooks:
- module: hooks-logging
  config:
    mode: session-only                      # or "all", "tool-only"
    session_log_template: path/template

- module: hooks-redaction
  config:
    allowlist: [session_id, turn_id]
    denylist: [api_key, password]
```

## Profile Inheritance (extends)

Profiles can inherit from other profiles:

```yaml
profile:
  name: advanced
  extends: base                             # Inherit from foundation/base
  version: 1.2.0
  description: Advanced features built on base

# Override or add to base profile
tools:
- module: tool-custom                       # Add custom tool
  source: git+https://...

# Base tools (web, search, task, todo) are inherited automatically
```

**How extends works:**
1. Base profile is loaded first
2. Current profile merges/overrides settings
3. Lists are appended (tools, hooks, providers)
4. Dicts are merged (config sections)

**Use cases:**
- **Organization profiles** extending standard profiles
- **Environment variants** (dev/staging/prod)
- **Incremental customization** (minimal → base → advanced)

## Agents vs. Context Directories

**Agents** and **context** are different:

### Agents (compiled into mount plans)

**What they are:**
- Markdown files with agent personas/instructions
- Embedded directly in mount plans
- Available as `session.config["agents"]["name"]`
- Kernel sees them as config data

**How to include:**
```yaml
agents:
  code-expert: https://raw.githubusercontent.com/.../code-expert.md
  debug-helper: file:///local/path/debug-helper.md
```

**Result:** Content embedded in mount plan dict

### Context Directories (loaded at runtime via @mentions)

**What they are:**
- Directories of markdown documentation
- Loaded on-demand via @mention resolution
- Injected as messages via `context.add_message()` API
- Kernel sees them as messages (NOT config)

**How to include:**
```yaml
context:
  docs: git+https://github.com/org/docs@main#subdirectory=documentation
  specs: file:///local/path/specifications
```

**How to use:**
```markdown
# In profile body or during session
@docs:context/USAGE.md
@specs:architecture/DESIGN.md
```

**Result:** Files loaded at runtime, injected as messages

**Key distinction:**
- **Agents** = Static config embedded at mount plan generation
- **Context** = Dynamic content loaded during execution

## Where Profiles Live

**Development (source):**
```
amplifierd/registry/profiles/
  foundation/
    base.md                     # Source profile definition
    advanced.md
  enterprise/
    secure.md
```

**After compilation (cache):**
```
.amplifierd/share/profiles/
  foundation/
    base/
      profile.md                # Cached profile definition
      profile.lock              # Change detection
      orchestrator/
        loop-streaming/
          amplifier_module_loop_streaming/
      context/
        context-simple/
          amplifier_module_context_simple/
      providers/
        provider-anthropic/
          amplifier_module_provider_anthropic/
      agents/
        explorer.md
      contexts/
        foundation/             # Context directory
```

## Common Patterns

### Minimal Profile (testing)
```yaml
session:
  orchestrator: {module: loop-streaming, source: git+https://...}
  context: {module: context-simple, source: git+https://...}
providers:
- module: provider-anthropic
  source: git+https://...
```

### Standard Profile (general use)
```yaml
session: {...}
providers: [{...}]
tools:
- module: tool-web
  source: git+https://...
- module: tool-search
  source: git+https://...
hooks:
- module: hooks-logging
  source: git+https://...
agents:
  helper: https://...
```

### Enterprise Profile (production)
```yaml
profile:
  extends: foundation/base      # Build on standard base
session:
  context:
    config:
      max_tokens: 800000        # Larger context for complex tasks
providers:
- module: provider-azure-openai # Use Azure instead of Anthropic
  config:
    deployment: gpt-4-turbo
hooks:
- module: hooks-audit           # Add audit logging
  config:
    audit_endpoint: https://...
- module: hooks-approval        # Add approval workflow
  config:
    approval_required: true
```

## Validation

Profiles are validated when compiled:

**Required fields:**
- `profile.name`
- `profile.version`
- `profile.schema_version`
- `session.orchestrator.module`
- `session.orchestrator.source`
- `session.context.module`
- `session.context.source`
- At least one provider in `providers` list

**Optional but recommended:**
- `profile.description` - Helps others understand profile purpose
- Module `config` sections - Explicit > implicit defaults

**Common errors:**
- Missing orchestrator or context
- No providers specified
- Invalid git refs (typo in URL, wrong branch)
- Malformed YAML (indentation, syntax)

## Next Steps

Now that you understand profile structure:

1. **See how profiles become sessions:** [Mount Plans](./mount-plans.md)
2. **Deep dive into transformation:** [Profile Lifecycle](../04-advanced/profile-lifecycle.md)
3. **Browse example profiles:** `amplifierd/registry/profiles/`

## Key Takeaways

- **Profiles are Markdown + YAML** - Easy to read and version control
- **Minimum: orchestrator + context + provider** - These three are required
- **Git refs enable sharing** - Profiles work across systems
- **Agents embed, context loads dynamically** - Different use cases
- **Inheritance enables reuse** - Build specialized profiles on standard base
- **Profile hint = "collection/profile"** - Namespaced, portable identifiers
