"""
Interactive Foreman-Worker Demo

Demonstrates the specialized Foreman-Worker Orchestrator where:
- Foreman handles all user interaction
- Workers run continuously in background
- No workflow YAML needed - pattern is hardcoded
- Much simpler than generic workflow orchestrator
"""

import asyncio
import logging
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


logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Delete the .demo-workspace if it exists from prior runs
workspace_dir = Path.cwd() / ".demo-workspace"
if workspace_dir.exists():
    import shutil

    shutil.rmtree(workspace_dir)


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

    async with ForemanWorkerOrchestrator(
        loader=loader,
        mount_plans_dir=Path(__file__).parent / "mount_plans",
        foreman_profile="foreman",
        worker_configs=[
            WorkerConfig(profile="coding-worker", count=2),
            WorkerConfig(profile="research-worker", count=1),
        ],
        workspace_root=workspace,
        approval_system=approval_system,
        display_system=display_system,
    ) as orchestrator:
        print(f"{Color.GREEN}✓ Orchestrator initialized{Color.ENDC}")
        print("   Foreman: foreman")
        print("   Workers: 2x coding-worker, 1x research-worker")
        print(f"   Workspace: {workspace}\n")

        print(f"{Color.BOLD}Starting interactive demo...{Color.ENDC}\n")
        print("=" * 70)

        # Simulated user interactions
        user_interactions = [
            {
                "message": "Create 4 demo issues: 2 coding tasks (fix auth, add password reset), 2 research tasks (competitor analysis, user research)",
                "description": "User asks foreman to create initial work queue",
            },
            {
                "message": "What's the current status? How many issues are open, in progress, and completed?",
                "description": "User checks on worker progress",
                "wait_before": 30,  # Let workers complete multiple workflow cycles
            },
            {
                "message": "One task needs database schema. Here's the schema: users table (id, email, password_hash), sessions table (id, user_id, token, expires_at)",
                "description": "User unblocks a task that needs information",
                "wait_before": 20,
            },
            {
                "message": "Give me a final summary of all work completed",
                "description": "User requests final status",
                "wait_before": 20,
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

            except Exception as e:
                print(f"{Color.RED}Error: {e}{Color.ENDC}\n")
                import traceback

                traceback.print_exc()

        # Final wait to let workers finish
        print(f"\n{Color.YELLOW}[Waiting 30s for workers to finish remaining work...]{Color.ENDC}\n")
        await asyncio.sleep(30)

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
