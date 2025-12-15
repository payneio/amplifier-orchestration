# Profile Lifecycle

This document provides a **complete technical walkthrough** of how profiles transform from markdown files into running Amplifier sessions. After reading this, you'll understand every phase, artifact, and transformation.

## Overview

The profile lifecycle has **four distinct phases:**

```
Phase 1: Collection Resolution  (Git URLs → Cached Repos)
    ↓
Phase 2: Profile Compilation    (Profile Specs → Organized Modules)
    ↓
Phase 3: Mount Plan Generation  (Compiled Profile → Execution Config)
    ↓
Phase 4: Session Initialization (Mount Plan → Running Session)
```

Each phase:
- Has clear inputs and outputs
- Produces intermediate artifacts
- Can be validated independently
- Maintains resource identity

## Phase 1: Collection Resolution

**Purpose:** Resolve collection references and cache git content

**Input:** `.amplifierd/share/collections.yaml`

### collections.yaml Format

```yaml
collections:
  foundation:
    source: git+https://github.com/microsoft/amplifier-profiles@v1.0.0

  enterprise:
    source: git+https://github.com/myorg/amplifier-profiles@main

  local:
    source: file:///home/user/dev/my-profiles
```

### Processing Steps

1. **Read collections.yaml:**
   ```python
   collections_file = share_dir / "collections.yaml"
   collections_config = yaml.safe_load(collections_file.read_text())
   ```

2. **Resolve each collection:**
   ```python
   for collection_name, collection_spec in collections_config["collections"].items():
       source_ref = collection_spec["source"]

       # Parse fsspec URL
       if source_ref.startswith("git+"):
           # Clone git repository
           repo_url, ref = parse_git_ref(source_ref)
           commit_hash = git.clone(repo_url, ref)
           cache_dir = cache_dir / "git" / commit_hash
       elif source_ref.startswith("file://"):
           # Copy local directory
           local_path = parse_file_ref(source_ref)
           cache_dir = cache_dir / "local" / hash(local_path)
           shutil.copytree(local_path, cache_dir)
   ```

3. **Find profile definitions:**
   ```python
   # Scan for profile.md files in collection
   profile_files = cache_dir.glob("**/profile.md")

   # Copy to share directory
   for profile_file in profile_files:
       profile_name = profile_file.parent.name
       dest = share_dir / "profiles" / collection_name / profile_name / "profile.md"
       shutil.copy(profile_file, dest)
   ```

### Output Artifacts

**Cache directory structure:**
```
.amplifierd/cache/
  git/
    abc123def456.../                    # Commit hash directory
      profiles/
        base/
          profile.md
        advanced/
          profile.md
      modules/
        loop-streaming/
          amplifier_module_loop_streaming/
```

**Share directory structure:**
```
.amplifierd/share/profiles/
  foundation/
    base/
      profile.md                        # Cached profile definition
    advanced/
      profile.md
  enterprise/
    secure/
      profile.md
```

### Change Detection

Collections are re-resolved when:
- **collections.yaml changes** (new collections, updated refs)
- **Cache is missing** (first run, manual deletion)
- **User forces refresh** (via CLI flag)

Git commit hashes provide automatic change detection:
- Same commit hash → Cache hit (skip cloning)
- Different commit hash → Cache miss (re-clone)

## Phase 2: Profile Compilation

**Purpose:** Resolve module references and organize by mount type

**Input:** `share/profiles/<collection>/<profile>/profile.md`

### Profile Parsing

1. **Read profile.md:**
   ```python
   profile_path = share_dir / "profiles" / collection / profile / "profile.md"
   content = profile_path.read_text()

   # Extract YAML frontmatter between --- delimiters
   if not content.startswith("---\n"):
       raise ValueError("Profile has no YAML frontmatter")

   end_idx = content.find("\n---\n", 4)
   frontmatter_text = content[4:end_idx]

   frontmatter = yaml.safe_load(frontmatter_text)
   ```

2. **Extract resource references:**
   ```python
   # Session resources (orchestrator + context)
   orchestrator_ref = frontmatter["session"]["orchestrator"]["source"]
   context_ref = frontmatter["session"]["context"]["source"]

   # Optional resources
   provider_refs = [p["source"] for p in frontmatter.get("providers", [])]
   tool_refs = [t["source"] for t in frontmatter.get("tools", [])]
   hook_refs = [h["source"] for h in frontmatter.get("hooks", [])]
   agent_refs = frontmatter.get("agents", {})
   context_refs = frontmatter.get("context", {})
   ```

### Resource Resolution

For each resource reference:

**1. Parse reference:**
```python
if ref.startswith("git+"):
    # Git reference
    repo_url, commit_or_ref = parse_git_url(ref)
    subdirectory = extract_subdirectory(ref)  # Optional #subdirectory=path

elif ref.startswith("http://") or ref.startswith("https://"):
    # HTTP reference (for single files like agents)
    url = ref

elif ref.startswith("file://"):
    # Local file reference
    local_path = parse_file_url(ref)
```

**2. Fetch/clone resource:**
```python
if ref.startswith("git+"):
    # Clone to cache
    commit_hash = git.clone(repo_url, commit_or_ref)
    cache_path = cache_dir / "git" / commit_hash

    if subdirectory:
        source_path = cache_path / subdirectory
    else:
        source_path = cache_path

elif ref.startswith("http"):
    # Download file
    content = requests.get(url).text
    cache_hash = hashlib.sha256(content.encode()).hexdigest()
    cache_path = cache_dir / "http" / cache_hash / Path(url).name
    cache_path.write_text(content)
    source_path = cache_path
```

**3. Copy to profile directory:**
```python
# Determine mount type from module ID
mount_type = guess_mount_type(module_id)
# Examples: "provider-anthropic" → "providers"
#           "loop-streaming" → "orchestrator"
#           "tool-web" → "tools"

# Create destination
dest_dir = profile_dir / mount_type / module_id

# Copy module package
shutil.copytree(source_path, dest_dir)
```

### Mount Type Organization

Modules are organized by type:

| Mount Type | Module Patterns | Purpose |
|-----------|-----------------|---------|
| `orchestrator/` | `orchestrator-*`, `loop-*` | Execution loop (one required) |
| `context/` | `context-*` | Message history (one required) |
| `providers/` | `provider-*` | LLM providers (one+ required) |
| `tools/` | `tool-*` | Capabilities (optional) |
| `hooks/` | `hooks-*`, `hook-*` | Interceptors (optional) |

### Agent Compilation

Agents are handled differently (single files, not Python packages):

```python
# Resolve agent references
for agent_name, agent_ref in frontmatter.get("agents", {}).items():
    # Download/copy agent markdown
    if agent_ref.startswith("http"):
        content = requests.get(agent_ref).text
    elif agent_ref.startswith("file://"):
        content = Path(parse_file_url(agent_ref)).read_text()

    # Save to agents directory
    agent_file = profile_dir / "agents" / f"{agent_name}.md"
    agent_file.parent.mkdir(parents=True, exist_ok=True)
    agent_file.write_text(content)
```

### Context Directory Compilation

Context directories (for @mention resolution):

```python
# Resolve context directory references
for context_name, context_ref in frontmatter.get("context", {}).items():
    # Clone/copy context directory
    if context_ref.startswith("git+"):
        # Parse git ref with optional subdirectory
        repo_url, ref = parse_git_ref(context_ref)
        subdirectory = extract_subdirectory(context_ref)

        # Clone and extract
        commit_hash = git.clone(repo_url, ref)
        source_path = cache_dir / "git" / commit_hash / subdirectory

        # Copy to contexts directory
        dest_dir = profile_dir / "contexts" / context_name
        shutil.copytree(source_path, dest_dir)
```

### Output: Compiled Profile Directory

```
.amplifierd/share/profiles/foundation/base/
  profile.md                                    # Original profile definition
  profile.lock                                  # Change detection metadata

  orchestrator/                                 # Mount type directory
    loop-streaming/                             # Module ID directory
      amplifier_module_loop_streaming/          # Python package
        __init__.py
        orchestrator.py

  context/                                      # Mount type directory
    context-simple/                             # Module ID directory
      amplifier_module_context_simple/          # Python package
        __init__.py
        manager.py

  providers/                                    # Mount type directory
    provider-anthropic/                         # Module ID directory
      amplifier_module_provider_anthropic/      # Python package
        __init__.py
        provider.py

  tools/                                        # Mount type directory
    tool-web/
      amplifier_module_tool_web/
    tool-search/
      amplifier_module_tool_search/
    tool-task/
      amplifier_module_tool_task/

  hooks/                                        # Mount type directory
    hooks-logging/
      amplifier_module_hooks_logging/
    hooks-redaction/
      amplifier_module_hooks_redaction/

  agents/                                       # Agent markdown files
    code-expert.md
    debug-helper.md

  contexts/                                     # Context directories
    foundation/                                 # Context name
      shared/
        common-agent-base.md
      IMPLEMENTATION_PHILOSOPHY.md
```

### profile.lock Format

Change detection metadata:

```json
{
  "generated_at": "2025-11-28T10:30:00Z",
  "profile_hash": "abc123def456",
  "resources": {
    "orchestrator": {
      "name": "loop-streaming",
      "ref": "git+https://github.com/payneio/amplifier-module-loop-streaming@main",
      "commit": "abc123def456789",
      "resolved_at": "2025-11-28T10:29:00Z"
    },
    "providers": [
      {
        "name": "provider-anthropic",
        "ref": "git+https://github.com/microsoft/amplifier-module-provider-anthropic@main",
        "commit": "def456abc123",
        "resolved_at": "2025-11-28T10:29:00Z"
      }
    ],
    "agents": {
      "code-expert": {
        "ref": "https://raw.githubusercontent.com/org/agents/main/code-expert.md",
        "hash": "fed456cba321",
        "resolved_at": "2025-11-28T10:29:00Z"
      }
    }
  }
}
```

### Change Detection

Profile is recompiled when:
- **profile.md changes** (checksum mismatch)
- **Resource refs change** (different git commit, updated URL)
- **profile.lock missing** (first compile, manual deletion)
- **User forces refresh** (via CLI flag)

## Phase 3: Mount Plan Generation

**Purpose:** Transform compiled profile into amplifier-core's expected format

**Input:** `share/profiles/<collection>/<profile>/` (complete directory)

### Generation Process

**1. Initialize mount plan service:**
```python
from amplifierd.services.mount_plan_service import MountPlanService

mount_plan_service = MountPlanService(share_dir=Path(".amplifierd/share"))
```

**2. Generate mount plan:**
```python
mount_plan = mount_plan_service.generate_mount_plan("foundation/base")
```

**Internal steps:**

```python
def generate_mount_plan(self, profile_id: str) -> dict[str, Any]:
    # 1. Parse profile_id
    collection, profile = profile_id.split("/")

    # 2. Find profile directory
    profile_dir = self.share_dir / "profiles" / collection / profile

    # 3. Load agents
    agents_dict = self._load_agents(profile_dir / "agents", profile_id)

    # 4. Parse profile.md frontmatter
    frontmatter = self._parse_frontmatter(profile_dir / "profile.md")

    # 5. Transform to mount plan
    mount_plan = self._transform_to_mount_plan(frontmatter, profile_id, agents_dict)

    return mount_plan
```

### Transform Logic

**Session section:**
```python
# Input (from profile.md frontmatter):
session:
  orchestrator:
    module: loop-streaming
    source: git+https://github.com/payneio/amplifier-module-loop-streaming@main
    config:
      extended_thinking: true

# Output (in mount plan):
"session": {
  "orchestrator": {
    "module": "loop-streaming",
    "source": "foundation/base",      # Profile hint replaces git URL
    "config": {"extended_thinking": True}
  }
}
```

**Providers section:**
```python
# Input:
providers:
- module: provider-anthropic
  source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
  config:
    default_model: claude-sonnet-4-5

# Output:
"providers": [
  {
    "module": "provider-anthropic",
    "source": "foundation/base",      # Profile hint
    "config": {"default_model": "claude-sonnet-4-5"}
  }
]
```

**Agents section:**
```python
# Input (agents directory):
agents/
  code-expert.md      # Contains: "You are an expert software engineer..."
  debug-helper.md     # Contains: "You specialize in debugging..."

# Output (embedded content):
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
```

### Output: Mount Plan Dict

```python
{
  "session": {
    "orchestrator": {
      "module": "loop-streaming",
      "source": "foundation/base",
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

  "tools": [
    {"module": "tool-web", "source": "foundation/base", "config": {}},
    {"module": "tool-search", "source": "foundation/base", "config": {}},
    {"module": "tool-task", "source": "foundation/base", "config": {}}
  ],

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

  "agents": {
    "code-expert": {
      "content": "You are an expert software engineer with deep knowledge...",
      "metadata": {"source": "foundation/base:agents/code-expert.md"}
    },
    "debug-helper": {
      "content": "You specialize in debugging complex issues...",
      "metadata": {"source": "foundation/base:agents/debug-helper.md"}
    }
  }
}
```

**Key transformations:**
- Git URLs → Profile hints (`"source": "foundation/base"`)
- Agent files → Embedded content
- Context refs → Omitted (loaded via @mentions at runtime)

## Phase 4: Session Initialization

**Purpose:** Translate mount plan into running session

**Input:** Mount plan dict from Phase 3

### Initialization Flow

**1. Create resolver:**
```python
from amplifierd.module_resolver import DaemonModuleSourceResolver

resolver = DaemonModuleSourceResolver(share_dir=Path(".amplifierd/share"))
```

**2. Mount resolver in coordinator:**
```python
# ExecutionRunner mounts resolver before session creation
coordinator.mount("module-source-resolver", resolver)
```

**3. Create session:**
```python
from amplifier_library import AmplifierSession

session = AmplifierSession(config=mount_plan)
```

**4. amplifier-core loads modules:**

For each module in mount plan:

```python
# Example: Load orchestrator
module_spec = mount_plan["session"]["orchestrator"]
# {"module": "loop-streaming", "source": "foundation/base", "config": {...}}

# Get resolver from coordinator
resolver = self.coordinator.get("module-source-resolver")

# Resolve module ID to path
source = resolver.resolve(
    module_id=module_spec["module"],       # "loop-streaming"
    profile_hint=module_spec["source"]      # "foundation/base"
)

# Get filesystem path
path = source.resolve()
# Returns: .amplifierd/share/profiles/foundation/base/orchestrator/loop-streaming

# Add to sys.path
sys.path.insert(0, str(path))

# Convert module ID to Python package name
# "loop-streaming" → "amplifier_module_loop_streaming"
package_name = "amplifier_module_" + module_spec["module"].replace("-", "_")

# Import module
module = importlib.import_module(package_name)

# Initialize with config
orchestrator = module.create_orchestrator(module_spec["config"])
```

### Resolution Details

**Resolver algorithm (from `module_resolver.py`):**

```python
def resolve(self, module_id: str, profile_hint: str | dict) -> ModuleSource:
    # 1. Parse profile hint
    if isinstance(profile_hint, dict):
        collection = profile_hint["collection"]
        profile = profile_hint["profile"]
    else:
        collection, profile = profile_hint.split("/")

    # 2. Guess mount type from module ID
    mount_type = self._guess_mount_type(module_id)
    # Examples:
    #   "provider-anthropic" → "providers"
    #   "loop-streaming" → "orchestrator"
    #   "tool-web" → "tools"

    # 3. Build path
    module_dir = (
        self.share_dir
        / "profiles"
        / collection
        / profile
        / mount_type
        / module_id
    )

    # 4. Return source
    return ModuleSource(path=module_dir, module_id=module_id)
```

**Mount type detection patterns:**

| Pattern | Mount Type |
|---------|-----------|
| `orchestrator-*`, `loop-*` | `orchestrator` |
| `context-*` | `context` |
| `provider-*` | `providers` |
| `tool-*` | `tools` |
| `hooks-*`, `hook-*` | `hooks` |

### Session Startup Sequence

```
1. Parse mount plan
   ↓
2. Validate required fields (orchestrator, context, providers)
   ↓
3. Load orchestrator module
   ├─ Resolve path via resolver
   ├─ Import Python package
   └─ Initialize with config
   ↓
4. Load context module
   ├─ Resolve path via resolver
   ├─ Import Python package
   └─ Initialize with config
   ↓
5. Load provider modules
   ├─ Resolve each provider
   ├─ Import packages
   └─ Initialize with configs
   ↓
6. Load tool modules (optional)
   ├─ Resolve each tool
   ├─ Import packages
   └─ Register with orchestrator
   ↓
7. Load hook modules (optional)
   ├─ Resolve each hook
   ├─ Import packages
   └─ Register interceptors
   ↓
8. Load agents (from mount plan)
   ├─ Extract embedded content
   └─ Make available via session.config["agents"]
   ↓
9. Session ready
```

### Error Handling

**Fatal errors (session creation fails):**
- Orchestrator module missing or failed to load
- Context module missing or failed to load
- No providers configured

**Non-fatal errors (warnings logged, session continues):**
- Tool module failed to load (others still loaded)
- Hook module failed to load (others still loaded)
- Provider module failed to load (if at least one succeeds)

## Complete Lifecycle Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│ USER DEFINES COLLECTIONS & PROFILES                                      │
│                                                                           │
│ .amplifierd/share/collections.yaml:                                      │
│   collections:                                                            │
│     foundation:                                                           │
│       source: git+https://github.com/microsoft/amplifier-profiles@v1.0.0 │
│                                                                           │
│ registry/profiles/foundation/base.md:                                     │
│   ---                                                                     │
│   session:                                                                │
│     orchestrator: {module: loop-streaming, source: git+https://...}      │
│   providers:                                                              │
│   - module: provider-anthropic                                            │
│     source: git+https://...                                               │
│   ---                                                                     │
└──────────────────────────────────────────────────────────────────────────┘
                                 ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: COLLECTION RESOLUTION                                           │
│                                                                           │
│ 1. Read collections.yaml                                                 │
│ 2. Clone git repositories to cache/git/<commit-hash>/                    │
│ 3. Find profile.md files in collections                                  │
│ 4. Copy to share/profiles/<collection>/<profile>/profile.md              │
│                                                                           │
│ Output:                                                                   │
│   cache/git/abc123.../profiles/base/profile.md                           │
│   share/profiles/foundation/base/profile.md                              │
└──────────────────────────────────────────────────────────────────────────┘
                                 ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: PROFILE COMPILATION                                             │
│                                                                           │
│ 1. Parse profile.md YAML frontmatter                                     │
│ 2. Extract resource references (orchestrator, providers, tools, etc.)    │
│ 3. Resolve each reference:                                               │
│    - Clone git repos → cache/git/<commit>/                               │
│    - Download HTTP files → cache/http/<hash>/                            │
│ 4. Copy/organize by mount type:                                          │
│    - orchestrator/loop-streaming/amplifier_module_loop_streaming/        │
│    - providers/provider-anthropic/amplifier_module_provider_anthropic/   │
│    - agents/code-expert.md                                               │
│ 5. Generate profile.lock for change detection                            │
│                                                                           │
│ Output:                                                                   │
│   share/profiles/foundation/base/                                        │
│     orchestrator/loop-streaming/amplifier_module_loop_streaming/         │
│     providers/provider-anthropic/amplifier_module_provider_anthropic/    │
│     agents/code-expert.md                                                │
│     profile.lock                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                 ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: MOUNT PLAN GENERATION                                           │
│                                                                           │
│ 1. Read profile.md frontmatter from registry                             │
│ 2. Load agents from share/profiles/foundation/base/agents/               │
│ 3. Transform to dict format:                                             │
│    - Replace git URLs with profile hints ("foundation/base")             │
│    - Embed agent content                                                 │
│    - Keep module IDs and configs                                         │
│                                                                           │
│ Output (Python dict):                                                    │
│   {                                                                       │
│     "session": {                                                          │
│       "orchestrator": {                                                   │
│         "module": "loop-streaming",                                       │
│         "source": "foundation/base",  # Profile hint                     │
│         "config": {...}                                                   │
│       }                                                                   │
│     },                                                                    │
│     "providers": [...],                                                   │
│     "agents": {                                                           │
│       "code-expert": {"content": "...", "metadata": {...}}               │
│     }                                                                     │
│   }                                                                       │
└──────────────────────────────────────────────────────────────────────────┘
                                 ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: SESSION INITIALIZATION                                          │
│                                                                           │
│ 1. Create DaemonModuleSourceResolver with share_dir                      │
│ 2. Mount resolver in coordinator                                         │
│ 3. Create AmplifierSession with mount plan dict                          │
│ 4. amplifier-core's ModuleLoader:                                        │
│    - For each module in mount plan:                                      │
│      a. Call resolver.resolve(module_id, "foundation/base")              │
│      b. Get filesystem path from resolver                                │
│      c. Add path to sys.path                                             │
│      d. Import amplifier_module_{name}                                   │
│      e. Initialize with config                                           │
│ 5. Session ready to execute                                              │
│                                                                           │
│ Example resolution:                                                       │
│   Input: module_id="provider-anthropic", profile_hint="foundation/base"  │
│   Resolver determines: mount_type="providers" (from "provider-*" pattern)│
│   Returns: .amplifierd/share/profiles/foundation/base/providers/provider-anthropic │
│   Imports: amplifier_module_provider_anthropic                           │
└──────────────────────────────────────────────────────────────────────────┘
                                 ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ RUNNING SESSION                                                           │
│                                                                           │
│ - Orchestrator executing turns                                           │
│ - Context managing message history                                       │
│ - Providers handling LLM requests                                        │
│ - Tools available for invocation                                         │
│ - Hooks intercepting events                                              │
│ - Agents accessible via session.config["agents"]                         │
└──────────────────────────────────────────────────────────────────────────┘
```

## Intermediate Artifacts Summary

| Artifact | Location | Purpose | Format |
|----------|----------|---------|--------|
| **collections.yaml** | `.amplifierd/share/collections.yaml` | Define collection sources | YAML |
| **Git cache** | `.amplifierd/cache/git/<commit>/` | Cached git repos | Directory tree |
| **HTTP cache** | `.amplifierd/cache/http/<hash>/` | Cached HTTP downloads | Files |
| **Profile definition** | `.amplifierd/share/profiles/<collection>/<profile>/profile.md` | Cached profile spec | Markdown + YAML |
| **Compiled modules** | `.amplifierd/share/profiles/.../orchestrator/...` | Organized Python packages | Python packages |
| **Agents** | `.amplifierd/share/profiles/.../agents/*.md` | Agent markdown files | Markdown |
| **Contexts** | `.amplifierd/share/profiles/.../contexts/<name>/` | Context directories | Markdown files |
| **profile.lock** | `.amplifierd/share/profiles/<collection>/<profile>/profile.lock` | Change detection | JSON |
| **Mount plan** | (In-memory dict) | Session config | Python dict |

## Key File Locations

**User-editable:**
- `.amplifierd/share/collections.yaml` - Collection definitions
- `registry/profiles/<collection>/<profile>.md` - Profile sources (in amplifierd repo)

**Generated/cached (don't edit):**
- `.amplifierd/cache/` - Git/HTTP cache
- `.amplifierd/share/profiles/` - Compiled profiles
- `.amplifierd/share/profiles/<collection>/<profile>/profile.lock` - Change detection

**Runtime (in-memory):**
- Mount plan dict - Never written to disk, passed directly to amplifier-core

## Change Detection Strategy

### Collection Changes
- **Trigger:** collections.yaml modified, git refs updated
- **Detection:** File checksum, git commit hashes
- **Action:** Re-clone changed collections

### Profile Changes
- **Trigger:** profile.md modified, resource refs updated
- **Detection:** profile.lock comparison (commit hashes, file hashes)
- **Action:** Recompile affected profiles

### Module Changes
- **Trigger:** Upstream module repos updated
- **Detection:** Git commit hash comparison in profile.lock
- **Action:** Re-fetch and update compiled modules

**Manual refresh:**
```bash
# Force recompilation
amplifierd compile-profile --force foundation/base

# Force collection update
amplifierd sync-collections --force
```

## Performance Considerations

**Caching effectiveness:**
- Git clones cached by commit hash (deterministic)
- HTTP downloads cached by content hash
- Profile compilation skipped if profile.lock matches

**Optimization strategies:**
- Shallow git clones (depth=1) for faster fetching
- Parallel module resolution where possible
- Incremental compilation (only changed profiles)

**Typical timings:**
- First compile (fresh): 30-60 seconds (git clones)
- Subsequent compiles (cached): 1-2 seconds (cache hits)
- Mount plan generation: <100ms (read + transform)
- Session initialization: 200-500ms (module imports)

## Troubleshooting

### Profile not found
**Symptom:** `ProfileNotFoundError: foundation/base`
**Cause:** Profile not in collections.yaml or not compiled
**Fix:** Add collection to collections.yaml, run compilation

### Module resolution failure
**Symptom:** `ModuleNotFoundError: amplifier_module_loop_streaming`
**Cause:** Module not in expected directory structure
**Fix:** Check compiled profile structure, verify naming conventions

### Stale cache
**Symptom:** Old module version used despite git ref update
**Cause:** profile.lock outdated
**Fix:** Delete profile.lock and recompile, or use `--force` flag

### Import errors
**Symptom:** `ImportError` during session initialization
**Cause:** Incorrect directory structure (missing Python package)
**Fix:** Verify module contains `amplifier_module_{name}/` directory

## Best Practices

1. **Use semantic versioning for collections:**
   ```yaml
   source: git+https://github.com/org/profiles@v1.0.0  # Not @main
   ```

2. **Pin module versions in production:**
   ```yaml
   source: git+https://github.com/org/module@v2.1.0#subdirectory=modules/provider
   ```

3. **Test profile compilation separately:**
   ```bash
   amplifierd compile-profile foundation/base
   amplifierd validate-profile foundation/base
   ```

4. **Monitor profile.lock for changes:**
   - Commit profile.lock to version control
   - Review diffs when resources update
   - Understand what changed before deploying

5. **Use local sources during development:**
   ```yaml
   source: file:///home/user/dev/my-module  # Fast iteration
   ```

## Summary

The profile lifecycle transforms human-friendly templates into running sessions through four distinct phases:

1. **Collection Resolution** - Git URLs → Cached repos
2. **Profile Compilation** - Profile specs → Organized modules
3. **Mount Plan Generation** - Compiled profile → Execution config
4. **Session Initialization** - Mount plan → Running session

Each phase:
- Has clear boundaries and responsibilities
- Produces inspectable artifacts
- Supports independent validation
- Enables incremental updates

**Key innovations:**
- **Profile hints** replace absolute paths (portability)
- **Consistent directory structure** enables reliable resolution
- **Cached artifacts** avoid redundant work
- **Change detection** supports incremental updates
- **Resolver pattern** bridges profiles and execution

This design provides:
- ✅ **Portability** - Profiles work everywhere
- ✅ **Maintainability** - Single source of truth
- ✅ **Performance** - Aggressive caching
- ✅ **Transparency** - Inspectable artifacts at every phase
