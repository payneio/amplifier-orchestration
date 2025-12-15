"""
Multi-Worker Orchestration Demo - Using Multi-Context Orchestrator

This demo uses the new amplifier-module-orchestrator-multi-context to manage
the foreman-worker workflow declaratively through a YAML configuration.

Compare with demo.py to see the difference:
- demo.py: Manual orchestration with explicit session management
- demo_orchestrated.py: Declarative workflow, orchestrator handles everything
"""

import asyncio
import logging
import sys
from pathlib import Path

# Configure logging at DEBUG level to see all trace messages
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Add the multi-context orchestrator module to path
orchestrator_path = Path(__file__).parent / "modules" / "amplifier-module-orchestrator-multi-context"
sys.path.insert(0, str(orchestrator_path))

from amplifier_core import ModuleLoader
from amplifier_orchestrator_multi_context import MultiContextOrchestrator
from amplifier_orchestrator_multi_context import load_workflow


# ANSI colors for output
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
    """Get module search paths for Amplifier Core."""
    modules_dir = Path(__file__).parent / "modules"

    if not modules_dir.exists():
        raise RuntimeError("Modules directory not found. Run setup:\n  python setup_modules.py")

    return [modules_dir]


async def main():
    """Main entry point."""
    # Set up logging to show orchestrator progress
    import logging

    logging.basicConfig(
        level=logging.ERROR,
        format=f"{Color.CYAN}[%(name)s]{Color.ENDC} {Color.CYAN}[%(levelname)s]{Color.ENDC} %(message)s",
        force=True,
    )

    ## Filter out httpx
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("primp").setLevel(logging.ERROR)
    logging.getLogger("amplifier_core").setLevel(logging.ERROR)
    logging.getLogger("amplifier_module_loop_streaming").setLevel(logging.WARNING)

    print(
        f"""
{Color.BOLD}======================================================================{Color.ENDC}
{Color.BOLD}  Multi-Worker Orchestration Demo{Color.ENDC}
{Color.BOLD}  Using Multi-Context Workflow Orchestrator with REAL Amplifier Core{Color.ENDC}
{Color.BOLD}======================================================================{Color.ENDC}
    """
    )

    # Validate API key early
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        print(f"{Color.RED}ERROR: Valid ANTHROPIC_API_KEY not set{Color.ENDC}\n")
        print("Please set your API key:")
        print("  export ANTHROPIC_API_KEY='sk-ant-api03-...'")
        print("\nOr create a .env file:")
        print("  ANTHROPIC_API_KEY=sk-ant-api03-...")
        print(f"\n{Color.YELLOW}Get your API key from: https://console.anthropic.com/{Color.ENDC}\n")
        return

    print(f"{Color.GREEN}✓ API key validated{Color.ENDC}\n")

    workspace = Path.cwd() / ".demo-workspace"
    workspace.mkdir(exist_ok=True)
    print(f"Workspace: {workspace}\n")

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
        print("Module loader initialized\n")

    except Exception as e:
        print(f"{Color.RED}Failed to initialize module loader: {e}{Color.ENDC}")
        return

    # Load workflow
    print(f"{Color.BLUE}Loading workflow...{Color.ENDC}")
    workflow_path = Path(__file__).parent / "workflows" / "foreman_demo.yaml"

    try:
        workflow = load_workflow(workflow_path)
        print(f"{Color.GREEN}✓ Loaded workflow: {workflow.name}{Color.ENDC}")
        print(f"  Description: {workflow.description}")
        print(f"  Phases: {len(workflow.phases)}")
        for phase in workflow.phases:
            print(f"    - {phase.name} ({phase.execution_mode})")
        print()

    except Exception as e:
        print(f"{Color.RED}Failed to load workflow: {e}{Color.ENDC}")
        return

    # Create orchestrator with real Amplifier Core
    print(f"{Color.BLUE}Creating multi-context orchestrator...{Color.ENDC}")
    mount_plans_dir = Path(__file__).parent / "mount_plans"

    try:
        orchestrator = MultiContextOrchestrator(loader=loader, mount_plans_dir=mount_plans_dir)
        print(f"{Color.GREEN}✓ Orchestrator initialized{Color.ENDC}\n")

    except Exception as e:
        print(f"{Color.RED}Failed to create orchestrator: {e}{Color.ENDC}")
        return

    # Run workflow with cleanup
    print(f"{Color.BOLD}Starting workflow execution...{Color.ENDC}\n")
    print("=" * 70)

    import time

    workflow_start = time.time()

    try:
        result = await orchestrator.execute_workflow(workflow)

        workflow_elapsed = time.time() - workflow_start

        print("=" * 70)
        print(f"\n{Color.GREEN}{Color.BOLD}Workflow completed successfully!{Color.ENDC}")
        print(f"{Color.CYAN}Total execution time: {workflow_elapsed:.2f}s{Color.ENDC}\n")
        print(f"{Color.CYAN}Final result:{Color.ENDC}")
        print(result)
        print()

        print(f"{Color.YELLOW}Execution Statistics:{Color.ENDC}")
        print(f"  Total tasks: {result['total_tasks']}")
        print(f"  Successful: {result['successful_tasks']}")
        print(f"  Failed: {result['failed_tasks']}")
        print(f"  Contexts used: {len(orchestrator.contexts)}")
        print(f"  Sessions created: {len(orchestrator.sessions)}")
        print()

    except Exception as e:
        print(f"\n{Color.RED}Workflow failed: {e}{Color.ENDC}")
        import traceback

        traceback.print_exc()
        return

    finally:
        print(f"\n{Color.YELLOW}Cleaning up sessions...{Color.ENDC}")
        await orchestrator.cleanup()

    print(
        f"""
{Color.BOLD}======================================================================{Color.ENDC}
{Color.BOLD}Demo complete!{Color.ENDC}
{Color.BOLD}======================================================================{Color.ENDC}

{Color.CYAN}Key Differences from demo.py:{Color.ENDC}
  ✓ Declarative workflow (YAML) vs imperative Python
  ✓ Orchestrator manages contexts vs manual session management
  ✓ Automatic parallel/sequential execution vs explicit asyncio
  ✓ Reusable workflow definition vs one-off script
  ✓ Simpler entry point vs complex orchestration logic
  ✓ Uses real Amplifier Core sessions (no mocks)

{Color.CYAN}Architecture Highlights:{Color.ENDC}
  ✓ One AmplifierSession per profile (shared across contexts)
  ✓ Mount plans loaded from JSON on-demand
  ✓ Sessions manage their own history internally
  ✓ Contexts track metadata only
  ✓ Automatic cleanup of all sessions
    """
    )


if __name__ == "__main__":
    asyncio.run(main())
