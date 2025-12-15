"""
Test if worker logs are visible
"""

import asyncio
import logging
import sys
from pathlib import Path

# Configure logging FIRST - before any imports
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)

# Add the foreman-worker orchestrator to path
orchestrator_path = Path(__file__).parent / "modules" / "amplifier-module-orchestrator-foreman-worker"
sys.path.insert(0, str(orchestrator_path))

from amplifier_orchestrator_foreman_worker import (
    ForemanWorkerOrchestrator,
    WorkerConfig
)
from amplifier_core import ModuleLoader
from demo_stubs import StubApprovalSystem, StubDisplaySystem


def get_module_search_paths() -> list[Path]:
    """Get module search paths for Amplifier Core."""
    modules_dir = Path(__file__).parent / "modules"
    return [modules_dir]


async def test_worker_startup():
    """Test that workers actually start and log messages."""
    print("=" * 70)
    print("TESTING WORKER STARTUP AND LOGGING")
    print("=" * 70)

    # Set up module loading
    search_paths = get_module_search_paths()
    for search_path in search_paths:
        for module_dir in search_path.iterdir():
            if module_dir.is_dir() and module_dir.name.startswith("amplifier-module-"):
                path_str = str(module_dir)
                if path_str not in sys.path:
                    sys.path.insert(0, path_str)

    loader = ModuleLoader(search_paths=search_paths)

    approval_system = StubApprovalSystem()
    display_system = StubDisplaySystem()

    workspace = Path.cwd() / ".demo-workspace"
    workspace.mkdir(exist_ok=True)

    print("\nCreating orchestrator with 1 worker...")

    async with ForemanWorkerOrchestrator(
        loader=loader,
        mount_plans_dir=Path(__file__).parent / "mount_plans",
        foreman_profile="foreman",
        worker_configs=[
            WorkerConfig(profile="coding-worker", count=1),
        ],
        workspace_root=workspace,
        approval_system=approval_system,
        display_system=display_system
    ) as orchestrator:
        print("✓ Orchestrator created")

        print("\nSending first message to trigger lazy initialization...")
        response = await orchestrator.execute_user_message("Create a demo issue")
        print(f"✓ Got response (length: {len(response)})")

        print("\nWaiting 5 seconds for worker to log messages...")
        await asyncio.sleep(5)

        print("\n✓ Test complete - check logs above for worker messages")


if __name__ == "__main__":
    asyncio.run(test_worker_startup())
