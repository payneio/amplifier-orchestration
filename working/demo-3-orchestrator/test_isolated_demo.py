"""
Isolated test replicating the exact demo scenario.
Comprehensive logging to see where workers stop/fail.
"""

import asyncio
import logging
import sys
from pathlib import Path

# MAX logging
logging.basicConfig(
    level=logging.INFO,  # INFO level to reduce noise but see key events
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Reduce library noise
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)

# Add modules to path
orchestrator_path = Path(__file__).parent / "modules" / "amplifier-module-orchestrator-foreman-worker"
sys.path.insert(0, str(orchestrator_path))

modules_dir = Path(__file__).parent / "modules"
for module_dir in modules_dir.iterdir():
    if module_dir.is_dir() and module_dir.name.startswith("amplifier-module-"):
        sys.path.insert(0, str(module_dir))

from amplifier_core import ModuleLoader
from amplifier_orchestrator_foreman_worker import ForemanWorkerOrchestrator
from amplifier_orchestrator_foreman_worker import WorkerConfig
from demo_stubs import StubApprovalSystem
from demo_stubs import StubDisplaySystem


async def test_isolated_demo():
    """Replicate exact demo scenario with detailed logging."""
    print("=" * 70)
    print("ISOLATED DEMO TEST - Replicating Full Scenario")
    print("=" * 70)
    print()

    loader = ModuleLoader(search_paths=[modules_dir])
    workspace = Path.cwd() / ".demo-workspace"
    # Remove existing workspace for clean test
    if workspace.exists():
        import shutil

        shutil.rmtree(workspace)
    workspace.mkdir(exist_ok=True)

    print("1. Creating orchestrator...")
    async with ForemanWorkerOrchestrator(
        loader=loader,
        mount_plans_dir=Path("mount_plans"),
        foreman_profile="foreman",
        worker_configs=[
            WorkerConfig(profile="coding-worker", count=2),
            WorkerConfig(profile="research-worker", count=1),
        ],
        workspace_root=workspace,
        approval_system=StubApprovalSystem(),
        display_system=StubDisplaySystem(),
    ) as orch:
        print("2. Orchestrator initialized")
        print(f"   Worker tasks: {len(orch.worker_tasks)}")
        print(f"   Tasks running: {[t.get_name() for t in orch.worker_tasks if not t.done()]}")
        print()

        # Step 1: Create issues
        print("=" * 70)
        print("STEP 1: Foreman creates issues")
        print("=" * 70)
        response = await orch.execute_user_message(
            "Create 4 demo issues: 2 coding (fix auth, add password reset), "
            "2 research (competitor analysis, user research)"
        )
        print(f"Foreman: {response[:200]}...")
        print()

        # Check worker task status
        print("Worker task status after issue creation:")
        for task in orch.worker_tasks:
            status = "done" if task.done() else "running"
            print(f"  {task.get_name()}: {status}")
            if task.done():
                try:
                    result = task.result()
                    print(f"    Result: {result}")
                except Exception as e:
                    print(f"    Exception: {e}")
        print()

        # Step 2: Wait and check
        print("=" * 70)
        print("STEP 2: Wait 30s for workers to process")
        print("=" * 70)
        print("Waiting...")
        await asyncio.sleep(30)
        print()

        # Check actual database
        import json

        issues_file = workspace / ".amplifier/issues/issues.jsonl"
        if issues_file.exists():
            lines = issues_file.read_text().strip().split("\n")
            issues = [json.loads(l) for l in lines if l.strip()]
            statuses = {}
            for issue in issues:
                status = issue["status"]
                statuses[status] = statuses.get(status, 0) + 1

            print(f"DATABASE shows: {statuses}")
            print(f"  Open: {statuses.get('open', 0)}")
            print(f"  In Progress: {statuses.get('in_progress', 0)}")
            print(f"  Closed: {statuses.get('closed', 0)}")
        print()

        # Ask foreman for status
        response = await orch.execute_user_message(
            "What's the current status? How many issues are open, in progress, and closed?"
        )
        print(f"Foreman says: {response[:300]}...")
        print()

        # Check worker tasks again
        print("Worker task status after 30s:")
        for task in orch.worker_tasks:
            status = "done" if task.done() else "running"
            print(f"  {task.get_name()}: {status}")
        print()

        # Step 3: Wait more and final check
        print("=" * 70)
        print("STEP 3: Wait another 30s")
        print("=" * 70)
        await asyncio.sleep(30)

        # Final database check
        if issues_file.exists():
            lines = issues_file.read_text().strip().split("\n")
            issues = [json.loads(l) for l in lines if l.strip()]
            statuses = {}
            for issue in issues:
                status = issue["status"]
                statuses[status] = statuses.get(status, 0) + 1

            print(f"\nFINAL DATABASE shows: {statuses}")

            # Show details
            print("\nIssue details:")
            for issue in issues:
                assignee = issue.get("assignee", "unassigned")
                print(f"  {issue['status']:12} {str(assignee):20} {issue['title'][:35]}")

        # Final foreman check
        print()
        response = await orch.execute_user_message("Give final summary of completed work")
        print(f"Foreman final: {response[:300]}...")

    print("\n" + "=" * 70)
    print("Test Complete")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_isolated_demo())
