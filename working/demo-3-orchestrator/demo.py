"""
Interactive Foreman-Worker Demo

Demonstrates the specialized Foreman-Worker Orchestrator where:
- Foreman handles all user interaction
- Workers run continuously in background
- No workflow YAML needed - pattern is hardcoded
- Much simpler than generic workflow orchestrator

KEY DEMO FLOW - User Input Orchestration:
=========================================
This demo specifically showcases how the foreman coordinates getting user input:

1. Foreman creates tasks for workers
2. Worker starts a task, discovers it needs more info (e.g., database schema)
3. Worker marks task as "pending_user_input" with notes about what's needed
4. Foreman notices the pending task and asks user for the missing info
5. User provides info, foreman updates the task and marks it "open" again
6. Worker picks up the unblocked task and completes it

This demonstrates foreman as the coordinator between autonomous workers and
human users - workers don't talk to users directly, foreman mediates.

Status values:
- open: Available for workers to claim
- in_progress: Worker is actively working on it
- pending_user_input: Worker needs info from user (foreman should ask)
- blocked: Blocked by dependency (another task)
- closed: Completed
"""

import asyncio
import json
import logging
import shutil
import sys
from pathlib import Path


# Add the foreman-worker orchestrator to path
orchestrator_path = Path(__file__).parent / "modules" / "amplifier-module-orchestrator-foreman-worker"
sys.path.insert(0, str(orchestrator_path))

from amplifier_core import ModuleLoader
from amplifier_orchestrator_foreman_worker import ForemanWorkerOrchestrator
from amplifier_orchestrator_foreman_worker import WorkerConfig
from demo_stubs import StubApprovalSystem
from demo_stubs import StubDisplaySystem


def load_mount_plan(mount_plans_dir: Path, profile: str) -> dict:
    """Load mount plan from JSON file."""
    mount_plan_path = mount_plans_dir / f"{profile}.json"
    if not mount_plan_path.exists():
        raise FileNotFoundError(f"Mount plan not found: {mount_plan_path}")
    with open(mount_plan_path) as f:
        return json.load(f)


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


logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Suppress noisy loggers - only show warnings and errors
for logger_name in [
    "httpcore",
    "httpx",
    "anthropic",
    "amplifier_core",
    "amplifier_module_loop_streaming",
    "amplifier_module_context_persistent",
    "amplifier_module_provider_anthropic",
    "amplifier_module_tool_filesystem",
    "amplifier_module_tool_bash",
    "amplifier_module_tool_issue",
    "amplifier_orchestrator_foreman_worker",
]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Delete the .demo-workspace if it exists from prior runs
workspace_dir = Path.cwd() / ".demo-workspace"
if workspace_dir.exists():
    shutil.rmtree(workspace_dir)

work_dir = Path.cwd() / "work"
if work_dir.exists():
    shutil.rmtree(work_dir)


def get_module_search_paths() -> list[Path]:
    """Get module search paths for Amplifier Core."""
    modules_dir = Path(__file__).parent / "modules"

    if not modules_dir.exists():
        raise RuntimeError("Modules directory not found. Run setup:\n  python setup_modules.py")

    return [modules_dir]


async def interactive_demo():
    """Run an interactive demo with simulated user interactions."""
    print(
        f"""
{Color.BOLD}======================================================================{Color.ENDC}
{Color.BOLD}  Foreman-Worker Orchestrator Demo{Color.ENDC}
{Color.BOLD}  Interactive Multi-Agent System{Color.ENDC}
{Color.BOLD}======================================================================{Color.ENDC}
    """
    )

    # Validate API key
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        print(f"{Color.RED}ERROR: Valid ANTHROPIC_API_KEY not set{Color.ENDC}\n")
        print("Please set your API key:")
        print("  export ANTHROPIC_API_KEY='sk-ant-api03-...'")
        print(f"\n{Color.YELLOW}Get your API key from: https://console.anthropic.com/{Color.ENDC}\n")
        return

    print(f"{Color.GREEN}✓ API key validated{Color.ENDC}\n")

    # Set up module loading
    try:
        search_paths = get_module_search_paths()

        # Add module directories to sys.path (required for Amplifier Core)
        for search_path in search_paths:
            for module_dir in search_path.iterdir():
                if module_dir.is_dir() and module_dir.name.startswith("amplifier-module-"):
                    path_str = str(module_dir)
                    if path_str not in sys.path:
                        sys.path.insert(0, path_str)

        loader = ModuleLoader(search_paths=search_paths)
        print(f"{Color.GREEN}✓ Module loader initialized{Color.ENDC}\n")

    except Exception as e:
        print(f"{Color.RED}Failed to initialize module loader: {e}{Color.ENDC}")
        return

    # Create stub systems to suppress warnings
    approval_system = StubApprovalSystem()
    display_system = StubDisplaySystem()

    # Create orchestrator
    print(f"{Color.BLUE}Creating Foreman-Worker Orchestrator...{Color.ENDC}")
    workspace = Path.cwd() / ".demo-workspace"
    workspace.mkdir(exist_ok=True)

    # Load mount plan configurations
    mount_plans_dir = Path(__file__).parent / "mount_plans"
    foreman_config = load_mount_plan(mount_plans_dir, "foreman")
    coding_worker_config = load_mount_plan(mount_plans_dir, "coding-worker")
    research_worker_config = load_mount_plan(mount_plans_dir, "research-worker")

    async with ForemanWorkerOrchestrator(
        loader=loader,
        foreman_config=foreman_config,
        worker_configs=[
            WorkerConfig(name="coding-worker", config=coding_worker_config, count=2),
            WorkerConfig(name="research-worker", config=research_worker_config, count=2),
        ],
        workspace_root=workspace,
        approval_system=approval_system,
        display_system=display_system,
    ) as orchestrator:
        print(f"{Color.GREEN}✓ Orchestrator created{Color.ENDC}")
        print("   Workers: 2x coding-worker, 2x research-worker")
        print(f"   Workspace: {workspace}")
        print(f"   (Session IDs will be shown after first message initializes sessions)\n")

        print(f"{Color.BOLD}Starting interactive demo...{Color.ENDC}\n")
        print("=" * 70)

        # Simulated user interactions
        # NOTE: This demo showcases the "pending_user_input" workflow:
        # - Worker starts "session management" task
        # - Worker discovers it needs database schema from user
        # - Worker marks task as "pending_user_input" with blocking_notes
        # - Foreman notices and asks user for the schema
        # - User provides schema, foreman updates task back to "open"
        # - Worker completes the task
        user_interactions = [
            {
                "message": (
                    "Create 4 demo issues:\n"
                    "1. CODING: Fix auth bug - the login endpoint returns 500 errors\n"
                    "2. CODING: Implement session management - IMPORTANT: This task REQUIRES the user's "
                    "actual database schema before any work can begin. The worker MUST mark this as "
                    "pending_user_input and request the exact table structure. DO NOT make up a schema.\n"
                    "3. RESEARCH: Competitor analysis - analyze 3 competitors\n"
                    "4. RESEARCH: User research - identify target user personas"
                ),
                "description": "User asks foreman to create initial work queue",
            },
            {
                "message": "What's the current status? Are any tasks waiting for input from me?",
                "description": "User checks on worker progress - foreman should notice pending_user_input",
                "wait_before": 30,  # Let workers claim tasks - session mgmt worker should request schema
            },
            {
                "message": "Here's the database schema: users table (id, email, password_hash), sessions table (id, user_id, token, expires_at)",
                "description": "User provides the schema info that was requested",
                "wait_before": 10,  # Short wait since foreman already asked
            },
            {
                "message": "Give me a final summary of all work completed",
                "description": "User requests final status",
                "wait_before": 60,  # Workers need time to finish all 4 tasks
            },
        ]

        for i, interaction in enumerate(user_interactions):
            # Wait if requested (to let workers process)
            if "wait_before" in interaction:
                wait_time = interaction["wait_before"]
                print(f"\n{Color.YELLOW}[Waiting {wait_time}s for workers to process...]{Color.ENDC}")
                print(
                    f"{Color.CYAN}(Workers are continuously claiming and completing issues in background){Color.ENDC}\n"
                )
                await asyncio.sleep(wait_time)

            # User sends message
            print(f"\n{'=' * 70}")
            print(f"{Color.BOLD}USER INTERACTION {i + 1}:{Color.ENDC} {interaction['description']}")
            print(f"{'=' * 70}\n")
            print(f"{Color.YELLOW}User:{Color.ENDC} {interaction['message']}\n")

            # Foreman responds
            print(f"{Color.CYAN}Foreman is processing...{Color.ENDC}\n")

            try:
                response = await orchestrator.execute_user_message(interaction["message"])

                print(f"{Color.GREEN}Foreman:{Color.ENDC} {response}\n")

                # Print session IDs after first interaction (when everything is initialized)
                if i == 0:
                    print(f"{Color.BLUE}{'=' * 70}{Color.ENDC}")
                    print(f"{Color.BLUE}SESSION IDs:{Color.ENDC}")
                    print(f"   Foreman: {orchestrator.foreman_session.session_id}")
                    # Workers may take a moment to initialize, print what we have
                    await asyncio.sleep(2)  # Brief wait for workers to start
                    for worker_id, session_id in orchestrator.worker_session_ids.items():
                        print(f"   {worker_id}: {session_id}")
                    print(f"{Color.BLUE}{'=' * 70}{Color.ENDC}\n")

            except Exception as e:
                print(f"{Color.RED}Error: {e}{Color.ENDC}\n")
                import traceback

                traceback.print_exc()

        # Poll for completion instead of fixed wait
        print(f"\n{Color.YELLOW}[Polling for task completion...]{Color.ENDC}")
        max_wait = 120  # Maximum 2 minutes
        poll_interval = 10  # Check every 10 seconds
        waited = 0
        zero_count = 0  # Track consecutive "0" responses

        while waited < max_wait:
            await asyncio.sleep(poll_interval)
            waited += poll_interval

            # Ask foreman for status
            status_response = await orchestrator.execute_user_message(
                "How many tasks are still open or in_progress? Reply with just the number."
            )

            # Extract just the first line for display
            first_line = status_response.strip().split("\n")[0][:50]
            print(f"{Color.CYAN}[{waited}s] Status: {first_line}{Color.ENDC}")

            # Check if response indicates 0 remaining tasks
            # Look for "0" at start or as the only content, or keywords indicating completion
            response_lower = status_response.lower().strip()
            if (
                response_lower.startswith("0")
                or response_lower == "0"
                or "0 tasks" in response_lower
                or "no tasks" in response_lower
                or "all tasks" in response_lower
                and "closed" in response_lower
            ):
                zero_count += 1
                if zero_count >= 2:  # Require 2 consecutive "0" responses to confirm
                    print(f"{Color.GREEN}All tasks complete!{Color.ENDC}")
                    break
            else:
                zero_count = 0  # Reset if we get a non-zero response
        else:
            print(f"{Color.YELLOW}Max wait time reached. Some tasks may still be in progress.{Color.ENDC}")

        print("=" * 70)
        print(f"\n{Color.GREEN}{Color.BOLD}Demo complete!{Color.ENDC}")
        print(f"{Color.CYAN}Workers processed tasks continuously throughout the demo.{Color.ENDC}")
        print(f"{Color.CYAN}Shutting down foreman and workers...{Color.ENDC}\n")

    # Context manager handles shutdown
    print(f"{Color.GREEN}✓ All agents shut down gracefully{Color.ENDC}\n")

    print(
        f"""
{Color.BOLD}======================================================================{Color.ENDC}
{Color.BOLD}Key Features Demonstrated:{Color.ENDC}
{Color.BOLD}======================================================================{Color.ENDC}

{Color.CYAN}✓ Foreman as User Interface{Color.ENDC}
  - All user messages go to foreman
  - Foreman creates tasks, reports status, unblocks work
  - Conversational, context-aware responses

{Color.CYAN}✓ Autonomous Workers{Color.ENDC}
  - Run continuously in background
  - Automatically claim and process available work
  - No manual coordination needed

{Color.CYAN}✓ No Workflow Files{Color.ENDC}
  - Pattern hardcoded in orchestrator
  - Just configure worker types and counts
  - Simpler than generic workflow orchestrator

{Color.CYAN}✓ Real-time Coordination{Color.ENDC}
  - Workers process while foreman interacts with user
  - Shared state via issue queue (tool-issue)
  - Blocking/unblocking happens naturally

{Color.CYAN}✓ Clean Lifecycle{Color.ENDC}
  - Context manager for automatic cleanup
  - Graceful worker shutdown
  - Proper session cleanup

{Color.BOLD}======================================================================{Color.ENDC}

{Color.YELLOW}Compare with other demos:{Color.ENDC}
  • demo.py               - Manual orchestration (explicit asyncio)
  • demo_orchestrated.py  - Generic workflow orchestrator (YAML-driven)
  • demo_foreman_worker.py - Specialized foreman-worker (this demo)

{Color.YELLOW}When to use Foreman-Worker Orchestrator:{Color.ENDC}
  ✓ Task queue processing systems
  ✓ Interactive agent management
  ✓ Continuous background processing
  ✓ User-directed multi-agent work

{Color.YELLOW}When to use Workflow Orchestrator:{Color.ENDC}
  ✓ Complex multi-phase workflows
  ✓ Different patterns (not just foreman-worker)
  ✓ Workflows that change frequently
  ✓ Batch processing with defined end
    """
    )


if __name__ == "__main__":
    asyncio.run(interactive_demo())
