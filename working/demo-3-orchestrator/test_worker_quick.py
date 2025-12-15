"""Quick test - just check if workers call tools"""

import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(name)s - %(message)s')

orchestrator_path = Path(__file__).parent / "modules" / "amplifier-module-orchestrator-foreman-worker"
sys.path.insert(0, str(orchestrator_path))

from amplifier_orchestrator_foreman_worker import ForemanWorkerOrchestrator, WorkerConfig
from amplifier_core import ModuleLoader
from demo_stubs import StubApprovalSystem, StubDisplaySystem


def get_module_search_paths() -> list[Path]:
    modules_dir = Path(__file__).parent / "modules"
    return [modules_dir]


async def test():
    print("\n" + "="*70)
    print("TESTING: Do workers call tools?")
    print("="*70 + "\n")

    search_paths = get_module_search_paths()
    for search_path in search_paths:
        for module_dir in search_path.iterdir():
            if module_dir.is_dir() and module_dir.name.startswith("amplifier-module-"):
                path_str = str(module_dir)
                if path_str not in sys.path:
                    sys.path.insert(0, path_str)

    loader = ModuleLoader(search_paths=search_paths)
    workspace = Path.cwd() / ".demo-workspace"
    workspace.mkdir(exist_ok=True)

    print("Creating orchestrator...")
    orchestrator = ForemanWorkerOrchestrator(
        loader=loader,
        mount_plans_dir=Path(__file__).parent / "mount_plans",
        foreman_profile="foreman",
        worker_configs=[WorkerConfig(profile="coding-worker", count=1)],
        workspace_root=workspace,
        approval_system=StubApprovalSystem(),
        display_system=StubDisplaySystem()
    )

    print("Initializing (this triggers lazy init)...")
    try:
        await orchestrator.__aenter__()

        # Trigger initialization
        print("\nSending message to trigger init...")
        await asyncio.wait_for(
            orchestrator.execute_user_message("Create issue: Fix authentication bug (category: coding)"),
            timeout=10.0
        )
        print("✓ Foreman responded")

        # Give worker time to see the issue and act
        print("\nWaiting 5s for worker to process...")
        await asyncio.sleep(5)

    except asyncio.TimeoutError:
        print("✗ Timed out waiting for foreman")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        await orchestrator.__aexit__(None, None, None)

    print("\n" + "="*70)
    print("Check logs above for worker tool calls")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test())
