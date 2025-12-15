#!/usr/bin/env python3
"""Setup script for demo modules.

Creates symlinks in demo/modules/ with proper amplifier-module-* naming
to modules from the max-payne-collection profile.
"""

import sys
from pathlib import Path

# Modules required for demo, organized by category
REQUIRED_MODULES = [
    ("providers", "provider-anthropic"),
    ("context", "context-persistent"),
    ("orchestrator", "loop-streaming"),
    ("tools", "tool-bash"),
    ("tools", "tool-filesystem"),
    ("tools", "tool-web"),
]


def create_symlink(source: Path, target: Path) -> bool:
    """Create a symlink, handling platform differences.

    Args:
        source: Path to link to (must exist)
        target: Path of symlink to create

    Returns:
        True if successful, False otherwise
    """
    try:
        # Remove existing symlink or directory if present
        if target.exists() or target.is_symlink():
            if target.is_symlink():
                target.unlink()
            else:
                print(f"  Warning: {target.name} exists as regular directory, skipping")
                return False

        # Create symlink
        target.symlink_to(source, target_is_directory=True)
        return True

    except OSError as e:
        if sys.platform == "win32":
            print("  Error: Failed to create symlink (Windows requires admin or Developer Mode)")
            print("    Run as administrator or enable Developer Mode in Windows Settings")
        else:
            print(f"  Error: {e}")
        return False


def main() -> int:
    """Setup demo modules directory with symlinks."""

    # Paths
    demo_dir = Path(__file__).parent
    modules_dir = demo_dir / "modules"

    # Use amplifier-dev modules for API compatibility
    # These match the installed amplifier-core version
    amplifier_dev = Path("/data/repos/msft/amplifier/amplifier-dev")

    print("Setting up demo modules...")
    print(f"Demo directory: {demo_dir}")
    print(f"Module source: {amplifier_dev}")
    print()

    # Verify amplifier-dev exists
    if not amplifier_dev.exists():
        print(f"Error: amplifier-dev not found at {amplifier_dev}")
        print("This demo requires access to the amplifier-dev repository.")
        return 1

    # Create modules directory
    modules_dir.mkdir(exist_ok=True)
    print(f"Created/verified: {modules_dir}")
    print()

    # Create symlinks for each required module
    success_count = 0
    fail_count = 0

    for category, module_name in REQUIRED_MODULES:
        # Target path with standard naming
        target_name = f"amplifier-module-{module_name}"
        target = modules_dir / target_name

        # Find source in amplifier-dev
        source = amplifier_dev / target_name

        # Verify source exists
        if not source.exists():
            print(f"❌ {target_name}")
            print(f"   Module not found at {source}")
            fail_count += 1
            continue

        # Create symlink
        if create_symlink(source, target):
            print(f"✅ {target_name}")
            print(f"   → {source}")
            success_count += 1
        else:
            fail_count += 1

    # Summary
    print()
    print(f"Setup complete: {success_count} modules linked, {fail_count} failed")

    if fail_count > 0:
        print()
        print("Some modules failed to link. Demo may not work correctly.")
        return 1

    print()
    print("✅ Demo is ready! Run with:")
    print("   python demo.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
