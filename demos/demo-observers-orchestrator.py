"""
Research Compiler with Fact-Checkers Demo

Demonstrates the Observer Orchestrator pattern where:
- A main session (Researcher) researches and writes content
- Observer sessions run continuously in background, watching for changes
- Observers automatically create feedback issues when they spot problems
- The Researcher addresses feedback when prompted

KEY PATTERN - Bottom-Up Feedback with Continuous Observers:
==========================================================
Like the Foreman-Worker pattern (where workers run continuously), observers
here run in infinite background loops:

1. Researcher writes initial research on a topic
2. Observers (Skeptic, Depth Seeker, Clarity Editor) automatically detect changes
3. Observers review and create issues when they spot problems
4. User asks Researcher to address feedback
5. Cycle continues naturally without manual coordination

Observer Types:
- Skeptic: Questions claims that seem unsupported or dubious
- Depth Seeker: Identifies areas that need more detail or exploration
- Clarity Editor: Flags confusing or unclear passages

This demonstrates observers as autonomous critics that improve quality
through continuous background monitoring.
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

# Add issue manager to path for monitoring
issue_manager_path = Path(__file__).parent / "modules" / "amplifier-module-issue-manager"
sys.path.insert(0, str(issue_manager_path))

from amplifier_module_orchestrator_observers import ObserverConfig, ObserverOrchestrator
from amplifier_module_issue_manager import IssueManager


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
    DIM = "\033[2m"


# Issue status symbols and colors
STATUS_DISPLAY = {
    "open": (Color.YELLOW, "○"),
    "in_progress": (Color.BLUE, "◐"),
    "pending_user_input": (Color.MAGENTA, "?"),
    "closed": (Color.GREEN, "●"),
}

PRIORITY_DISPLAY = {
    0: (Color.RED, "P0"),
    1: (Color.RED, "P1"),
    2: (Color.YELLOW, "P2"),
    3: (Color.CYAN, "P3"),
    4: (Color.DIM, "P4"),
}


def format_issue_line(issue, show_assignee: bool = True) -> str:
    """Format a single issue as a compact one-line display."""
    status_color, status_symbol = STATUS_DISPLAY.get(issue.status, (Color.ENDC, "?"))
    priority_color, priority_label = PRIORITY_DISPLAY.get(issue.priority, (Color.ENDC, f"P{issue.priority}"))

    # Truncate title if too long
    title = issue.title[:50] + "..." if len(issue.title) > 50 else issue.title

    # Format assignee if present
    assignee_part = ""
    if show_assignee and issue.assignee:
        assignee_part = f" {Color.DIM}[{issue.assignee}]{Color.ENDC}"

    return (
        f"  {status_color}{status_symbol}{Color.ENDC} "
        f"{priority_color}{priority_label}{Color.ENDC} "
        f"{title}{assignee_part}"
    )


def display_issue_summary(manager: IssueManager, label: str = "Issues") -> dict:
    """Display a summary of all issues and return counts by status."""
    issues = manager.list_issues()

    counts = {"open": 0, "in_progress": 0, "pending_user_input": 0, "closed": 0}
    for issue in issues:
        if issue.status in counts:
            counts[issue.status] += 1

    total = len(issues)
    if total == 0:
        print(f"  {Color.DIM}No issues yet{Color.ENDC}")
        return counts

    # Summary line
    summary_parts = []
    if counts["open"]:
        summary_parts.append(f"{Color.YELLOW}{counts['open']} open{Color.ENDC}")
    if counts["in_progress"]:
        summary_parts.append(f"{Color.BLUE}{counts['in_progress']} in progress{Color.ENDC}")
    if counts["closed"]:
        summary_parts.append(f"{Color.GREEN}{counts['closed']} closed{Color.ENDC}")

    print(f"  {label}: {', '.join(summary_parts)} ({total} total)")

    # Show open/in-progress issues (most relevant)
    active_issues = [i for i in issues if i.status in ("open", "in_progress")]
    for issue in sorted(active_issues, key=lambda i: (i.priority, i.created_at)):
        print(format_issue_line(issue))

    return counts


async def monitor_issues_with_feedback(
    manager: IssueManager,
    duration: float,
    poll_interval: float = 3.0,
    label: str = "Observer Review",
) -> None:
    """Monitor issues during a wait period, showing changes as they happen."""
    seen_issues: dict[str, str] = {}  # id -> status
    start_time = asyncio.get_event_loop().time()

    print(f"\n{Color.DIM}{'─' * 60}{Color.ENDC}")
    print(f"{Color.MAGENTA}📋 {label} - monitoring for {int(duration)}s...{Color.ENDC}")

    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= duration:
            break

        # Check for new/changed issues
        try:
            issues = manager.list_issues()

            for issue in issues:
                prev_status = seen_issues.get(issue.id)

                if prev_status is None:
                    # New issue
                    status_color, status_symbol = STATUS_DISPLAY.get(issue.status, (Color.ENDC, "?"))
                    print(
                        f"  {Color.GREEN}+ NEW{Color.ENDC} {status_color}{status_symbol}{Color.ENDC} "
                        f"{issue.title[:45]}{'...' if len(issue.title) > 45 else ''} "
                        f"{Color.DIM}[{issue.assignee or 'unassigned'}]{Color.ENDC}"
                    )
                    seen_issues[issue.id] = issue.status

                elif prev_status != issue.status:
                    # Status changed
                    old_color, old_symbol = STATUS_DISPLAY.get(prev_status, (Color.ENDC, "?"))
                    new_color, new_symbol = STATUS_DISPLAY.get(issue.status, (Color.ENDC, "?"))
                    print(
                        f"  {Color.CYAN}↻{Color.ENDC} {old_color}{old_symbol}{Color.ENDC}→"
                        f"{new_color}{new_symbol}{Color.ENDC} "
                        f"{issue.title[:45]}{'...' if len(issue.title) > 45 else ''} "
                        f"{Color.DIM}({prev_status}→{issue.status}){Color.ENDC}"
                    )
                    seen_issues[issue.id] = issue.status

        except Exception:
            pass  # Ignore transient read errors

        # Wait for next poll (but not longer than remaining time)
        remaining = duration - elapsed
        await asyncio.sleep(min(poll_interval, remaining))

    # Final summary
    print(f"{Color.DIM}{'─' * 60}{Color.ENDC}")
    display_issue_summary(manager, "Current state")


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


async def interactive_demo():
    """Run the observer demo with continuous background observers."""
    print(
        f"""
{Color.BOLD}======================================================================{Color.ENDC}
{Color.BOLD}  Research Compiler with Fact-Checkers Demo{Color.ENDC}
{Color.BOLD}  Observer Orchestrator: Continuous Background Observers{Color.ENDC}
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
    print("   Observer check interval: 15 seconds")
    print("   Watch paths: work/")
    print("=" * 70)

    # Create issue manager for monitoring (reads from same location as sessions)
    issues_dir = workspace / ".amplifier" / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    issue_monitor = IssueManager(data_dir=issues_dir, actor="monitor")

    async with ObserverOrchestrator(
        loader=loader,
        main_config=researcher_config,
        observer_configs=observer_configs,
        workspace_root=workspace,
        approval_system=approval_system,
        display_system=display_system,
        observer_interval=15.0,  # Check every 15 seconds
        watch_paths=["work/"],
    ) as orchestrator:
        print(f"{Color.GREEN}Orchestrator created - observers starting in background{Color.ENDC}\n")

        # === User Interaction 1: Initial Research ===
        print(f"\n{Color.BLUE}{Color.BOLD}=== USER: Create initial research ==={Color.ENDC}")
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

        # Show session IDs
        if orchestrator.main_session_id:
            print(f"\n{Color.BLUE}Main session ID: {orchestrator.main_session_id}{Color.ENDC}")

        # === Wait for observers to review ===
        print(f"\n{'=' * 70}")
        print(f"{Color.MAGENTA}{Color.BOLD}Observers are now reviewing in the background...{Color.ENDC}")
        await monitor_issues_with_feedback(
            issue_monitor,
            duration=30.0,
            poll_interval=2.0,
            label="Observers creating feedback issues",
        )

        # Show observer session IDs
        if orchestrator.observer_session_ids:
            print(f"\n{Color.BLUE}Observer sessions:{Color.ENDC}")
            for name, sid in orchestrator.observer_session_ids.items():
                print(f"   {name}: {sid}")

        # === User Interaction 2: Address Feedback ===
        print(f"\n{'=' * 70}")
        print(f"{Color.BLUE}{Color.BOLD}=== USER: Address any feedback ==={Color.ENDC}\n")

        # Show current issues before researcher starts
        print(f"{Color.YELLOW}Issues created by observers:{Color.ENDC}")
        display_issue_summary(issue_monitor, "Before addressing")
        print()

        print(f"{Color.CYAN}Researcher checking for and addressing issues...{Color.ENDC}")

        # Run researcher and monitor concurrently
        async def researcher_task():
            return await orchestrator.execute_user_message(
                "Check for any open feedback issues and address them. "
                "Update the research file to fix any problems the observers found."
            )

        async def monitor_task():
            """Monitor while researcher works (up to 120 seconds)."""
            seen: dict[str, str] = {}
            for _ in range(60):  # Check for up to 2 minutes
                try:
                    for issue in issue_monitor.list_issues():
                        prev = seen.get(issue.id)
                        if prev and prev != issue.status:
                            old_color, old_sym = STATUS_DISPLAY.get(prev, (Color.ENDC, "?"))
                            new_color, new_sym = STATUS_DISPLAY.get(issue.status, (Color.ENDC, "?"))
                            action = "addressed" if issue.status == "closed" else "working on"
                            print(
                                f"  {Color.CYAN}↻ Researcher {action}:{Color.ENDC} "
                                f"{old_color}{old_sym}{Color.ENDC}→{new_color}{new_sym}{Color.ENDC} "
                                f"{issue.title[:40]}{'...' if len(issue.title) > 40 else ''}"
                            )
                        seen[issue.id] = issue.status
                except Exception:
                    pass
                await asyncio.sleep(2)

        # Start monitoring in background, wait for researcher
        monitor = asyncio.create_task(monitor_task())
        response = await researcher_task()
        monitor.cancel()
        try:
            await monitor
        except asyncio.CancelledError:
            pass

        print(f"\n{Color.GREEN}Feedback addressed{Color.ENDC}")
        if len(response) > 400:
            print(f"{Color.CYAN}{response[:400]}...{Color.ENDC}")
        else:
            print(f"{Color.CYAN}{response}{Color.ENDC}")

        # Show issue status after researcher addressed them
        print(f"\n{Color.YELLOW}Issues after researcher addressed:{Color.ENDC}")
        display_issue_summary(issue_monitor, "After addressing")

        # === Wait for observers to review changes ===
        print(f"\n{'=' * 70}")
        print(f"{Color.MAGENTA}{Color.BOLD}Observers reviewing the updated work...{Color.ENDC}")
        await monitor_issues_with_feedback(
            issue_monitor,
            duration=30.0,
            poll_interval=2.0,
            label="Observers reviewing updates",
        )

        # === User Interaction 3: Final check ===
        print(f"\n{'=' * 70}")
        print(f"{Color.BLUE}{Color.BOLD}=== USER: Final status check ==={Color.ENDC}\n")

        print(f"{Color.CYAN}Checking final status...{Color.ENDC}")
        response = await orchestrator.execute_user_message(
            "Give me a summary: How many issues were raised and addressed? "
            "Are there any remaining open issues? What's the final state of the research?"
        )

        print(f"\n{Color.GREEN}Final status:{Color.ENDC}")
        print(f"{Color.CYAN}{response}{Color.ENDC}")

        print(f"\n{Color.CYAN}Shutting down orchestrator (stopping observer loops)...{Color.ENDC}")

    # Orchestrator cleanup handled by context manager
    print(f"{Color.GREEN}Orchestrator shut down gracefully{Color.ENDC}")

    # Final summary
    print(
        f"""
{"=" * 70}
{Color.GREEN}{Color.BOLD}Demo Complete!{Color.ENDC}
{"=" * 70}

{Color.CYAN}Research file: {work_dir / "research.md"}{Color.ENDC}

{Color.BOLD}Key Features Demonstrated:{Color.ENDC}

{Color.CYAN}Continuous Background Observers{Color.ENDC}
  - Observers run in infinite loops (like workers in foreman-worker)
  - Automatically detect file changes via watch_paths
  - Create feedback issues without manual triggering
  - No need for explicit "run observer round" calls

{Color.CYAN}Change Detection{Color.ENDC}
  - Observers track file modification times
  - Only review when files actually change
  - Avoids duplicate reviews of unchanged content

{Color.CYAN}Compared to Foreman-Worker{Color.ENDC}
  - Foreman-Worker: Workers claim tasks from queue (top-down)
  - Observer: Observers watch output and create feedback (bottom-up)
  - Both use continuous background loops

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
