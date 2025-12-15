# Collection Seeding Implementation Summary

## Overview

Implemented automatic seeding of `collections.yaml` with package-bundled collections on first run.

## Changes Made

### 1. CollectionRegistry.initialize_with_defaults()

**File:** `amplifierd/services/collection_registry.py`

Added method that:
- Checks if registry is already initialized (skips if not empty)
- Discovers built-in collections from `amplifierd/data/collections/`
- Seeds registry with `package:{collection-name}` source format
- Marks collections as `package_bundled: true`
- Initializes with `version: 0.0.0` (updated on mount)

### 2. SimpleCollectionService.__init__()

**File:** `amplifierd/services/simple_collection_service.py`

Updated initialization to call `registry.initialize_with_defaults()` after creating registry.

### 3. SimpleCollectionService.sync_collections()

**File:** `amplifierd/services/simple_collection_service.py`

Added handling for `package:` source format:
- Resolves `package:{name}` to actual package path
- Converts to `local:{resolved-path}` for normal sync flow
- Sets `package_bundled=True` flag

## Behavior

### First Run (Empty Registry)

1. Service initialization creates empty `collections.yaml`
2. `initialize_with_defaults()` discovers package collections:
   - `developer-expertise`
   - `foundation`
3. Seeds registry with entries:
   ```yaml
   collections:
     developer-expertise:
       source: "package:developer-expertise"
       package_bundled: true
       version: "0.0.0"
       installed_at: ""
       resources: {modules: [], profiles: [], agents: [], context: []}
   ```

### Subsequent Syncs

1. `sync_collections()` resolves `package:` sources to actual paths
2. Mounts collections from package directory
3. Extracts resources to share directories
4. Updates registry with actual version and resource lists

### User Override

Users can override package collections by adding explicit entries with the same name in `collections.yaml`.

## Testing

### Unit Tests

**File:** `tests/services/test_collection_seeding.py`

- ✅ `test_initialize_with_defaults_creates_registry` - Verifies seeding behavior
- ✅ `test_initialize_with_defaults_skips_if_not_empty` - Ensures idempotency
- ✅ `test_package_collections_have_expected_structure` - Validates package structure

### Integration Tests

**File:** `tests/integration/test_collection_sync_flow.py`

- ✅ `test_collection_sync_seeds_and_mounts_package_collections` - End-to-end flow
- ✅ `test_collection_service_initializes_empty_share_dir` - First-run behavior
- ✅ `test_package_collection_source_format_resolved` - Source format resolution

### Manual Verification

**File:** `tests/manual_test_seeding.py`

Demonstrates complete flow:
1. Initialize service with empty share directory
2. Verify `collections.yaml` seeded with 2 package collections
3. Sync collections to mount from package
4. List collections showing proper metadata
5. Verify resources extracted to share directories

Results:
- ✅ 2 collections seeded (developer-expertise, foundation)
- ✅ Both marked as `package_bundled: true`
- ✅ Sources resolved from `package:` to `local:` format
- ✅ Resources successfully extracted

## Key Implementation Details

### Source Format

- **Initial:** `package:{collection-name}` in seeded registry
- **Resolved:** `local:{absolute-path}` during sync
- **Final:** User sees actual path in mounted collections

### Package Collections Directory

Location: `amplifierd/data/collections/`

Expected structure:
```
amplifierd/data/collections/
├── developer-expertise/
│   ├── profiles/
│   ├── agents/
│   └── pyproject.toml
└── foundation/
    ├── profiles/
    ├── agents/
    ├── context/
    └── pyproject.toml
```

### Registry Entry Evolution

**After seeding:**
```yaml
source: "package:foundation"
version: "0.0.0"
installed_at: ""
resources: {modules: [], profiles: [], agents: [], context: []}
```

**After first sync:**
```yaml
source: "local:/path/to/amplifierd/data/collections/foundation"
version: "0.1.0"  # from pyproject.toml
installed_at: "2025-11-23T10:46:38.280000"
resources:
  profiles: ["profiles/foundation/base.md", "profiles/foundation/test.md"]
  agents: ["agents/foundation/example.yaml"]
  context: ["context/foundation/docs.md"]
```

## Verification

All checks passing:
- ✅ `make check` - Linting, formatting, type checking
- ✅ Unit tests - Collection registry seeding
- ✅ Integration tests - End-to-end sync flow
- ✅ Existing tests - No regressions in API tests

## Notes

- Collections are only seeded once (on empty registry)
- Seeding happens automatically on service initialization
- User can override by adding explicit entries
- Package collections discovered from `amplifierd/data/collections/`
- Only directories with resource subdirs (modules/profiles/agents/context) are seeded
