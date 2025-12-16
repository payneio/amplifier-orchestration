"""
Interactive Foreman-Worker Demo - Version 2 (FIXED)

This version incorporates all the fixes discovered through debugging:
1. Hybrid async approach (workers get CPU time during foreman execution)
2. Metadata filtering support in issue tool
3. Clean, simple worker prompts (NO complex system instructions)
4. Proper string formatting (no .format() conflicts)

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

# Add modules to path
modules_dir = Path(__file__).parent / "modules"
for module_dir in modules_dir.iterdir():
    if module_dir.is_dir() and module_dir.name.startswith("amplifier-module-"):
        sys.path.insert(0, str(module_dir))

from amplifier_core import AmplifierSession, ModuleLoader
from demo_stubs import StubApprovalSystem, StubDisplaySystem


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


def load_mount_plan(name: str) -> dict:
    """Load mount plan configuration."""
    path = Path(__file__).parent / "mount_plans" / f"{name}.json"
    with open(path) as f:
        import json
        return json.load(f)


class SimpleForemanWorkerOrchestrator:
    """
    Simplified Foreman-Worker Orchestrator with ALL FIXES applied.

    Key differences from original:
    1. Hybrid async (explicit yields for event loop fairness)
    2. NO complex system instructions (they break tool usage!)
    3. Clean, simple worker prompts
    4. Metadata filtering in queries
    """

    def __init__(self, loader, workspace, approval_system=None, display_system=None):
        self.loader = loader
        self.workspace = workspace
        self.approval_system = approval_system
        self.display_system = display_system
        self.worker_tasks = []
        self._shutdown = asyncio.Event()

    async def __aenter__(self):
        # Initialize foreman
        foreman_config = load_mount_plan("foreman")
        self.foreman_session = AmplifierSession(
            foreman_config,
            loader=self.loader,
            approval_system=self.approval_system,
            display_system=self.display_system,
        )
        await self.foreman_session.__aenter__()
        self.foreman_session_id = getattr(self.foreman_session, 'session_id', 'unknown')

        # Start workers
        self.worker_tasks = [
            asyncio.create_task(self._worker_loop("coding-worker-0", "coding")),
            asyncio.create_task(self._worker_loop("coding-worker-1", "coding")),
            asyncio.create_task(self._worker_loop("research-worker-0", "research")),
        ]

        return self

    async def __aexit__(self, *args):
        # Shutdown workers
        self._shutdown.set()
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)

        # Close foreman
        if self.foreman_session:
            await self.foreman_session.__aexit__(None, None, None)

    async def execute_user_message(self, message: str) -> str:
        """
        Execute foreman message with HYBRID ASYNC approach.

        Creates foreman execution as background task and polls with explicit yields.
        This gives worker tasks regular CPU time during foreman's LLM calls.
        """
        # Create foreman execution as background task (not blocking await)
        execution_task = asyncio.create_task(
            self.foreman_session.execute(message)
        )

        # Poll with explicit yields every 100ms to give workers CPU time
        while not execution_task.done():
            await asyncio.sleep(0.1)  # Event loop fairness!

        return execution_task.result()

    async def _worker_loop(self, worker_id: str, category: str):
        """
        Worker polling loop with CLEAN, SIMPLE prompts (NO system instructions).

        Key insight: Complex system instructions break tool usage!
        Solution: Just use simple, direct prompts like test_single_worker.py
        """
        try:
            worker_config = load_mount_plan("coding-worker" if category == "coding" else "research-worker")

            async with AmplifierSession(worker_config, loader=self.loader, parent_id=self.foreman_session_id) as session:
                worker_session_id = getattr(session, 'session_id', 'unknown')
                print(f"{Color.CYAN}[{worker_id}] Started (session_id: {worker_session_id}){Color.ENDC}", flush=True)

                # NO SYSTEM INSTRUCTIONS - This was the bug!
                # Just send clean prompts directly

                while not self._shutdown.is_set():
                    # Clean, simple prompt (like test_single_worker.py that works!)
                    prompt = f"""You are {worker_id}, a {category} specialist.

Task: Find and work on one issue

1. Use the issue tool to list ready issues: status=open, metadata={{'category': '{category}'}}
2. If you find one:
   - Update it to status=in_progress, assignee='{worker_id}'
   - Analyze the task
   - Complete your work and close the issue with a brief result
3. If no issues available, respond with "No work available"

Process ONE issue then stop."""

                    result = await session.execute(prompt)

                    if "no work available" not in result.lower():
                        print(f"{Color.CYAN}[{worker_id}] Completed work!{Color.ENDC}")

                    # Poll every 5 seconds
                    await asyncio.sleep(5)

        except Exception as e:
            print(f"{Color.RED}[{worker_id}] Error: {e}{Color.ENDC}")


async def interactive_demo():
    """Run interactive demo with all fixes applied."""
    print(f"""
{Color.BOLD}======================================================================{Color.ENDC}
{Color.BOLD}  Foreman-Worker Orchestrator Demo v2 (FIXED){Color.ENDC}
{Color.BOLD}  All Debugging Fixes Applied{Color.ENDC}
{Color.BOLD}======================================================================{Color.ENDC}
    """)

    # Validate API key
    import os
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        print(f"{Color.RED}ERROR: Valid ANTHROPIC_API_KEY not set{Color.ENDC}\n")
        print("Please set your API key:")
        print("  export ANTHROPIC_API_KEY='sk-ant-api03-...'")
        return

    print(f"{Color.GREEN}✓ API key validated{Color.ENDC}\n")

    # Setup
    loader = ModuleLoader(search_paths=[modules_dir])
    workspace = Path.cwd() / ".demo-workspace"

    # Clean workspace
    if workspace.exists():
        import shutil
        shutil.rmtree(workspace)
    workspace.mkdir()

    print(f"{Color.GREEN}✓ Module loader initialized{Color.ENDC}\n")

    # Create orchestrator with fixes
    print(f"{Color.BLUE}Creating Fixed Orchestrator...{Color.ENDC}")

    async with SimpleForemanWorkerOrchestrator(
        loader=loader,
        workspace=workspace,
        approval_system=StubApprovalSystem(),
        display_system=StubDisplaySystem(),
    ) as orchestrator:
        print(f"{Color.GREEN}✓ Orchestrator initialized{Color.ENDC}")
        print(f"   Foreman: foreman (session_id: {orchestrator.foreman_session_id})")
        print("   Workers: 2x coding, 1x research")
        print(f"   Workspace: {workspace}\n")

        print(f"{Color.BOLD}Fixes Applied:{Color.ENDC}")
        print(f"{Color.CYAN}  ✓ Hybrid async (workers get CPU time){Color.ENDC}")
        print(f"{Color.CYAN}  ✓ Metadata filtering (direct category queries){Color.ENDC}")
        print(f"{Color.CYAN}  ✓ NO system instructions (clean prompts only){Color.ENDC}")
        print(f"{Color.CYAN}  ✓ Proper string formatting (no conflicts){Color.ENDC}\n")

        # Give workers time to initialize and print their session IDs
        print(f"{Color.YELLOW}[Waiting 3s for workers to initialize...]{Color.ENDC}\n", flush=True)
        await asyncio.sleep(3)

        print("=" * 70)

        # Simulated user interactions
        interactions = [
            {
                "message": "Create 4 demo issues: 2 coding (fix auth, add password reset), 2 research (competitor analysis, user research)",
                "description": "User asks foreman to create initial work queue",
            },
            {
                "message": "What's the current status?",
                "description": "Check worker progress",
                "wait_before": 15,  # Let workers claim and complete work
            },
            {
                "message": "Give me a final summary",
                "description": "Final status check",
                "wait_before": 15,
            },
        ]

        for i, interaction in enumerate(interactions):
            # Wait for workers
            if "wait_before" in interaction:
                wait = interaction["wait_before"]
                print(f"\n{Color.YELLOW}[Waiting {wait}s for workers...]{Color.ENDC}\n")
                await asyncio.sleep(wait)

            # User message
            print(f"\n{'=' * 70}")
            print(f"{Color.BOLD}INTERACTION {i + 1}:{Color.ENDC} {interaction['description']}")
            print(f"{'=' * 70}\n")
            print(f"{Color.YELLOW}User:{Color.ENDC} {interaction['message']}\n")

            # Foreman responds
            try:
                response = await orchestrator.execute_user_message(interaction["message"])
                print(f"{Color.GREEN}Foreman:{Color.ENDC} {response}\n")
            except Exception as e:
                print(f"{Color.RED}Error: {e}{Color.ENDC}\n")

        # Final wait
        print(f"\n{Color.YELLOW}[Final wait for workers...]{Color.ENDC}\n")
        await asyncio.sleep(15)

        print("=" * 70)
        print(f"\n{Color.GREEN}{Color.BOLD}Demo complete!{Color.ENDC}\n")

    print(f"{Color.GREEN}✓ All agents shut down gracefully{Color.ENDC}\n")

    print(f"""
{Color.BOLD}======================================================================{Color.ENDC}
{Color.BOLD}Fixes Applied in This Version:{Color.ENDC}
{Color.BOLD}======================================================================{Color.ENDC}

{Color.CYAN}1. Hybrid Async Architecture{Color.ENDC}
   - Foreman execution wrapped in background task
   - Explicit yields every 100ms for event loop fairness
   - Workers get CPU time during foreman LLM calls
   - Result: Workers poll throughout execution (not starved)

{Color.CYAN}2. Metadata Filtering{Color.ENDC}
   - Added metadata parameter to issue tool
   - Workers query directly: metadata={{'category': 'coding'}}
   - No manual LLM parsing needed
   - Result: Reliable issue discovery

{Color.CYAN}3. Removed Complex System Instructions{Color.ENDC}
   - Original: 40+ lines of instructions confused LLM
   - Fixed: Simple, direct prompts only
   - Result: Workers actually use tools!

{Color.CYAN}4. Clean String Formatting{Color.ENDC}
   - Removed conflicting f-string + .format() usage
   - Result: No KeyError crashes

{Color.BOLD}======================================================================{Color.ENDC}

{Color.YELLOW}Why test_single_worker.py worked but test_isolated_demo.py didn't:{Color.ENDC}

{Color.GREEN}✓ test_single_worker.py:{Color.ENDC} Clean prompts, no system instructions
{Color.RED}✗ test_isolated_demo.py:{Color.ENDC} Complex system instructions broke tool usage

{Color.YELLOW}The lesson:{Color.ENDC} Sometimes LESS instruction is MORE effective!
    """)


if __name__ == "__main__":
    asyncio.run(interactive_demo())
