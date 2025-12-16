"""
Multi-Worker Orchestration Demo - Using Real Amplifier Core and tool-issue

This demo uses actual Amplifier Core sessions, mount plans, and tool-issue
to demonstrate the multi-worker pattern with blocking/unblocking.

Workers and foreman interact with issues through natural language prompts,
letting the LLM decide when to call tool-issue operations.
"""

import asyncio
import json
import sys
from pathlib import Path

from amplifier_core import AmplifierSession, ModuleLoader


# ANSI colors
class Color:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def get_module_search_paths() -> list[Path]:
    """Get module search paths.

    Expects modules in demo/modules/ with standard naming:
    - amplifier-module-provider-anthropic/
    - amplifier-module-tool-bash/
    - amplifier-module-tool-issue/
    - etc.

    Run `python setup_modules.py` to create these.
    """
    modules_dir = Path(__file__).parent / "modules"

    if not modules_dir.exists():
        raise RuntimeError("Modules directory not found. Run setup:\n  python setup_modules.py")

    return [modules_dir]


def load_mount_plan(name: str) -> dict:
    """Load a mount plan from demo/mount_plans/"""
    mount_plan_path = Path(__file__).parent / "mount_plans" / f"{name}.json"
    with open(mount_plan_path) as f:
        return json.load(f)


async def foreman_create_issues(loader: ModuleLoader):
    """Foreman creates initial issues using tool-issue."""
    print(f"\n{Color.BLUE}{Color.BOLD}=== FOREMAN: Creating Issues ==={Color.ENDC}")

    config = load_mount_plan("foreman")

    async with AmplifierSession(config, loader=loader) as session:
        foreman_session_id = getattr(session, 'session_id', 'unknown')
        print(f"   Foreman session_id: {foreman_session_id}")
        prompt = """Create 4 demo issues using the issue tool:

1. Title: "Fix login authentication bug"
   - Type: task, Priority: 1
   - Metadata: {"worker_type": "coding", "demo_id": "T1"}

2. Title: "Research competitor pricing models"
   - Type: task, Priority: 1
   - Metadata: {"worker_type": "research", "demo_id": "T2"}

3. Title: "Add password reset feature"
   - Type: task, Priority: 1
   - Metadata: {"worker_type": "coding", "demo_id": "T3"}

4. Title: "Optimize database queries - will need endpoint priorities"
   - Type: task, Priority: 1
   - Metadata: {"worker_type": "coding", "demo_id": "T4", "needs_input": true}

After creating these, list all issues to confirm they were created."""

        result = await session.execute(prompt)
        print(f"{Color.GREEN}Issues created successfully{Color.ENDC}")
        print(result[:200] + "..." if len(result) > 200 else result)


async def worker_process_work(worker_id: str, worker_type: str, loader: ModuleLoader):
    """Worker claims and completes issues using tool-issue."""
    print(f"\n{Color.GREEN}{Color.BOLD}=== {worker_type.upper()}-WORKER ({worker_id}): Starting ==={Color.ENDC}")

    config = load_mount_plan(f"{worker_type}-worker")

    async with AmplifierSession(config, loader=loader) as session:
        worker_session_id = getattr(session, 'session_id', 'unknown')
        print(f"   {worker_id} session_id: {worker_session_id}", flush=True)
        for iteration in range(3):
            print(f"\n{Color.YELLOW}{worker_id}: Iteration {iteration + 1}{Color.ENDC}")

            prompt = f"""You are {worker_id}, a {worker_type} specialist.

Task: Find and work on one issue

1. Use the issue tool to list ready issues (filter: status=open)
2. Look for issues where metadata.worker_type == "{worker_type}"
3. If you find one:
   - Update it to status=in_progress
   - Analyze the task
   - If you need information (e.g., the task mentions "endpoint priorities"), update status to blocked with blocking_notes explaining what you need
   - Otherwise, complete your work and close the issue with a brief result
4. If no issues available for you, respond with "No work available"

Process ONE issue then stop."""

            result = await session.execute(prompt)

            # Check if worker found work
            if "No work available" in result or "no issues" in result.lower():
                print(f"{Color.YELLOW}{worker_id}: No work available{Color.ENDC}")
                break

            print(
                f"{Color.CYAN}{worker_id}: {result[:150]}...{Color.ENDC}"
                if len(result) > 150
                else f"{Color.CYAN}{worker_id}: {result}{Color.ENDC}"
            )

            await asyncio.sleep(2)


async def foreman_check_blocked(loader: ModuleLoader):
    """Foreman checks for and unblocks blocked issues."""
    print(f"\n{Color.BLUE}{Color.BOLD}=== FOREMAN: Checking for Blocked Issues ==={Color.ENDC}")

    config = load_mount_plan("foreman")

    async with AmplifierSession(config, loader=loader) as session:
        foreman_session_id = getattr(session, 'session_id', 'unknown')
        print(f"   Foreman (blocked check) session_id: {foreman_session_id}")
        for check_num in range(3):
            await asyncio.sleep(5)

            print(f"\n{Color.BLUE}Foreman: Check #{check_num + 1}{Color.ENDC}")

            prompt = """Check for blocked issues using the issue tool.

1. List issues with status=blocked
2. For each blocked issue:
   - Read the blocking_notes
   - If it asks about "endpoint priorities", update the issue:
     * Set status back to open
     * Add to metadata: {"blocking_answer": "/api/users and /api/orders"}
   - If it asks something else, provide a reasonable answer

3. After unblocking, list all issues to show current status

Report what you found and what you did."""

            result = await session.execute(prompt)
            print(f"{Color.GREEN}Foreman check complete{Color.ENDC}")

            if "No blocked issues" in result or "no issues" in result.lower():
                print(f"{Color.YELLOW}No blocked issues found{Color.ENDC}")
            else:
                print(
                    f"{Color.CYAN}{result[:200]}...{Color.ENDC}" if len(result) > 200 else f"{Color.CYAN}{result}{Color.ENDC}"
                )


async def main():
    """Main orchestration."""
    print(
        f"""
{Color.BOLD}======================================================================{Color.ENDC}
{Color.BOLD}  Multi-Worker Orchestration Demo{Color.ENDC}
{Color.BOLD}  Using Real Amplifier Core + tool-issue{Color.ENDC}
{Color.BOLD}======================================================================{Color.ENDC}
    """
    )

    workspace = Path.cwd() / ".demo-workspace"
    workspace.mkdir(exist_ok=True)
    print(f"Workspace: {workspace}")

    # Set up module loading
    try:
        search_paths = get_module_search_paths()
        print(f"Module search paths: {[str(p) for p in search_paths]}")

        # Add module directories to sys.path
        for search_path in search_paths:
            for module_dir in search_path.iterdir():
                if module_dir.is_dir() and module_dir.name.startswith("amplifier-module-"):
                    path_str = str(module_dir)
                    if path_str not in sys.path:
                        sys.path.insert(0, path_str)

        loader = ModuleLoader(search_paths=search_paths)
        print("Module loader initialized")

    except Exception as e:
        print(f"{Color.RED}Failed to initialize module loader: {e}{Color.ENDC}")
        return

    # Phase 1: Foreman creates issues
    await foreman_create_issues(loader)

    # Phase 2: Workers process in parallel
    print(f"\n{Color.BOLD}=== Phase 2: Workers Processing ==={Color.ENDC}")
    worker_tasks = [
        asyncio.create_task(worker_process_work("coding-worker-1", "coding", loader)),
        asyncio.create_task(worker_process_work("coding-worker-2", "coding", loader)),
        asyncio.create_task(worker_process_work("research-worker-1", "research", loader)),
    ]

    # Give workers time to process
    await asyncio.sleep(10)

    # Phase 3: Foreman checks and unblocks
    await foreman_check_blocked(loader)

    # Give workers time to pick up unblocked work (if foreman unblocked anything)
    await asyncio.sleep(10)

    # Wait for all workers to finish
    await asyncio.gather(*worker_tasks, return_exceptions=True)

    print(
        f"""
{Color.BOLD}======================================================================{Color.ENDC}
{Color.BOLD}Demo complete!{Color.ENDC}
{Color.BOLD}======================================================================{Color.ENDC}
    """
    )


if __name__ == "__main__":
    asyncio.run(main())
