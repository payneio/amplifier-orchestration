"""
Research Compiler with Fact-Checkers Demo

Demonstrates the Observer Orchestrator pattern where:
- A main session (Researcher) researches and writes content
- Observer sessions watch the output and create feedback issues
- The Researcher addresses feedback and refines the content

KEY PATTERN - Bottom-Up Feedback:
================================
Unlike the Foreman-Worker pattern (top-down delegation), this demo shows
bottom-up feedback where observers autonomously identify issues:

1. Researcher writes initial research on a topic
2. Observers (Skeptic, Depth Seeker, Clarity Editor) read the content
3. Observers create issues when they spot problems in their domain
4. Researcher sees issues and addresses them
5. Cycle continues until observers have no more feedback

Observer Types:
- Skeptic: Questions claims that seem unsupported or dubious
- Depth Seeker: Identifies areas that need more detail or exploration
- Clarity Editor: Flags confusing or unclear passages

This demonstrates observers as autonomous critics that improve quality
through continuous feedback, without direct coordination.
"""

import asyncio
import json
import logging
import shutil
import sys
from pathlib import Path

from amplifier_core import ModuleLoader

from demo_stubs import StubApprovalSystem, StubDisplaySystem


# Add the observer orchestrator to path
orchestrator_path = Path(__file__).parent / "modules" / "amplifier-module-orchestrator-observers"
sys.path.insert(0, str(orchestrator_path))

from amplifier_module_orchestrator_observers import ObserverConfig, ObserverOrchestrator


# ANSI colors
class Color:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[35m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Suppress noisy loggers
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
    "amplifier_module_tool_web",
    "amplifier_module_orchestrator_observers",
]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_module_search_paths() -> list[Path]:
    """Get module search paths for Amplifier Core."""
    modules_dir = Path(__file__).parent / "modules"
    if not modules_dir.exists():
        raise RuntimeError("Modules directory not found. Run setup:\n  python setup_modules.py")
    return [modules_dir]


def load_mount_plan(mount_plans_dir: Path, profile: str) -> dict:
    """Load mount plan from JSON file."""
    mount_plan_path = mount_plans_dir / f"{profile}.json"
    if not mount_plan_path.exists():
        raise FileNotFoundError(f"Mount plan not found: {mount_plan_path}")
    with open(mount_plan_path) as f:
        return json.load(f)


# Demo configuration
RESEARCH_TOPIC = "the benefits and risks of intermittent fasting for health and longevity"
RESEARCH_FILE = "work/research.md"
MAX_ROUNDS = 3  # Maximum feedback rounds before stopping


async def interactive_demo():
    """Run the observer demo with the ObserverOrchestrator."""
    print(
        f"""
{Color.BOLD}======================================================================{Color.ENDC}
{Color.BOLD}  Research Compiler with Fact-Checkers Demo{Color.ENDC}
{Color.BOLD}  Observer Orchestrator: Bottom-Up Feedback Pattern{Color.ENDC}
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

    print(f"{Color.GREEN}API key validated{Color.ENDC}\n")

    # Clean workspace
    workspace = Path.cwd() / ".demo-workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(exist_ok=True)

    work_dir = Path.cwd() / "work"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(exist_ok=True)

    print(f"Workspace: {workspace}")
    print(f"Output: {work_dir}")
    print(f"Research topic: {RESEARCH_TOPIC}\n")

    # Set up module loading
    try:
        search_paths = get_module_search_paths()

        for search_path in search_paths:
            for module_dir in search_path.iterdir():
                if module_dir.is_dir() and module_dir.name.startswith("amplifier-module-"):
                    path_str = str(module_dir)
                    if path_str not in sys.path:
                        sys.path.insert(0, path_str)

        loader = ModuleLoader(search_paths=search_paths)
        print(f"{Color.GREEN}Module loader initialized{Color.ENDC}\n")

    except Exception as e:
        print(f"{Color.RED}Failed to initialize module loader: {e}{Color.ENDC}")
        return

    # Load mount plan configurations
    mount_plans_dir = Path(__file__).parent / "mount_plans"
    researcher_config = load_mount_plan(mount_plans_dir, "researcher")
    observer_config = load_mount_plan(mount_plans_dir, "observer")

    # Create stub systems
    approval_system = StubApprovalSystem()
    display_system = StubDisplaySystem()

    # Define observers
    observer_configs = [
        ObserverConfig(
            name="Skeptic",
            config=observer_config,
            role="Questions unsupported or dubious claims",
            focus=(
                "Look for claims that lack citations, seem exaggerated, or contradict common knowledge. "
                "Flag statements that need better evidence or qualification. "
                "Be specific about which claims are problematic and why."
            ),
        ),
        ObserverConfig(
            name="Depth Seeker",
            config=observer_config,
            role="Identifies areas needing more detail",
            focus=(
                "Look for topics mentioned briefly that deserve more exploration, missing important aspects, "
                "or areas where the reader might want more practical information. "
                "Suggest specific additions that would improve completeness."
            ),
        ),
        ObserverConfig(
            name="Clarity Editor",
            config=observer_config,
            role="Flags confusing or unclear passages",
            focus=(
                "Look for jargon that isn't explained, sentences that are hard to follow, "
                "logical jumps that might confuse readers, or structure that could be improved. "
                "Suggest specific rewrites or clarifications."
            ),
        ),
    ]

    print(f"{Color.BLUE}Creating Observer Orchestrator...{Color.ENDC}")
    print("   Main session: Researcher")
    print(f"   Observers: {', '.join(obs.name for obs in observer_configs)}")
    print("=" * 70)

    async with ObserverOrchestrator(
        loader=loader,
        main_config=researcher_config,
        observer_configs=observer_configs,
        workspace_root=workspace,
        approval_system=approval_system,
        display_system=display_system,
    ) as orchestrator:
        print(f"{Color.GREEN}Orchestrator created{Color.ENDC}\n")

        # Phase 1: Initial research
        print(f"\n{Color.BLUE}{Color.BOLD}=== PHASE 1: Initial Research ==={Color.ENDC}")
        print(f"{Color.YELLOW}Topic: {RESEARCH_TOPIC}{Color.ENDC}\n")

        initial_prompt = f"""Research and write about: {RESEARCH_TOPIC}

Instructions:
1. Research this topic thoroughly
2. Write a comprehensive research summary to the file: {RESEARCH_FILE}
3. Include:
   - An introduction explaining the topic
   - Key benefits (with specific claims)
   - Key risks (with specific claims)
   - Current scientific consensus
   - Practical recommendations
4. Make it about 500-800 words
5. Include specific claims that can be fact-checked

Write the research now."""

        print(f"{Color.CYAN}Researcher is working...{Color.ENDC}")
        response = await orchestrator.execute_user_message(initial_prompt)

        print(f"\n{Color.GREEN}Initial draft complete{Color.ENDC}")
        if len(response) > 400:
            print(f"{Color.CYAN}{response[:400]}...{Color.ENDC}")
        else:
            print(f"{Color.CYAN}{response}{Color.ENDC}")

        # Show session ID
        if orchestrator.main_session_id:
            print(f"\n{Color.BLUE}Main session ID: {orchestrator.main_session_id}{Color.ENDC}")

        # Phase 2-N: Feedback loops
        for round_num in range(1, MAX_ROUNDS + 1):
            print(f"\n{'=' * 70}")
            print(f"{Color.BOLD}FEEDBACK ROUND {round_num} of {MAX_ROUNDS}{Color.ENDC}")
            print("=" * 70)

            # Run observers
            print(f"\n{Color.MAGENTA}{Color.BOLD}Observers reviewing...{Color.ENDC}")
            await asyncio.sleep(2)  # Brief pause for readability

            issues_created = await orchestrator.run_observer_round(round_num)

            if issues_created == 0:
                print(f"\n{Color.GREEN}{Color.BOLD}All observers satisfied! No more feedback.{Color.ENDC}")
                break

            print(f"\n{Color.YELLOW}Observers created {issues_created} issue(s){Color.ENDC}")

            # Address feedback
            print(f"\n{Color.BLUE}{Color.BOLD}Researcher addressing feedback...{Color.ENDC}")
            await asyncio.sleep(2)

            had_feedback = await orchestrator.address_feedback(round_num)

            if not had_feedback:
                print(f"{Color.GREEN}No feedback to address - work complete!{Color.ENDC}")
                break

            print(f"{Color.GREEN}Feedback addressed{Color.ENDC}")

        else:
            print(f"\n{Color.YELLOW}Maximum rounds ({MAX_ROUNDS}) reached.{Color.ENDC}")

        print(f"\n{Color.CYAN}Shutting down orchestrator...{Color.ENDC}")

    # Orchestrator cleanup handled by context manager
    print(f"{Color.GREEN}Orchestrator shut down gracefully{Color.ENDC}")

    # Final summary
    print(
        f"""
{'=' * 70}
{Color.GREEN}{Color.BOLD}Demo Complete!{Color.ENDC}
{'=' * 70}

{Color.CYAN}Research file: {work_dir / 'research.md'}{Color.ENDC}

{Color.BOLD}Key Features Demonstrated:{Color.ENDC}

{Color.CYAN}Observer Orchestrator Pattern{Color.ENDC}
  - Main session does actual work (research/writing)
  - Observers watch and provide specialized feedback
  - Issues flow bottom-up (observers create, main addresses)
  - Natural convergence when observers are satisfied

{Color.CYAN}Compared to Foreman-Worker{Color.ENDC}
  - Foreman-Worker: Top-down delegation (foreman creates tasks)
  - Observer: Bottom-up feedback (observers create issues)
  - Main session IS the worker, not a delegator

{Color.CYAN}Observer Types Used{Color.ENDC}
  - Skeptic: Questioned unsupported claims
  - Depth Seeker: Identified areas needing expansion
  - Clarity Editor: Flagged confusing passages

{Color.BOLD}When to Use Observer Orchestrator:{Color.ENDC}
  - Content creation with quality review
  - Code generation with automated review
  - Research with fact-checking
  - Any workflow needing iterative refinement through feedback

{Color.BOLD}When to Use Foreman-Worker:{Color.ENDC}
  - Task queue processing
  - Parallel independent work items
  - User-directed multi-agent delegation
    """
    )


if __name__ == "__main__":
    asyncio.run(interactive_demo())
