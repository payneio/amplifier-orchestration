# Simple Services Implementation

Successfully implemented three simplified services based on zen-architect's design specification.

## Files Created

1. **amplifierd/services/simple_module_service.py** (~170 lines)
2. **amplifierd/services/simple_collection_service.py** (~240 lines)
3. **amplifierd/services/simple_profile_service.py** (~360 lines)

## Implementation Details

### SimpleModuleService

**Purpose**: Scans collections directory for modules organized by type

**Key Features**:
- Single collections directory scanning
- Type detection from path structure (providers/, tools/, hooks/, orchestrators/)
- Module metadata from module.yaml files
- Module ID format: `{collection}/{type}/{name}`

**Methods**:
- `list_modules(type_filter)` - List all modules with optional type filter
- `get_module(module_id)` - Get detailed module information

**Internal Models**:
- `ModuleMetadata` dataclass for internal representation
- Returns `ModuleInfo` and `ModuleDetails` API models

### SimpleCollectionService

**Purpose**: Manages collections via mounting/unmounting

**Key Features**:
- Lists collections with metadata from collection.yaml
- Mounts via git clone or filesystem copy
- Unmounts via directory removal
- Auto-detects collection type (git vs local)

**Methods**:
- `list_collections()` - List all collections
- `get_collection(identifier)` - Get detailed collection info
- `mount_collection(identifier, source, method)` - Mount collection
- `unmount_collection(identifier)` - Unmount collection

**Internal Models**:
- `CollectionMetadata` dataclass for internal representation
- Returns `CollectionInfo` and `CollectionDetails` API models

### SimpleProfileService

**Purpose**: Manages profiles with one-level inheritance

**Key Features**:
- Scans collections/*/profiles/*.yaml for profiles
- One-level inheritance via `extends` field
- Active profile stored in simple text file
- Profile merging with inheritance

**Methods**:
- `list_profiles()` - List all available profiles
- `get_profile(name)` - Get detailed profile with resolved inheritance
- `get_active_profile()` - Get currently active profile
- `activate_profile(name)` - Activate a profile
- `deactivate_profile()` - Deactivate current profile

**Internal Models**:
- `ProfileData` dataclass for internal representation
- Returns `ProfileInfo` and `ProfileDetails` API models

## Design Principles Applied

### Ruthless Simplicity
- Direct file system operations (no database)
- Simple YAML parsing with pyyaml
- Minimal error handling focused on common cases
- No elaborate state management

### Clear Contracts
- Type hints throughout
- Comprehensive docstrings
- Explicit error messages
- Standard exceptions (ValueError, FileNotFoundError, RuntimeError)

### Separation of Concerns
- Internal dataclasses for service logic
- API models for router compatibility
- Clear transformation between internal and external representations

## Testing

All services tested with:
- Instantiation
- Basic operations (list_*, get_*)
- Empty directory handling
- Logging output verification

Results:
```
✓ SimpleModuleService initialized
✓ SimpleCollectionService initialized
✓ SimpleProfileService initialized
✓ list_modules() returned 0 modules
✓ list_collections() returned 0 collections
✓ list_profiles() returned 0 profiles
```

## Code Quality

- ✅ All type checks pass (pyright)
- ✅ All linting passes (ruff)
- ✅ All formatting passes (ruff)
- ✅ No stubs or placeholders
- ✅ Comprehensive logging
- ✅ Proper error handling

## Next Steps

1. **Integration**: Wire services into FastAPI routers
2. **Testing**: Add unit tests for each service
3. **Migration**: Replace complex services with simple versions
4. **Validation**: Test with real collection data

## Notes

- Services use pathlib for all path operations
- All methods have proper type hints and docstrings
- Logging provides visibility into operations
- Error messages are descriptive and actionable
- Type narrowing used for pyright compatibility with dict[str, object]
