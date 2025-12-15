"""
Diagnostic script to understand why workers don't execute in orchestrator.

This adds extensive logging at every critical point to see exactly what's happening.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from amplifier_core import AmplifierSession, ModuleLoader

# Enable DEBUG logging to see EVERYTHING
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)


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


async def worker_loop_isolated(worker_id: str, profile: str, loader, cycles: int = 3):
    """Isolated worker loop with extensive logging."""
    logger.info(f"=== WORKER {worker_id} STARTING ===")

    try:
        logger.info(f"{worker_id}: Loading mount plan for profile: {profile}")
        config = load_mount_plan(profile)
        logger.info(f"{worker_id}: Mount plan loaded")

        worker_category = "coding" if "coding" in profile else "research"
        logger.info(f"{worker_id}: Category determined as: {worker_category}")

        logger.info(f"{worker_id}: Creating AmplifierSession...")
        async with AmplifierSession(config, loader=loader) as session:
            logger.info(f"{worker_id}: Session created, getting context...")

            context = session.coordinator.get("context")
            if not context:
                raise RuntimeError(f"{worker_id}: No context manager mounted!")
            logger.info(f"{worker_id}: Context retrieved: {type(context)}")

            # System instructions
            instructions = (
                f"You are {worker_id}, a {worker_category} worker.\n\n"
                "WORKFLOW:\n"
                "1. List open issues with issue_manager\n"
                f"2. Find issues where metadata.category == '{worker_category}'\n"
                "3. If found: Claim it (status=in_progress, assignee=YOU)\n"
                "4. Do the work\n"
                "5. Close the issue\n"
                "6. If no work: Respond 'no work'\n\n"
                "Execute ALL steps in ONE turn."
            )

            logger.info(f"{worker_id}: Adding system instructions...")
            await context.add_message({"role": "system", "content": instructions})
            logger.info(f"{worker_id}: System instructions added")

            # Execute cycles
            for i in range(cycles):
                logger.info(f"{worker_id}: === CYCLE {i+1}/{cycles} ===")

                prompt = (
                    f"Execute your workflow:\n"
                    f"1. List open issues\n"
                    f"2. Claim ONE {worker_category} issue\n"
                    f"3. Complete and close it\n"
                )

                logger.info(f"{worker_id}: Calling session.execute()...")
                logger.info(f"{worker_id}: Prompt: {prompt[:100]}...")

                result = await session.execute(prompt)

                logger.info(f"{worker_id}: Execute returned ({len(result)} chars)")
                logger.info(f"{worker_id}: Result preview: {result[:200]}")

                if "no work" in result.lower():
                    logger.info(f"{worker_id}: No work available")
                else:
                    logger.info(f"{worker_id}: Appears to have done work!")

                logger.info(f"{worker_id}: Sleeping 2s before next cycle...")
                await asyncio.sleep(2)

            logger.info(f"{worker_id}: All cycles complete")

    except Exception as e:
        logger.error(f"{worker_id}: EXCEPTION: {e}", exc_info=True)
        raise


async def test_isolated_worker():
    """Test worker in isolation."""
    logger.info("=== DIAGNOSTIC TEST START ===")

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
    workspace.mkdir(exist_ok=True)

    logger.info("Module loader initialized")

    # Create test issue
    logger.info("Creating test issue via foreman...")
    foreman_config = load_mount_plan("foreman")

    async with AmplifierSession(foreman_config, loader=loader) as session:
        result = await session.execute(
            "Create one test issue: title='Diagnostic test', "
            "issue_type='task', priority=1, "
            "metadata={'category': 'coding'}"
        )
        logger.info(f"Foreman created issue: {result[:100]}")

    # Run worker
    logger.info("Starting diagnostic worker...")
    await worker_loop_isolated("diagnostic-worker", "coding-worker", loader, cycles=2)

    logger.info("=== DIAGNOSTIC TEST COMPLETE ===")

    # Check events file
    events_file = workspace / ".amplifier" / "issues" / "events.jsonl"
    if events_file.exists():
        logger.info(f"\nEvents file contents:")
        with open(events_file) as f:
            for line in f:
                event = json.loads(line)
                logger.info(f"  Event: {event['event_type']} by {event['actor']}")


async def test_background_task_worker():
    """Test worker as background task (like orchestrator does)."""
    logger.info("=== BACKGROUND TASK TEST START ===")

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
    workspace.mkdir(exist_ok=True)

    logger.info("Module loader initialized")

    # Create test issue
    logger.info("Creating test issue...")
    foreman_config = load_mount_plan("foreman")
    async with AmplifierSession(foreman_config, loader=loader) as session:
        result = await session.execute(
            "Create one test issue: title='Background task test', "
            "issue_type='task', priority=1, "
            "metadata={'category': 'coding'}"
        )
        logger.info(f"Issue created: {result[:100]}")

    # Launch worker as background task
    logger.info("Launching worker as background task...")
    shutdown_event = asyncio.Event()

    async def worker_task():
        logger.info("Worker task STARTED")
        try:
            config = load_mount_plan("coding-worker")
            worker_category = "coding"

            async with AmplifierSession(config, loader=loader) as session:
                context = session.coordinator.get("context")
                instructions = f"You are bg-worker, a {worker_category} worker. Complete available work."
                await context.add_message({"role": "system", "content": instructions})

                for i in range(3):
                    if shutdown_event.is_set():
                        break

                    logger.info(f"bg-worker: Cycle {i+1}")
                    prompt = "List issues, claim and complete ONE coding issue, or respond 'no work'"
                    result = await session.execute(prompt)
                    logger.info(f"bg-worker: Result ({len(result)} chars): {result[:200]}")

                    await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"bg-worker EXCEPTION: {e}", exc_info=True)

        logger.info("Worker task COMPLETED")

    task = asyncio.create_task(worker_task(), name="bg-worker")
    logger.info("Background task created")

    # Wait for worker to run
    logger.info("Waiting 10s for background task to execute...")
    await asyncio.sleep(10)

    # Check task status
    logger.info(f"Task status: done={task.done()}, cancelled={task.cancelled()}")
    if task.done():
        try:
            result = task.result()
            logger.info(f"Task result: {result}")
        except Exception as e:
            logger.error(f"Task exception: {e}")

    # Shutdown
    shutdown_event.set()
    await task

    logger.info("=== BACKGROUND TASK TEST COMPLETE ===")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("DIAGNOSTIC TESTS")
    print("="*70 + "\n")

    print("\nTest 1: Isolated worker (direct await)")
    print("-" * 70)
    asyncio.run(test_isolated_worker())

    print("\n\nTest 2: Background task worker (like orchestrator)")
    print("-" * 70)
    asyncio.run(test_background_task_worker())

    print("\n" + "="*70)
    print("DIAGNOSTICS COMPLETE")
    print("="*70 + "\n")
