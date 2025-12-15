"""
Minimal test: Can ONE worker claim and complete ONE issue?

This isolates whether the problem is:
- Tool usage
- Worker prompts
- Orchestrator
- Something else
"""

import asyncio
import json
import sys
from pathlib import Path

from amplifier_core import AmplifierSession
from amplifier_core import ModuleLoader


def get_module_search_paths() -> list[Path]:
    """Get module search paths."""
    modules_dir = Path(__file__).parent / "modules"
    if not modules_dir.exists():
        raise RuntimeError("Modules directory not found")

    return [modules_dir]


def load_mount_plan(name: str) -> dict:
    """Load mount plan."""
    path = Path(__file__).parent / "mount_plans" / f"{name}.json"
    with open(path) as f:
        return json.load(f)


async def test_worker():
    """Test if a single worker can claim and complete an issue."""
    print("\n" + "=" * 70)
    print("MINIMAL WORKER TEST")
    print("=" * 70 + "\n")

    # Setup
    search_paths = get_module_search_paths()
    for search_path in search_paths:
        for module_dir in search_path.iterdir():
            if module_dir.is_dir() and module_dir.name.startswith("amplifier-module-"):
                path_str = str(module_dir)
                if path_str not in sys.path:
                    sys.path.insert(0, path_str)

    loader = ModuleLoader(search_paths=search_paths)
    workspace = Path.cwd() / ".demo-workspace"
    if workspace.exists():
        import shutil

        shutil.rmtree(workspace)
    workspace.mkdir(exist_ok=True)

    print("✓ Module loader initialized\n")

    # Step 1: Create ONE test issue manually
    print("Step 1: Creating ONE test issue...")
    foreman_config = load_mount_plan("foreman")

    async with AmplifierSession(foreman_config, loader=loader) as session:
        result = await session.execute(
            "Create ONE test issue: title='Test coding task', "
            "issue_type='task', priority=1, "
            "metadata={'category': 'coding'}"
        )
        print(f"✓ Issue created: {result[:200]}\n")

    # Step 2: Try to have ONE worker claim and complete it
    print("Step 2: Starting ONE coding worker...")
    worker_config = load_mount_plan("coding-worker")

    async with AmplifierSession(worker_config, loader=loader) as session:
        print("✓ Worker session created\n")

        for iteration in range(3):
            print(f"--- Iteration {iteration + 1} ---")

            # Use the EXACT prompt from working demo.py
            prompt = """You are test-worker, a coding specialist.

Task: Find and work on one issue

1. Use the issue tool to list ready issues (filter: status=open)
2. Look for issues where metadata.category == "coding"
3. If you find one:
   - Update it to status=in_progress, assignee='test-worker'
   - Analyze the task
   - Complete your work and close the issue with a brief result
4. If no issues available for you, respond with "No work available"

Process ONE issue then stop."""

            result = await session.execute(prompt)

            print(f"Worker response ({len(result)} chars):")
            print(f"{result[:500]}\n")

            if "No work available" in result or "no work" in result.lower():
                print("Worker says no work available")
            else:
                print(f"Worker appears to have processed something! ({result[:100]})")
                break

            await asyncio.sleep(1)

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(test_worker())
