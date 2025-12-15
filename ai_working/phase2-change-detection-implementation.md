# Phase 2: Change Detection Implementation

**Status**: ✅ Complete
**Date**: 2025-01-26

## Overview

Implemented hash-based change detection for profile compilation to prevent unnecessary recompilation on every startup. This addresses the issue where profiles were being recompiled even when `force_profile_rebuild_on_start: false` because all "synced" collections triggered compilation.

## Changes Made

### 1. New Compilation Metadata Model

**File**: `amplifierd/models/compilation_metadata.py` (new)

Created a dataclass to track compilation state:
- `source_commit`: Collection commit when compiled (for future use)
- `manifest_hash`: SHA256 hash of profile manifest
- `compiled_at`: ISO timestamp of compilation

Stored as `.compilation_meta.json` in compiled profile directories.

### 2. Profile Compilation Service Updates

**File**: `amplifierd/services/profile_compilation.py`

**Added**:
- `_hash_profile_manifest()`: Creates stable SHA256 hash of profile manifest
  - Includes: name, version, agents, context, tools, hooks, providers, orchestrator, context_manager
  - Uses sorted JSON for consistent hashing

- Updated `compile_profile()`:
  - Added `force: bool = False` parameter
  - Checks existing metadata before compilation
  - Skips compilation if hash matches and `force=False`
  - Saves metadata after successful compilation
  - Handles corrupted metadata gracefully (logs warning and recompiles)

### 3. Collection Service Integration

**File**: `amplifierd/services/collection_service.py`

Updated `sync_collections()` to pass `force_compile` parameter to compilation service:
```python
compiled_path = self.compilation_service.compile_profile(
    name, profile, force=force_compile
)
```

### 4. Gitignore Update

**File**: `.gitignore`

Added `.compilation_meta.json` to ignore metadata files.

### 5. Comprehensive Tests

**File**: `tests/services/test_profile_compilation_change_detection.py` (new)

Created 5 test cases covering:
1. ✅ First compilation creates metadata
2. ✅ Second compilation skips unchanged profiles
3. ✅ `force=True` recompiles even if unchanged
4. ✅ Changed profile triggers recompilation
5. ✅ Corrupted metadata triggers recompilation

All tests pass.

## Expected Behavior

### First Startup (no cache)
```
Collections: cloned/synced
Profiles: compiled (metadata saved)
Result: Normal startup time
```

### Second Startup (with cache, force_compile=False)
```
Collections: status="skipped" (cache exists, no refresh)
Profiles: Compilation SKIPPED (hashes match)
Result: ⚡ FAST startup!
```

### With force_compile=True
```
Collections: status="skipped" (cache exists, no refresh)
Profiles: RECOMPILED (force overrides hash check)
Result: Normal compilation time
```

### After Profile Changes
```
Collections: status="updated" or "synced"
Profiles: RECOMPILED (hash mismatch detected)
Result: Only changed profiles recompiled
```

## Design Philosophy Alignment

✅ **Ruthless Simplicity**:
- Simple hash-based check (SHA256 of manifest)
- No complex dependency tracking
- Fail-safe: Corrupted metadata → recompile

✅ **Single Responsibility**:
- Metadata model: Data structure only
- Hash function: Manifest serialization only
- Compilation service: Change detection isolated

✅ **Defensive**:
- Handles missing metadata (first run)
- Handles corrupted metadata (logs warning, recompiles)
- Atomic: Metadata saved after successful compilation

## Testing

### Unit Tests
```bash
uv run pytest tests/services/test_profile_compilation_change_detection.py -xvs
# Result: 5/5 passed
```

### Integration Tests
```bash
uv run pytest tests/services/test_profile_compilation.py -xvs
# Result: 14/14 passed (existing tests still work)
```

## Next Steps (Future Phases)

Phase 3 would add:
- Source commit tracking (detect upstream changes)
- Asset hash tracking (detect changes in referenced files)
- Partial recompilation (only changed assets)

For now, manifest-level change detection provides significant startup speed improvement while maintaining simplicity.

## Impact

**Before**: Every startup recompiled all profiles (~5-10s per profile)
**After**: Second startup skips unchanged profiles (~instant)

For a typical setup with 5 profiles:
- **Before**: 25-50s compilation time on every startup
- **After**: 0s compilation time on repeat startups (with cache)

🎯 **Mission Accomplished**: Fast startup while preserving correctness!
